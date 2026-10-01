import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "_shared" / "engine"))
import campaign_save as saves
import release_save_compatibility as release

MANIFEST = Path(__file__).resolve().parents[1] / "scenario/compatibility/release-save-v1.json"


class ReleaseSaveCompatibilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = release.load_manifest(MANIFEST)
        cls.fixtures = [release.expand_fixture(cls.manifest, item) for item in cls.manifest["fixtures"]]

    def test_matrix_is_derived_from_complete_registered_paths(self):
        registry = saves.MigrationRegistry()
        self.assertEqual((1, 2, 3, 4), registry.supported_source_versions())
        self.assertEqual((1, 2, 3, 4), registry.migration_path(1))
        partial = saves.MigrationRegistry(current_version=5)
        partial.register(4, lambda d: dict(d, schemaVersion=5))
        self.assertEqual((4, 5), partial.supported_source_versions())
        with self.assertRaises(saves.IncompatibleSaveError): partial.migration_path(3)

    def test_every_immutable_fixture_migrates_and_resaves_deterministically(self):
        results = [release.validate_release_fixture(f, self.manifest["budgets"]) for f in self.fixtures]
        self.assertEqual([1, 2, 3, 4], [r["schemaVersion"] for r in results])
        self.assertEqual({self.fixtures[0]["expectedAuthoritySha256"]}, {r["authoritySha256"] for r in results})
        self.assertEqual(["migrated", "migrated", "migrated", "compatible"], [r["status"] for r in results])

    def test_direct_multistep_and_idempotent_paths_preserve_all_authority(self):
        expected = self.manifest["expectedCurrentAuthority"]
        for fixture in self.fixtures:
            raw = release.fixture_payload(fixture)
            original = bytes(raw)
            first = saves.load_save(raw)
            second = saves.load_save(release.canonical(first))
            self.assertEqual(expected, first["state"])
            self.assertEqual(first["state"], second["state"])
            self.assertEqual(original, raw)
            ids = self._stable_ids(first["state"])
            self.assertEqual(len(ids), len(set(ids)))

    def test_corruption_and_unsupported_metadata_are_bounded_and_non_mutating(self):
        raw = release.fixture_payload(self.fixtures[-1])
        cases = [raw[:len(raw)//2]]
        for field, value in (("schemaVersion", 99), ("buildVersion", "wrong-build")):
            item = json.loads(raw); item[field] = value; item["integrity"]["checksum"] = saves._checksum(item)
            cases.append(release.canonical(item))
        item = json.loads(raw); item["scenario"]["id"] = "wrong_scenario"; item["integrity"]["checksum"] = saves._checksum(item)
        cases.append(release.canonical(item))
        for candidate in cases:
            before = bytes(candidate)
            status, message, loaded = release.classify_load(candidate)
            self.assertIn(status, {"corrupt", "unsupported"})
            self.assertLessEqual(len(message), 80)
            self.assertIsNone(loaded)
            self.assertEqual(before, candidate)

    def test_migration_failure_is_wrapped_and_source_is_preserved(self):
        raw = release.fixture_payload(self.fixtures[0]); before = bytes(raw)
        registry = saves.MigrationRegistry()
        registry._migrations[1] = lambda _d: (_ for _ in ()).throw(RuntimeError("private details"))
        status, message, loaded = release.classify_load(raw, registry)
        self.assertEqual(("unsupported", release.DIAGNOSTICS["unsupported"], None), (status, message, loaded))
        self.assertEqual(before, raw)

    @staticmethod
    def _stable_ids(authority):
        ids = []
        for container in authority.values():
            if isinstance(container, dict): ids.extend(str(key) for key in container)
        return ids


if __name__ == "__main__": unittest.main()
