import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


CATEGORY_ROOT = Path(__file__).resolve().parents[2]
WORLD_PATH = Path(__file__).resolve().parents[1] / "scenario" / "world" / "world.json"


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


validator = load_module("validate_world_navigation_tests", CATEGORY_ROOT / "_shared" / "tooling" / "validate_world.py")
navigation = load_module("navigation", CATEGORY_ROOT / "_shared" / "engine" / "navigation.py")


class NavigationContractTests(unittest.TestCase):
    def data(self):
        return json.loads(WORLD_PATH.read_text(encoding="utf-8"))

    def assert_invalid(self, data):
        with tempfile.NamedTemporaryFile("w", suffix=".json", encoding="utf-8", delete=False) as stream:
            json.dump(data, stream)
            path = Path(stream.name)
        try:
            with self.assertRaises(validator.ValidationError):
                validator.validate(path)
        finally:
            path.unlink(missing_ok=True)

    def zones(self):
        return {zone["id"]: zone for zone in self.data()["navigationZones"]}

    def candidate(self, zone_id, ident):
        return {
            "id": ident, "zoneId": zone_id, "position": {"x": 1, "y": 2},
            "movementClasses": ["naval"], "verifiedSafe": True,
        }

    def choose(self, **overrides):
        arguments = {
            "unit_category": "mobile", "movement_class": "naval",
            "current_zone_id": "english_channel",
            "last_safe_point": {"zoneId": "english_channel", "x": 1, "y": 2},
            "nearby_safe_points": [],
            "recovery_anchors": [self.candidate("north_sea_atlantic", "anchor")],
            "zones": self.zones(),
        }
        arguments.update(overrides)
        return navigation.choose_recovery_destination(**arguments)

    def test_all_movement_classes_are_supported(self):
        self.assertEqual({"land", "naval", "amphibious", "flying"}, navigation.MOVEMENT_CLASSES)

    def test_connections_must_be_reciprocal_per_movement_class(self):
        data = self.data()
        channel = next(zone for zone in data["navigationZones"] if zone["id"] == "english_channel")
        channel["connections"]["naval"] = []
        self.assert_invalid(data)

    def test_active_unit_last_safe_zone_must_be_connected(self):
        data = self.data()
        data["activeUnitNavigationStates"][0]["lastSafePosition"]["zoneId"] = "decorative_lake"
        self.assert_invalid(data)

    def test_navigation_state_is_only_for_active_units(self):
        data = self.data()
        data["activeUnitNavigationStates"][0]["unitId"] = "english_guard_formation"
        self.assert_invalid(data)

    def test_recovery_priority_is_nearby_then_last_safe_then_anchor(self):
        nearby = self.candidate("english_channel", "nearby")
        self.assertEqual("nearby_safe_point", self.choose(nearby_safe_points=[nearby])["source"])
        self.assertEqual("last_safe_point", self.choose()["source"])
        self.assertEqual("recovery_anchor", self.choose(last_safe_point=None)["source"])

    def test_unverified_or_disconnected_candidates_fail_without_destination(self):
        lake = self.candidate("decorative_lake", "lake")
        unverified = self.candidate("english_channel", "unverified")
        unverified["verifiedSafe"] = False
        result = self.choose(last_safe_point=None, nearby_safe_points=[lake, unverified], recovery_anchors=[lake])
        self.assertIsNone(result)

    def test_structures_and_dummies_are_ineligible(self):
        self.assertIsNone(self.choose(unit_category="structure"))
        self.assertIsNone(self.choose(unit_category="dummy"))

    def test_land_cannot_cross_disconnected_land(self):
        zones = self.zones()
        zones["island_land"] = {"id": "island_land", "movementClasses": ["land"], "connections": {"land": []}}
        destination = {"zoneId": "island_land", "movementClasses": ["land"], "verifiedSafe": True}
        result = navigation.choose_recovery_destination(
            unit_category="mobile", movement_class="land", current_zone_id="western_europe_land",
            last_safe_point=None, nearby_safe_points=[destination], recovery_anchors=[], zones=zones,
        )
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
