"""PII span detection and token mapping."""

from __future__ import annotations

import re

from .rules import LABELS, REGEX_RULES, filter_overlaps


class Masker:
    """Find PII spans and replace them with stable per-document tokens."""

    def __init__(self, enable_ner: bool = True):
        self.mapping: dict[str, str] = {}
        self.counters = {label: 0 for label in LABELS}
        self.enable_ner = enable_ner
        self._ner = None

    def _get_ner(self):
        if self._ner is None:
            from natasha import Doc, NewsEmbedding, NewsNERTagger, Segmenter

            segmenter = Segmenter()
            embedding = NewsEmbedding()
            tagger = NewsNERTagger(embedding)
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
                    spans.append((start, stop, label, match.group(1)))
                else:
                    spans.append((match.start(), match.end(), label, match.group(0)))

        if self.enable_ner:
            try:
                segmenter, tagger, doc_type = self._get_ner()
            except ImportError:
                segmenter = None
            if segmenter and any(char.isalpha() for char in text):
                doc = doc_type(text)
                doc.segment(segmenter)
                doc.tag_ner(tagger)
                for span in doc.spans:
                    if span.type in ("PER", "ORG", "LOC"):
                        spans.append((span.start, span.stop, span.type, span.text))
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
