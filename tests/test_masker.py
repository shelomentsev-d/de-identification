import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

import pii_kit  # noqa: E402
from engine.masker import Masker  # noqa: E402


class MaskerExtractionTests(unittest.TestCase):
    def test_legacy_module_uses_extracted_masker(self):
        self.assertIs(pii_kit.Masker, Masker)

    def test_regex_only_mode_masks_without_ner(self):
        masker = Masker(enable_ner=False)
        cleaned = masker.mask_text("Телефон +7 999 123-45-67")
        self.assertEqual(cleaned, "Телефон [PHONE_1]")

    def test_mapping_and_counters_are_preserved(self):
        masker = Masker(enable_ner=False)
        self.assertEqual(masker.mask_text("+7 999 123-45-67; +7 999 123-45-67"), "[PHONE_1]; [PHONE_1]")
        self.assertEqual(masker.mapping, {"+7 999 123-45-67": "[PHONE_1]"})
        self.assertEqual(masker.counters["PHONE"], 1)

    def test_regex_fallback_survives_unavailable_ner(self):
        masker = Masker(enable_ner=True)
        masker._get_ner = lambda: (_ for _ in ()).throw(RuntimeError("model unavailable"))
        cleaned = masker.mask_text("Телефон +7 999 123-45-67")
        self.assertEqual(cleaned, "Телефон [PHONE_1]")
        self.assertTrue(masker._ner_unavailable)


if __name__ == "__main__":
    unittest.main()
