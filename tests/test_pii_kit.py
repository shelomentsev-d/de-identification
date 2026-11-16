#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Baseline tests for the current pii_kit.py behavior.

These tests intentionally describe the existing prototype before extracting
an engine package. They should be kept green during the first refactor.
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

import pii_kit  # noqa: E402


class MaskerTests(unittest.TestCase):
    def test_masks_supported_regex_entities(self):
        text = (
            "ИНН 7707083893, ОГРН 1027700132195, ОГРНИП 304774600123456, "
            "СНИЛС 123-456-789 00, паспорт 45 12 345678, счет 40702810123456789012, "
            "БИК 044525225, индекс 123456, телефон +7 (999) 123-45-67, "
            "email test.person@example.ru, дата 15.03.1985 г."
        )

        masker = pii_kit.Masker()
        cleaned = masker.mask_text(text)

        for label in (
            "INN",
            "OGRN",
            "OGRNIP",
            "SNILS",
            "PASSPORT",
            "ACCOUNT",
            "BIC",
            "ZIP",
            "PHONE",
            "EMAIL",
            "DATE",
        ):
            self.assertRegex(cleaned, rf"\[{label}_1\]")
        self.assertEqual(len(masker.mapping), 11)
        self.assertNotIn("7707083893", cleaned)
        self.assertNotIn("test.person@example.ru", cleaned)

    def test_repeated_value_gets_same_token(self):
        masker = pii_kit.Masker()

        cleaned = masker.mask_text("Телефон +7 999 123-45-67 и снова +7 999 123-45-67.")

        self.assertEqual(cleaned.count("[PHONE_1]"), 2)
        self.assertEqual(len(masker.mapping), 1)
        self.assertEqual(masker.counters["PHONE"], 1)

    def test_overlapping_spans_keep_longest_at_same_start(self):
        spans = [
            (0, 5, "A", "short"),
            (0, 10, "B", "long"),
            (8, 12, "C", "overlap"),
            (12, 14, "D", "next"),
        ]

        self.assertEqual(
            pii_kit.filter_overlaps(spans),
            [(0, 10, "B", "long"), (12, 14, "D", "next")],
        )


class RestoreTests(unittest.TestCase):
    def test_restore_accepts_tolerant_token_forms(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            answer = root / "answer.txt"
            keys = root / "document_keys.json"
            answer.write_text(
                "[ORG_1] (ORG_1) «ORG_1» ORG_1 [PHONE_1]",
                encoding="utf-8",
            )
            keys.write_text(
                json.dumps(
                    {
                        "mapping": {
                            "ООО «Ромашка»": "[ORG_1]",
                            "+7 999 123-45-67": "[PHONE_1]",
                        }
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            args = type("Args", (), {"answer_file": str(answer), "keys": str(keys)})
            pii_kit.cmd_restore(args)

            restored = (root / "answer_restored.txt").read_text(encoding="utf-8")
            self.assertEqual(
                restored,
                "ООО «Ромашка» ООО «Ромашка» ООО «Ромашка» ООО «Ромашка» "
                "+7 999 123-45-67",
            )


class FileProcessingTests(unittest.TestCase):
    def test_process_text_keeps_original_and_writes_clean_copy(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "договор test.txt"
            original = "Контакт: +7 999 123-45-67\n"
            source.write_text(original, encoding="utf-8")

            masker = pii_kit.Masker()
            output = pii_kit.process_text(source, masker)

            self.assertEqual(output.name, "договор test_clean.txt")
            self.assertEqual(source.read_text(encoding="utf-8"), original)
            self.assertEqual(output.read_text(encoding="utf-8"), "Контакт: [PHONE_1]\n")
            self.assertEqual(masker.mapping, {"+7 999 123-45-67": "[PHONE_1]"})


if __name__ == "__main__":
    unittest.main()
