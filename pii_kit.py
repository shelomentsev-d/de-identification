#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pii_kit.py - локальная маскировка персональных данных и обратная замена.
Работает полностью на вашем Mac, ничего не отправляет в сеть.

Использование:
    python3 pii_kit.py clean договор.docx        -> договор_clean.docx + договор_keys.json
    python3 pii_kit.py clean договор.pdf         -> договор_clean.md   + договор_keys.json
    python3 pii_kit.py restore ответ.txt         -> ответ_restored.txt (использует найденный _keys.json)

Поддерживаемые форматы: .docx (текст и таблицы, форматирование сохраняется),
.xlsx, .pptx, .txt, .md, .csv, .pdf (с текстовым слоем, извлекается в .md).
"""

import argparse
import json
import re
import sys
from pathlib import Path

from engine.masker import Masker
from engine.rules import LABELS, REGEX_RULES, filter_overlaps


def apply_span_to_paragraph(p, start, stop, token):
    """Заменить [start:stop) в абзаце docx с сохранением форматирования:
    вставка делается в run(ы), а не через p.text (которое схлопывает разметку)."""
    pos = 0
    hit = []
    for r in p.runs:
        rl = len(r.text)
        rs, re_ = pos, pos + rl
        if rs < stop and re_ > start:
            hit.append((r, max(start - rs, 0), min(stop - rs, rl)))
        pos = re_
    if not hit:
        return False
    if len(hit) == 1:
        r, a, b = hit[0]
        r.text = r.text[:a] + token + r.text[b:]
    else:
        r0, a0, _ = hit[0]
        r0.text = r0.text[:a0] + token
        for r, _, _ in hit[1:-1]:
            r.text = ""
        r1, _, b1 = hit[-1]
        r1.text = r1.text[b1:]
    return True


def process_docx(path, masker):
    from docx import Document
    doc = Document(path)

    def handle_paragraph(p):
        text = p.text
        if not text.strip():
            return
        spans = filter_overlaps(masker.find_spans(text))
        for start, stop, label, value in sorted(spans, key=lambda s: s[0],
                                                reverse=True):
            token = masker.token_for(value, label)
            if not apply_span_to_paragraph(p, start, stop, token):
                p.text = masker.mask_text(text)  # запасной вариант
                return

    def walk_tables(tables):
        for t in tables:
            for row in t.rows:
                for cell in row.cells:
                    for p in cell.paragraphs:
                        handle_paragraph(p)
                    walk_tables(cell.tables)  # вложенные таблицы

    for p in doc.paragraphs:
        handle_paragraph(p)
    walk_tables(doc.tables)

    out = path.with_name(path.stem + "_clean" + path.suffix)
    doc.save(out)
    return out


def process_text(path, masker):
    content = path.read_text(encoding="utf-8")
    clean = masker.mask_text(content)
    out = path.with_name(path.stem + "_clean" + path.suffix)
    out.write_text(clean, encoding="utf-8")
    return out


def process_xlsx(path, masker):
    from openpyxl import load_workbook
    wb = load_workbook(path)
    for ws in wb.worksheets:
        for row in ws.iter_rows():
            for cell in row:
                if isinstance(cell.value, str) and cell.value.strip():
                    cell.value = masker.mask_text(cell.value)
    out = path.with_name(path.stem + "_clean" + path.suffix)
    wb.save(out)
    return out


def process_pptx(path, masker):
    from pptx import Presentation
    prs = Presentation(path)

    def handle_tf(tf):
        for p in tf.paragraphs:
            text = "".join(r.text for r in p.runs)
            if not text.strip():
                continue
            spans = filter_overlaps(masker.find_spans(text))
            for start, stop, label, value in sorted(spans, key=lambda s: s[0],
                                                    reverse=True):
                token = masker.token_for(value, label)
                if not apply_span_to_paragraph(p, start, stop, token):
                    p.runs[0].text = masker.mask_text(text)
                    for r in p.runs[1:]:
                        r.text = ""
                    break

    def walk_shapes(shapes):
        for sh in shapes:
            if sh.shape_type == 6:  # группа фигур
                walk_shapes(sh.shapes)
                continue
            if sh.has_text_frame:
                handle_tf(sh.text_frame)
            if getattr(sh, "has_table", False) and sh.has_table:
                for row in sh.table.rows:
                    for cell in row.cells:
                        handle_tf(cell.text_frame)

    for slide in prs.slides:
        walk_shapes(slide.shapes)
        if slide.has_notes_slide:  # заметки докладчика
            walk_shapes(slide.notes_slide.shapes)

    out = path.with_name(path.stem + "_clean" + path.suffix)
    prs.save(out)
    return out


def process_pdf(path, masker):
    try:
        from pypdf import PdfReader
    except ImportError:
        sys.exit("Нужна библиотека: pip3 install pypdf")
    reader = PdfReader(str(path))
    parts = []
    for i, page in enumerate(reader.pages, 1):
        txt = page.extract_text() or ""
        if not txt.strip():
            sys.exit(
                "Страница {} не содержит текстового слоя (скан).\n"
                "Распознайте текст заранее: tesseract (brew install tesseract "
                "tesseract-lang) или Live Text на Mac, затем повторите.".format(i)
            )
        parts.append("## Страница {}\n\n{}".format(i, txt))
    clean = masker.mask_text("\n\n".join(parts))
    out = path.with_name(path.stem + "_clean.md")
    out.write_text(clean, encoding="utf-8")
    return out


def cmd_clean(args):
    path = Path(args.file)
    if not path.exists():
        sys.exit("Файл не найден: {}".format(path))
    masker = Masker()
    suffix = path.suffix.lower()
    if suffix == ".docx":
        out = process_docx(path, masker)
    elif suffix == ".xlsx":
        out = process_xlsx(path, masker)
    elif suffix == ".pptx":
        out = process_pptx(path, masker)
    elif suffix == ".pdf":
        out = process_pdf(path, masker)
    elif suffix in (".txt", ".md", ".csv"):
        out = process_text(path, masker)
    else:
        sys.exit("Неизвестный формат {}. Поддерживаются: docx, xlsx, pptx, pdf, txt, md, csv.".format(suffix))

    keys_path = path.with_name(path.stem + "_keys.json")
    keys_path.write_text(
        json.dumps({"mapping": masker.mapping}, ensure_ascii=False, indent=2),
        encoding="utf-8")

    print("Готово.")
    print("  Очищенный файл: {}".format(out.name))
    print("  Ключ замен:     {}".format(keys_path.name))
    total = sum(masker.counters.values())
    print("  Заменено сущностей: {} ({} уникальных)".format(total, len(masker.mapping)))
    for label in LABELS:
        if masker.counters.get(label):
            print("    {}: {}".format(label, masker.counters[label]))
    print("Проверьте очищенный файл глазами перед отправкой в Cherry Studio.")


def cmd_restore(args):
    answer = Path(args.answer_file)
    if not answer.exists():
        sys.exit("Файл не найден: {}".format(answer))
    if args.keys:
        keys_path = Path(args.keys)
    else:
        candidates = sorted(answer.parent.glob("*_keys.json"))
        if len(candidates) != 1:
            sys.exit("Ключ не найден однозначно. Укажите явно: --keys договор_keys.json")
        keys_path = candidates[0]

    mapping = json.loads(keys_path.read_text(encoding="utf-8"))["mapping"]
    text = answer.read_text(encoding="utf-8")
    restored = 0
    for real, token in mapping.items():
        label, num = token.strip("[]").rsplit("_", 1)
        # Толерантный поиск: модель может выдать ORG_1, [ORG_1], (ORG_1), «ORG_1»
        pattern = re.compile(
            r"[\[\(\«\"']?" + re.escape(label) + r"[\s_]?" + re.escape(num) +
            r"[\]\)\»\"']?")
        text, n = pattern.subn(lambda m: real, text)
        restored += n
    out = answer.with_name(answer.stem + "_restored.txt")
    out.write_text(text, encoding="utf-8")
    print("Готово: {}".format(out.name))
    print("Восстановлено замен: {}".format(restored))
    if restored < len(mapping):
        print("Внимание: не все токены встретились в ответе ({} из {}). "
              "Если модель исказила токен, сверьтесь с {}".format(
                  restored, len(mapping), keys_path.name))


def main():
    ap = argparse.ArgumentParser(description="Локальная маскировка PII (офлайн)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("clean", help="обезличить файл перед отправкой в нейросеть")
    c.add_argument("file")
    c.set_defaults(func=cmd_clean)
    r = sub.add_parser("restore", help="вернуть реальные данные в ответ нейросети")
    r.add_argument("answer_file")
    r.add_argument("--keys", help="путь к _keys.json, если рядом несколько ключей")
    r.set_defaults(func=cmd_restore)
    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
