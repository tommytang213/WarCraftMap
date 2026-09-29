import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent / "_shared" / "engine"))

import campaign_save
from settlement import (
    RecordingSettlementAdapter,
    SettlementError,
    SettlementRuntime,
    SettlementSaveAdapter,
)

WORLD_PATH = ROOT / "scenario" / "world" / "world.json"


class SettlementRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.source = json.loads(WORLD_PATH.read_text(encoding="utf-8"))
        self.original = copy.deepcopy(self.source)
        self.objects = RecordingSettlementAdapter()
        self.runtime = SettlementRuntime(self.source, self.objects)

    def test_deterministic_initialization_lookup_and_separate_fields(self):
        self.assertEqual(152,len(self.runtime.ids())); self.assertTrue({"dover","london","paris","rouen","timbuktu","kilwa"}.issubset(self.runtime.ids()))
        london = self.runtime.require("london")
        self.assertEqual(
            ("england", "england", "greater_london", "capital", True,
             "atlantic_isles_land", "city_core_london", "defense_london"),
            (london.legal_owner_polity_id, london.controller_polity_id,
             london.province_id, london.kind, london.capturable,
             london.definition.navigation_zone_id, london.definition.city_core_id,
             london.definition.defense_layout_id),
        )
        self.assertTrue(london.operational)
        self.assertTrue(london.services["banking"])
        self.assertEqual(self.original, self.source)
        self.assertIsNone(self.runtime.lookup("missing"))

    def test_updates_and_snapshots_are_deterministic(self):
        self.assertTrue(self.runtime.update("london", controllerPolityId="france"))
        self.assertFalse(self.runtime.update("london", controllerPolityId="france"))
        self.assertTrue(self.runtime.set_service_available("london", "banking", False))
        first = self.runtime.snapshot()
        second = self.runtime.snapshot()
        self.assertEqual(first, second)
        london = next(item for item in first["settlements"] if item["id"] == "london")
        self.assertEqual("france", london["controllerPolityId"])
        self.assertFalse(london["services"]["banking"])
        self.assertNotIn("representation", json.dumps(first).lower())

    def test_representation_loss_and_recreation_preserves_authority(self):
        self.runtime.update("london", controllerPolityId="france")
        self.runtime.set_service_available("london", "banking", False)
        before = self.runtime.snapshot()
        first = self.runtime.create_representation("london")
        self.assertTrue(self.runtime.require("london").represented)
        self.assertTrue(self.runtime.destroy_representation("london"))
        self.assertEqual(before, self.runtime.snapshot())
        second = self.runtime.create_representation("london")
        self.assertNotEqual(first, second)
        self.assertEqual(before, self.runtime.snapshot())
        self.assertEqual(["create", "destroy", "create"], [op[0] for op in self.objects.operations])

    def test_reconstructs_operational_representations_through_adapter(self):
        self.runtime.update("paris", operational=False)
        self.runtime.reconstruct_representations()
        created = [op[1] for op in self.objects.operations if op[0] == "create"]
        self.assertNotIn("paris",created); self.assertEqual(151,len(created)); self.assertIn("london",created)
        self.assertFalse(self.runtime.require("paris").represented)
        self.assertTrue(self.runtime.require("london").represented)

    def test_missing_and_inconsistent_definition_references_are_rejected(self):
        cases = []
        for field, value, pattern in (
            ("provinceId", "missing_province", "missing province"),
            ("legalOwnerPolityId", "missing_polity", "missing legal owner polity"),
            ("controllerPolityId", "missing_polity", "missing controller polity"),
            ("navigationZoneId", "missing_zone", "missing navigation zone"),
            ("cityCoreId", "missing_core", "missing city core"),
            ("defenseLayoutId", "missing_layout", "missing defense layout"),
        ):
            candidate = copy.deepcopy(self.source)
            candidate["settlements"][0][field] = value
            cases.append((candidate, pattern))
        inconsistent = copy.deepcopy(self.source)
        inconsistent["provinces"][0]["settlementIds"] = []
        cases.append((inconsistent, "does not include settlement"))
        for candidate, pattern in cases:
            with self.subTest(pattern=pattern), self.assertRaisesRegex(SettlementError, pattern):
                SettlementRuntime(candidate, RecordingSettlementAdapter())

    def test_missing_template_references_are_rejected(self):
        core = copy.deepcopy(self.source)
        core["cityCores"][0]["objectTemplateId"] = "missing_template"
        with self.assertRaisesRegex(SettlementError, "missing object template"):
            SettlementRuntime(core, RecordingSettlementAdapter())
        layout = copy.deepcopy(self.source)
        layout["defenseLayouts"][0]["objectTemplateIds"] = ["missing_template"]
        with self.assertRaisesRegex(SettlementError, "missing object template"):
            SettlementRuntime(layout, RecordingSettlementAdapter())

    def test_rejected_restoration_leaves_campaign_and_objects_unchanged(self):
        self.runtime.create_representation("london")
        baseline = self.runtime.snapshot()
        operations = list(self.objects.operations)
        bad = copy.deepcopy(baseline)
        london = next(item for item in bad["settlements"] if item["id"] == "london")
        london["provinceId"] = "kent"
        with self.assertRaisesRegex(SettlementError, "inconsistent province"):
            self.runtime.restore(bad)
        self.assertEqual(baseline, self.runtime.snapshot())
        self.assertEqual(operations, self.objects.operations)
        self.assertTrue(self.runtime.require("london").represented)

    def test_campaign_save_round_trip_restores_state_and_representations(self):
        adapter = SettlementSaveAdapter(self.runtime, {"calendar": {"day": 1}})
        storage = campaign_save.MemorySaveStorage()
        players = {"main": {"characterId": "captain"}}
        manager = campaign_save.CampaignSaveManager(
            build_version="1", scenario_id="test", scenario_version="1", storage=storage,
            capture_state=lambda: (adapter.capture_world(), players),
            validate_state=lambda world, loaded: adapter.validate_world(world),
            reconstruct_runtime=lambda world, loaded: adapter.reconstruct(world),
            activate_state=lambda world, loaded, rebuilt: adapter.activate(world, rebuilt),
            is_save_safe=lambda: True,
        )
        self.runtime.update("london", controllerPolityId="france")
        self.runtime.set_service_available("london", "banking", False)
        slot = campaign_save.SaveSlot("manual", 1)
        manager.save(slot, "now")
        payload = storage.read(slot.stable_id)
        self.assertNotIn(b"representation_", payload)
        self.runtime.update("london", controllerPolityId="england")
        self.runtime.set_service_available("london", "banking", True)
        manager.load(slot)
        london = self.runtime.require("london")
        self.assertEqual("france", london.controller_polity_id)
        self.assertFalse(london.services["banking"])
        self.assertTrue(london.represented)

    def test_legacy_world_migration_is_explicit_and_non_mutating(self):
        adapter = SettlementSaveAdapter(self.runtime, {})
        legacy = {"calendar": {"day": 3}}
        migrated = adapter.migrate_legacy_world(legacy)
        self.assertNotIn("settlementState", legacy)
        self.assertEqual(self.runtime.snapshot(), migrated["settlementState"])
        with self.assertRaisesRegex(SettlementError, "missing settlementState"):
            adapter.validate_world(legacy)


if __name__ == "__main__":
    unittest.main()
