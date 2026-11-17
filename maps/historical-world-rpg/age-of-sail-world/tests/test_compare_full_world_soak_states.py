"""Read-only regression for exact-input soak state diagnostic tooling.

Helper tests never replace the existing real authored-world full-scenario suite.
"""
import hashlib
import importlib.util
import json
import unittest
from pathlib import Path
from types import SimpleNamespace

PROJECT = Path(__file__).resolve().parents[1]
CONFIG = PROJECT / "scenario/benchmarks/full-world-soak.json"
SPEC = importlib.util.spec_from_file_location(
    "compare_full_world_soak_states", PROJECT / "tooling/compare_full_world_soak_states.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class SoakStateComparisonToolTests(unittest.TestCase):
    def test_manifest_covers_authentic_full_world_sources_and_exact_bytes(self):
        config = json.loads(CONFIG.read_text(encoding="utf-8"))
        manifest = MODULE._manifest(CONFIG, config)
        self.assertEqual({"config", *config["sources"]}, set(manifest))
        for name, relative in [("config", CONFIG), *(
            (n, (CONFIG.parent / p).resolve()) for n, p in config["sources"].items()
        )]:
            content = Path(relative).read_bytes()
            self.assertEqual(hashlib.sha256(content).hexdigest(), manifest[name]["sha256"])
            self.assertEqual(len(content), manifest[name]["sizeBytes"])

    def test_field_summary_is_bounded_and_detects_exact_domain_id_changes(self):
        summary = MODULE._summarize(["id_a", "id_b"], ["id_b", "id_c"])
        self.assertEqual(["id_a"], summary["removedIds"])
        self.assertEqual(["id_c"], summary["addedIds"])
        self.assertNotEqual(summary["referenceHash"], summary["candidateHash"])
        changes = MODULE._summarize({"a": 1, "b": 2}, {"a": 1, "b": 3, "c": 4})
        self.assertEqual(["b"], changes["changedKeys"])
        self.assertEqual(["c"], changes["addedKeys"])

    def test_mismatched_timeline_or_source_set_fails_closed(self):
        profile = SimpleNamespace(seeds=(1450, 1701), step_days=365, jump_days=36500,
                                  checkpoint_date="1635-01-01", representation_limit=64)
        a = {"logicalTickDays": 30, "workload": {"quests": 1}, "sources": {"world": "a"}}
        b = {"logicalTickDays": 30, "workload": {"quests": 1}, "sources": {"world": "b"}}
        MODULE._check_compatible(a, b, profile, profile)
        for key, replacement in (("logicalTickDays", 31), ("workload", {"quests": 2}),
                                 ("sources", {"world": "b", "extra": "c"})):
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, "incomparable"):
                MODULE._check_compatible(a, {**b, key: replacement}, profile, profile)
        with self.assertRaisesRegex(ValueError, "step_days"):
            MODULE._check_compatible(a, b, profile, SimpleNamespace(**{**vars(profile), "step_days": 30}))


if __name__ == "__main__":
    unittest.main()
