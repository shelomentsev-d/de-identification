import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

import pii_kit  # noqa: E402
from engine.rules import LABELS, REGEX_RULES, filter_overlaps  # noqa: E402


class RulesTests(unittest.TestCase):
    def test_legacy_module_exports_same_rule_objects(self):
        self.assertIs(pii_kit.LABELS, LABELS)
        self.assertIs(pii_kit.REGEX_RULES, REGEX_RULES)
        self.assertIs(pii_kit.filter_overlaps, filter_overlaps)

    def test_long_numeric_rules_precede_shorter_rules(self):
        names = [label for label, _pattern in REGEX_RULES]
        self.assertLess(names.index("ACCOUNT"), names.index("INN"))
        self.assertLess(names.index("OGRNIP"), names.index("INN"))

    def test_filter_overlaps_prefers_longest_span_at_same_start(self):
        spans = [
            (0, 5, "A", "short"),
            (0, 10, "B", "long"),
            (8, 12, "C", "overlap"),
            (12, 14, "D", "next"),
        ]
        self.assertEqual(
            filter_overlaps(spans),
            [(0, 10, "B", "long"), (12, 14, "D", "next")],
        )


if __name__ == "__main__":
    unittest.main()
