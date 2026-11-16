"""Built-in personal data labels, regular expressions, and span conflict handling."""

from __future__ import annotations

import re
Span = tuple[int, int, str, str]

LABELS = [
    "PER",
    "ORG",
    "LOC",
    "PHONE",
    "EMAIL",
    "INN",
    "OGRN",
    "OGRNIP",
    "SNILS",
    "PASSPORT",
    "ACCOUNT",
    "BIC",
    "ZIP",
    "DATE",
]

# Порядок важен: длинные цифровые последовательности идут первыми,
# чтобы ИНН не откусил кусок от расчетного счета.
REGEX_RULES = [
    ("ACCOUNT", r"\b\d{20}\b|\b\d{5}(?:\s\d{3,6}){3,4}\b"),
    ("OGRN", r"\b\d{13}\b"),
    ("OGRNIP", r"\b[34]\d{14}\b"),
    ("INN", r"\b\d{10}(?:\d{2})?\b"),
    ("SNILS", r"\b\d{3}-\d{3}-\d{3}[ -]?\d{2}\b"),
    ("PASSPORT", r"\b\d{2}\s?\d{2}\s?\d{6}\b"),
    ("BIC", r"\b\d{9}\b"),
    ("ZIP", r"\b\d{6}\b"),
    (
        "PHONE",
        r"(?<!\d)(?:\+7|8)[\s\-]?(?:\(\d{3}\)|\d{3})[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}(?!\d)",
    ),
    ("EMAIL", r"[A-Za-z0-9_.+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+"),
    ("DATE", r"\b\d{2}\.\d{2}\.\d{4}(?:\s?года|\s?г\.?)?(?!\d)"),
    # Имя ИП: префикс не входит в замену, маскируется только ФИО (группа 1)
    (
        "PER",
        r"(?:[Ии]ндивидуальн\w+|[Ии]П|И\.П\.)\s+(?:[Пп]редпринимател\w+\s+)?([А-ЯЁ][а-яё]+(?:-[А-ЯЁ][а-яё]+)?(?:\s+[А-ЯЁ]\.\s?[А-ЯЁ]\.|\s+[А-ЯЁ][а-яё]+(?:-[А-ЯЁ][а-яё]+)?\s+[А-ЯЁ][а-яё]+))",
    ),
]


def filter_overlaps(spans: list[Span]) -> list[Span]:
    """Keep non-overlapping spans, preferring earlier and longer spans."""
    ordered = sorted(spans, key=lambda span: (span[0], -(span[1] - span[0])))
    result: list[Span] = []
    last_end = -1
    for span in ordered:
        if span[0] >= last_end:
            result.append(span)
            last_end = span[1]
    return result
