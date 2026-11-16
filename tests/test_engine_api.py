import json
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from engine import (  # noqa: E402
    DependencyError,
    InputFileError,
    MaskingConfig,
    ProcessingError,
    UnsupportedFormatError,
    load_mapping,
    mask,
    restore,
)


class EngineApiTests(unittest.TestCase):
    def test_mask_returns_artifacts_and_keeps_legacy_key_format(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "договор.txt"
            source.write_text("Контакт: +7 999 123-45-67", encoding="utf-8")

            result = mask(source, MaskingConfig(enable_ner=False))

            self.assertEqual(result.output_path.name, "договор_clean.txt")
            self.assertEqual(result.keys_path.name, "договор_keys.json")
            self.assertEqual(result.total_entities, 1)
            self.assertEqual(
                json.loads(result.keys_path.read_text(encoding="utf-8")),
                {"mapping": {"+7 999 123-45-67": "[PHONE_1]"}},
            )

    def test_restore_reports_missing_tokens_without_exposing_values(self):
        result = restore(
            "Ответ: [ORG_1].",
            {"ООО «Ромашка»": "[ORG_1]", "+7 999 123-45-67": "[PHONE_1]"},
        )

        self.assertEqual(result.text, "Ответ: ООО «Ромашка».")
        self.assertEqual(result.replacements, 1)
        self.assertEqual(result.missing_tokens, ("[PHONE_1]",))

    def test_restore_accepts_token_without_separator(self):
        result = restore("ORG1 и [ORG_1]", {"Компания": "[ORG_1]"})
        self.assertEqual(result.text, "Компания и Компания")
        self.assertEqual(result.replacements, 2)

    def test_mask_rejects_missing_and_unsupported_inputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaises(InputFileError):
                mask(root / "missing.txt")

            unsupported = root / "file.bin"
            unsupported.write_bytes(b"data")
            with self.assertRaises(UnsupportedFormatError):
                mask(unsupported)

    def test_corrupt_document_is_typed_processing_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "document.docx"
            source.write_bytes(b"not-a-real-docx")
            with self.assertRaises(ProcessingError):
                mask(source)

    def test_missing_processor_dependency_is_typed_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "document.docx"
            source.write_bytes(b"not-a-real-docx")
            with mock.patch.dict(sys.modules, {"docx": None}):
                with self.assertRaises(DependencyError):
                    mask(source)

    def test_load_mapping_reads_legacy_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "keys.json"
            path.write_text(
                json.dumps({"mapping": {"значение": "[PER_1]"}}, ensure_ascii=False),
                encoding="utf-8",
            )
            self.assertEqual(load_mapping(path), {"значение": "[PER_1]"})


if __name__ == "__main__":
    unittest.main()
