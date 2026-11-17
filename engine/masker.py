"""personal data span detection and token mapping."""

from __future__ import annotations

import re
import sys
from pathlib import Path

from .rules import LABELS, REGEX_RULES, filter_overlaps


def _bundled_data(*parts: str) -> str | None:
    """Return a data file shipped next to a frozen app, if it is on disk.

    PyInstaller keeps pure-Python modules in an archive, so natasha's
    ``dirname(__file__)`` does not point at the extracted ``.tar`` models.
    On macOS those files land in ``Contents/Resources``; on Windows and in
    onefile mode they land under ``sys._MEIPASS``.
    """
    if not getattr(sys, "frozen", False):
        return None
    roots = []
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        roots.append(Path(meipass))
        roots.append(Path(meipass).parent / "Resources")
    roots.append(Path(sys.executable).resolve().parent.parent / "Resources")
    for root in roots:
        candidate = root.joinpath(*parts)
        if candidate.is_file():
            return str(candidate)
    return None


class Masker:
    """Find personal data spans and replace them with stable per-document tokens."""

    def __init__(self, enable_ner: bool = True):
        self.mapping: dict[str, str] = {}
        self.counters = {label: 0 for label in LABELS}
        self.enable_ner = enable_ner
        self._ner = None
        self._ner_unavailable = False

    def _get_ner(self):
        if self._ner is None:
            from natasha import Doc, NewsEmbedding, NewsNERTagger, Segmenter

            # In a PyInstaller .app the model files land in Contents/Resources,
            # while natasha computes its paths from __file__ inside the archive.
            embedding_path = _bundled_data("natasha", "data", "emb", "navec_news_v1_1B_250K_300d_100q.tar")
            ner_path = _bundled_data("natasha", "data", "model", "slovnet_ner_news_v1.tar")
            segmenter = Segmenter()
            embedding = NewsEmbedding(embedding_path) if embedding_path else NewsEmbedding()
            tagger = NewsNERTagger(embedding, ner_path) if ner_path else NewsNERTagger(embedding)
            self._ner = (segmenter, tagger, Doc)
        return self._ner

    def token_for(self, value: str, label: str) -> str:
        if value not in self.mapping:
            self.counters[label] = self.counters.get(label, 0) + 1
            self.mapping[value] = f"[{label}_{self.counters[label]}]"
        return self.mapping[value]

    def find_spans(self, text: str) -> list[tuple[int, int, str, str]]:
        """Return all detected entities as ``(start, stop, label, value)``."""
        spans: list[tuple[int, int, str, str]] = []
        for label, pattern in REGEX_RULES:
            for match in re.finditer(pattern, text):
                if match.re.groups:
                    start, stop = match.span(1)
                    value = match.group(1)
                    # Keep the full match as a hidden priority boundary for
                    # prefixed forms such as "Индивидуальный Предприниматель".
                    # The public span still replaces only the captured name.
                    spans.append((start, stop, label, value))
                    if match.start() < start:
                        spans.append((match.start(), start, "__PREFIX__", ""))
                else:
                    spans.append((match.start(), match.end(), label, match.group(0)))

        if self.enable_ner and not self._ner_unavailable:
            try:
                segmenter, tagger, doc_type = self._get_ner()
                if any(char.isalpha() for char in text):
                    doc = doc_type(text)
                    doc.segment(segmenter)
                    doc.tag_ner(tagger)
                    for span in doc.spans:
                        if span.type in ("PER", "ORG", "LOC"):
                            spans.append((span.start, span.stop, span.type, span.text))
            except Exception:
                # NER is optional. Regex masking must still work in frozen builds
                # where Natasha's model data is unavailable or incomplete.
                self._ner_unavailable = True
        return spans

    def mask_text(self, text: str) -> str:
        spans = filter_overlaps(self.find_spans(text))
        output: list[str] = []
        position = 0
        for start, stop, label, value in spans:
            output.append(text[position:start])
            output.append(self.token_for(value, label))
            position = stop
        output.append(text[position:])
        return "".join(output)
