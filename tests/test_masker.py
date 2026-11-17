import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

import de_Identification  # noqa: E402
from engine.masker import Masker  # noqa: E402


class MaskerExtractionTests(unittest.TestCase):
    def test_legacy_module_uses_extracted_masker(self):
        self.assertIs(de_Identification.Masker, Masker)

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

    def test_masks_russian_names_and_organizations_without_ner(self):
        masker = Masker(enable_ner=False)
        cleaned = masker.mask_text(
            "ООО «МИРА», Марковой Марины Викторовны, ИП Канайлов Михаил Сергеевич"
        )
        self.assertEqual(cleaned, "[ORG_1], [PER_1], ИП [PER_2]")

    def test_masks_all_dates_in_contract_style_text(self):
        masker = Masker(enable_ner=False)
        cleaned = masker.mask_text("с 12.11.2026 г. по 30.11.2026г.")
        self.assertEqual(cleaned, "с [DATE_1] по [DATE_2]")

    def test_masks_iso_and_dashed_dates(self):
        masker = Masker(enable_ner=False)
        cleaned = masker.mask_text("Протокол 2026-07-03 и дата 03-07-2026.")
        self.assertEqual(cleaned, "Протокол [DATE_1] и дата [DATE_2].")

    def test_masks_ip_name_without_replacing_business_label(self):
        masker = Masker(enable_ner=False)
        cleaned = masker.mask_text(
            "Индивидуальный Предприниматель Канайлов Михаил Сергеевич"
        )
        self.assertEqual(cleaned, "Индивидуальный Предприниматель [PER_1]")

    def test_masks_initials_written_before_surname(self):
        masker = Masker(enable_ner=False)
        cleaned = masker.mask_text("_____________________М.В. Маркова /М.С. Канайлов/")
        self.assertEqual(cleaned, "_____________________[PER_1] /[PER_2]/")

    def test_masks_postal_addresses(self):
        masker = Masker(enable_ner=False)
        cleaned = masker.mask_text(
            "Юридический адрес: 630020, г. Новосибирск, ул. Окружная, д. 33, 3 этаж. "
            "190068, г. Санкт-Петербург, пер. Макаренко, д. 10, кв.12"
        )
        self.assertNotIn("Новосибирск", cleaned)
        self.assertNotIn("Окружная", cleaned)
        self.assertNotIn("Санкт-Петербург", cleaned)
        self.assertNotIn("Макаренко", cleaned)
        self.assertNotIn("д. 33", cleaned)
        self.assertNotIn("кв.12", cleaned)
        self.assertNotIn("3 этаж", cleaned)
        self.assertIn("Юридический адрес:", cleaned)
        self.assertIn("[ZIP_1]", cleaned)
        self.assertIn("[LOC_1]", cleaned)

    def test_masks_bank_names_and_branch(self):
        masker = Masker(enable_ner=False)
        cleaned = masker.mask_text(
            'Банк ВТБ (публичное акционерное общество) Банк ВТБ (ПАО) '
            'ФИЛИАЛ "НОВОСИБИРСКИЙ" АО "АЛЬФА-БАНК"'
        )
        self.assertNotIn("ВТБ", cleaned)
        self.assertNotIn("НОВОСИБИРСКИЙ", cleaned)
        self.assertNotIn("АЛЬФА-БАНК", cleaned)
        self.assertEqual(cleaned.count("[ORG_"), 4)

    def test_masks_account_split_into_six_groups(self):
        masker = Masker(enable_ner=False)
        cleaned = masker.mask_text("к/с: 30101 810 145 250 000 411")
        self.assertEqual(cleaned, "к/с: [ACCOUNT_1]")
        self.assertNotIn("411", cleaned)

    def test_labels_kpp_instead_of_bic(self):
        masker = Masker(enable_ner=False)
        cleaned = masker.mask_text(
            "ИНН/КПП 5405479197/541001001 КПП: 770943002 БИК: 044525411"
        )
        self.assertEqual(
            cleaned,
            "ИНН/КПП [INN_1]/[KPP_1] КПП: [KPP_2] БИК: [BIC_1]",
        )
        self.assertEqual(masker.mapping["541001001"], "[KPP_1]")
        self.assertEqual(masker.mapping["044525411"], "[BIC_1]")


if __name__ == "__main__":
    unittest.main()
