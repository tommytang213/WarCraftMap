import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent / "_shared" / "engine"))

from city_capture import CityCaptureError, CityCaptureRuntime, CityCaptureSaveAdapter, RecordingCityCaptureAdapter
from diplomacy import DiplomacyRuntime
from polity import PolityRuntime
from province import ProvinceRuntime
from settlement import RecordingSettlementAdapter, SettlementRuntime


class CityCaptureTests(unittest.TestCase):
    def setUp(self):
        self.world = json.loads((ROOT / "scenario/world/world.json").read_text())
        self.polities = PolityRuntime(self.world)
        self.provinces = ProvinceRuntime(self.world, self.polities)
        self.settlements = SettlementRuntime(self.world, RecordingSettlementAdapter())
        self.diplomacy = DiplomacyRuntime(self.polities, self.provinces, self.settlements)
        self.adapter = RecordingCityCaptureAdapter()
        self.capture = CityCaptureRuntime(self.settlements, self.provinces, self.diplomacy, self.adapter)
        self.capture.reconstruct("london")

    def war(self):
        self.diplomacy.declare_war("channel_war", "england", "france")

    def test_valid_capture_changes_control_not_ownership_and_has_typed_order(self):
        self.war()
        event = self.capture.notify_object_loss(*self.capture.representation_token("london"), "city_core", attacker_polity_id="france", now_seconds=10)
        city, province = self.settlements.require("london"), self.provinces.require("greater_london")
        self.assertEqual(("england", "france"), (city.legal_owner_polity_id, city.controller_polity_id))
        self.assertEqual(("england", "france"), (province.legal_owner_polity_id, province.controller_polity_id))
        self.assertEqual((1, "city_captured", "channel_war"), (event.sequence, event.kind, event.conflict_id))
        self.assertEqual(["stage", "commit", "remove_protection", "stage", "commit"], [x[0] for x in self.adapter.operations])

    def test_rejects_illegal_friendly_uncapturable_and_stale_events(self):
        with self.assertRaisesRegex(CityCaptureError, "active conflict"):
            self.capture.capture("london", "france", 0)
        self.war()
        with self.assertRaisesRegex(CityCaptureError, "active conflict"):
            self.capture.capture("london", "england", 0)
        self.settlements.update("london", capturable=False)
        with self.assertRaisesRegex(CityCaptureError, "not capturable"):
            self.capture.capture("london", "france", 0)
        self.settlements.update("london", capturable=True)
        self.capture.capture("london", "france", 0)
        captured = self.capture.snapshot()
        self.assertIsNone(self.capture.notify_object_loss("london", 0, "city_core", attacker_polity_id="france", now_seconds=6))
        self.assertEqual(captured, self.capture.snapshot())

    def test_atomic_adapter_failure_and_defense_recovery_preserve_authority(self):
        self.war()
        city_before, province_before = self.settlements.snapshot(), self.provinces.snapshot()
        self.adapter.fail_stage = True
        with self.assertRaisesRegex(RuntimeError, "reconstruction"):
            self.capture.capture("london", "france", 0)
        self.adapter.fail_stage = False; self.adapter.fail_commit = True
        with self.assertRaisesRegex(RuntimeError, "commit"):
            self.capture.capture("london", "france", 0)
        self.assertEqual(city_before, self.settlements.snapshot())
        self.assertEqual(province_before, self.provinces.snapshot())
        self.adapter.fail_commit = False
        services = dict(self.settlements.require("london").services)
        self.capture.notify_object_loss("london", 0, "defense", now_seconds=1)
        self.assertEqual(services, dict(self.settlements.require("london").services))

    def test_exact_five_second_boundary_and_unrelated_protection_survives(self):
        self.war(); self.capture.capture("london", "france", 20)
        representation = self.adapter.current["london"]
        self.adapter.add_protection("london", "quest_protection")
        with self.assertRaisesRegex(CityCaptureError, "cooldown"):
            self.capture.capture("london", "england", 24.999)
        self.capture.advance(24.999)
        self.assertTrue(any(x.startswith("city_capture:") for x in representation["protectionSources"]))
        self.capture.advance(25)
        self.assertEqual({"quest_protection"}, representation["protectionSources"])

    def test_save_load_during_cooldown_and_checkpoint_equivalence(self):
        self.war(); self.capture.capture("london", "france", 3)
        saved = self.capture.snapshot()
        save_adapter = CityCaptureSaveAdapter(self.capture, {"calendar": {"second": 4}})
        self.assertEqual(saved, save_adapter.capture_world()["cityCaptureState"])
        self.assertIn("cityCaptureState", save_adapter.migrate_legacy_world({}))
        replacement = RecordingCityCaptureAdapter()
        resumed = CityCaptureRuntime(self.settlements, self.provinces, self.diplomacy, replacement)
        resumed.restore(copy.deepcopy(saved), now_seconds=4)
        resumed.advance(8); self.capture.advance(8)
        self.assertEqual(self.capture.snapshot(), resumed.snapshot())
        self.assertFalse(any(x.startswith("city_capture:") for x in replacement.current["london"]["protectionSources"]))


if __name__ == "__main__":
    unittest.main()
