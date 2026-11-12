"""Executable legacy-refund contract for the schema-26 integration prerequisite.

Discovery exercises the current v1 reference catalogue. To probe a candidate
checkout's v2 catalogue, run this file with --engine-dir PATH --catalog-schema 2.
Both modes load the real modules from that directory; no gameplay is simulated
by a replacement resolver. These are Python reference-model tests, not Wurst,
whole-military-snapshot, packaging, or native Warcraft III acceptance.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import sys
import unittest
from pathlib import Path

ENGINE_DIR = Path(__file__).resolve().parents[2] / "_shared" / "engine"
CATALOG_SCHEMA = 1
SHIP = "test_ship"
ROUTE = "test_circuit"


def load_engine(directory: Path):
    """Load the selected complete source files without reusing another checkout."""
    def module(name, path):
        spec = importlib.util.spec_from_file_location(name, path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Cannot load reference engine: {path}")
        value = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(value)
        return value

    navigation = module("schema26_navigation_dependency", directory / "navigation.py")
    absent = object()
    previous = sys.modules.get("navigation", absent)
    try:
        sys.modules["navigation"] = navigation
        return module("schema26_voyage_reference", directory / "voyage_navigation.py")
    finally:
        if previous is absent:
            del sys.modules["navigation"]
        else:
            sys.modules["navigation"] = previous


def fixture(schema: int):
    """Synthetic valid circuit, with identical legacy economics in both modes."""
    celestial = {"kind": "modifier", "contentId": "celestial_credit"}
    coastal = {"kind": "modifier", "contentId": "coastal_credit"}
    world = {
        "technologies": [{"unlocks": [celestial, coastal]}],
        "navigationZones": [
            {"id": "harbor", "movementClasses": ["naval"],
             "connections": {"naval": ["sea"]}},
            {"id": "sea", "movementClasses": ["naval"],
             "connections": {"naval": ["harbor"]}},
        ],
        "strategicUnits": [{"id": SHIP, "kind": "ship",
                            "currentLocationId": "harbor",
                            "runtimeInstantiation": {"runtimeTemplateId": "test_vessel"}}],
    }
    route = {"id": ROUTE, "mapId": "test_map", "knownRegionId": "test_region",
             "days": 10, "dailyProvisions": 5, "dailyPositionFindingProvisions": 2,
             "zoneCircuit": ["harbor", "sea", "harbor"]}
    ship = {"forceId": SHIP, "mapId": "test_map", "stationZoneId": "harbor",
            "runtimeTemplateId": "test_vessel", "stationPosition": [0, 0],
            "observationCapable": True, "routeIds": [ROUTE]}
    data = {"schemaVersion": schema, "entitlement": celestial,
            "positionFindingReductionBasisPoints": 1000,
            "observationEquipmentMoneyCost": 120, "routes": [route], "ships": [ship]}
    if schema == 2:
        route.update(coastalBearingDays=[False, True] * 5, coastalBearings=["test_chart"])
        ship["coastalBearingCapable"] = True
        data["sources"] = [
            {"id": "celestial", "entitlement": celestial, "reductionBasisPoints": 1000,
             "qualification": "astronomical_observation", "equipmentSiteId": ""},
            {"id": "coastal", "entitlement": coastal, "reductionBasisPoints": 1000,
             "qualification": "coastal_bearings", "equipmentSiteId": "test_station"},
        ]
    return data, world


def legacy_save(credit=6000, equipment=True):
    # Three days consumed from an undiscounted 50-provision reservation.
    return {"schemaVersion": 1, "ships": {SHIP: {
        "equipment": equipment, "routeId": ROUTE, "elapsedDays": 3,
        "lastDay": 3, "reserved": 35, "creditBasisPoints": credit,
    }}}


class Schema26NavigationCompatibilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = load_engine(ENGINE_DIR)

    def setUp(self):
        data, world = fixture(CATALOG_SCHEMA)
        self.catalog = self.engine.VoyageCatalog(data, world)

    def restored(self, credit=6000, equipment=True):
        saved = legacy_save(credit, equipment)
        before = copy.deepcopy(saved)
        restored = self.catalog.validate(saved)
        self.assertEqual(before, saved, "validation mutated the legacy input")
        self.assertEqual(CATALOG_SCHEMA, restored["schemaVersion"])
        if CATALOG_SCHEMA == 2:
            self.assertEqual({"celestial": credit, "coastal": 0},
                             restored["ships"][SHIP]["sourceCredits"])
        return restored

    def assert_credit(self, state, expected):
        self.assertEqual(expected, state["creditBasisPoints"])
        if CATALOG_SCHEMA == 2:
            # Boolean legacy eligibility must not grant the new coastal effect.
            self.assertEqual({"celestial": expected, "coastal": 0}, state["sourceCredits"])

    def test_every_legacy_fraction_and_eligibility_pair_preserves_exact_refund(self):
        # 40,000 resumed voyages: every legal fractional value, equipment on/off,
        # and research eligibility on/off. Seven remaining days cost 35 supplies.
        for equipment in (False, True):
            for eligible in (False, True):
                increment = 14000 if equipment and eligible else 0
                for credit in range(10000):
                    state = self.restored(credit, equipment)["ships"][SHIP]
                    expected_refund, expected_credit = divmod(credit + increment, 10000)
                    self.assertEqual(expected_refund, self.catalog.resolve(state, 10, eligible))
                    self.assert_credit(state, expected_credit)
                    self.assertEqual(("", 0, 0, 0),
                                     (state["routeId"], state["elapsedDays"],
                                      state["lastDay"], state["reserved"]))
                    completed = copy.deepcopy(state)
                    self.assertEqual(0, self.catalog.resolve(state, 10, eligible))
                    self.assertEqual(completed, state)

    def test_6000_credit_releases_one_provision_after_two_more_days(self):
        state = self.restored()["ships"][SHIP]
        self.assertEqual(1, self.catalog.resolve(state, 5, True))
        self.assert_credit(state, 0)
        self.assertEqual((5, 5, 25), (state["elapsedDays"], state["lastDay"], state["reserved"]))
        before = copy.deepcopy(state)
        self.assertEqual(0, self.catalog.resolve(state, 5, True))
        self.assertEqual(before, state)

    def test_chunking_and_save_resume_match_one_callback(self):
        direct = self.restored()["ships"][SHIP]
        chunked_save = self.restored()
        refund = 0
        for day in (4, 5, 7, 10):
            refund += self.catalog.resolve(chunked_save["ships"][SHIP], day, True)
            chunked_save = self.catalog.validate(json.loads(json.dumps(chunked_save)))
        self.assertEqual(self.catalog.resolve(direct, 10, True), refund)
        self.assertEqual(direct, chunked_save["ships"][SHIP])

    def test_oversized_day_callback_never_refunds_future_travel(self):
        exact = self.restored()["ships"][SHIP]
        late = self.restored()["ships"][SHIP]
        self.assertEqual(self.catalog.resolve(exact, 10, True),
                         self.catalog.resolve(late, 100, True))
        self.assertEqual(exact, late)

    def test_interruption_retains_fraction_without_free_future_provisions(self):
        state = self.restored()["ships"][SHIP]
        self.assertEqual(35, self.catalog.interrupt(state))
        self.assert_credit(state, 6000)
        self.assertEqual(0, self.catalog.interrupt(state))
        self.assertEqual(0, self.catalog.resolve(state, 100, True))
        self.assertEqual(20, self.catalog.start(SHIP, state, ROUTE, 100, 70))
        self.assertEqual(1, self.catalog.resolve(state, 102, True))
        self.assert_credit(state, 0)
        self.assertEqual(40, self.catalog.interrupt(state))

    def test_eligibility_change_applies_only_to_its_elapsed_days(self):
        state = self.restored()["ships"][SHIP]
        self.assertEqual(0, self.catalog.resolve(state, 5, False))
        self.assert_credit(state, 6000)
        self.assertEqual(1, self.catalog.resolve(state, 8, True))
        self.assert_credit(state, 2000)
        self.assertEqual(0, self.catalog.resolve(state, 10, False))
        self.assert_credit(state, 2000)

    def test_migration_is_idempotent_detached_and_round_trippable(self):
        saved = legacy_save()
        migrated = self.catalog.validate(saved)
        self.assertEqual(migrated, self.catalog.validate(migrated))
        self.assertEqual(migrated, self.catalog.validate(json.loads(json.dumps(migrated))))
        migrated["ships"][SHIP]["equipment"] = False
        self.assertTrue(saved["ships"][SHIP]["equipment"])
        self.assertEqual(1, saved["schemaVersion"])

    def test_invalid_legacy_records_reject_without_mutating_input(self):
        for field, value in (("creditBasisPoints", -1), ("creditBasisPoints", 10000),
                             ("creditBasisPoints", True), ("reserved", 34),
                             ("elapsedDays", 10), ("equipment", 1),
                             ("routeId", "unknown"), ("lastDay", -1)):
            with self.subTest(field=field, value=value):
                saved = legacy_save()
                saved["ships"][SHIP][field] = value
                before = copy.deepcopy(saved)
                with self.assertRaises(self.engine.VoyageError):
                    self.catalog.validate(saved)
                self.assertEqual(before, saved)

    def test_legacy_record_cannot_smuggle_new_source_credit(self):
        saved = legacy_save()
        saved["ships"][SHIP]["sourceCredits"] = {"celestial": 6000, "coastal": 9000}
        before = copy.deepcopy(saved)
        with self.assertRaises(self.engine.VoyageError):
            self.catalog.validate(saved)
        self.assertEqual(before, saved)

    def test_v2_qualified_source_fraction_and_coastal_day_gating(self):
        if CATALOG_SCHEMA != 2:
            self.skipTest("typed-source accounting exists only in v2 catalogue")
        state = self.restored()["ships"][SHIP]
        # Offset 3 has valid coastal bearings. Offset 4 does not.
        self.assertEqual(0, self.catalog.resolve(state, 4, {"coastal"}))
        self.assertEqual(8000, state["creditBasisPoints"])
        self.assertEqual({"celestial": 6000, "coastal": 2000}, state["sourceCredits"])
        state = self.catalog.validate({"schemaVersion": 2, "ships": {SHIP: state}})["ships"][SHIP]
        before = copy.deepcopy(state)
        self.assertEqual(0, self.catalog.resolve(state, 5, {"coastal"}))
        self.assertEqual(before["creditBasisPoints"], state["creditBasisPoints"])
        self.assertEqual(before["sourceCredits"], state["sourceCredits"])
        # Offset 5 has bearings again; source fractions sum to an exact bucket.
        self.assertEqual(1, self.catalog.resolve(state, 6, {"coastal"}))
        self.assertEqual(0, state["creditBasisPoints"])
        self.assertEqual({"celestial": 6000, "coastal": 4000}, state["sourceCredits"])
        self.assertEqual(state, self.catalog.validate({"schemaVersion": 2, "ships": {SHIP: state}})["ships"][SHIP])

    def test_v2_rejects_disagreeing_source_bucket_without_mutation(self):
        if CATALOG_SCHEMA != 2:
            self.skipTest("typed-source accounting exists only in v2 catalogue")
        migrated = self.restored()
        original = copy.deepcopy(migrated)
        migrated["ships"][SHIP]["sourceCredits"]["coastal"] = 2000
        tampered = copy.deepcopy(migrated)
        with self.assertRaises(self.engine.VoyageError):
            self.catalog.validate(migrated)
        self.assertEqual(tampered, migrated)
        self.assertEqual(6000, original["ships"][SHIP]["creditBasisPoints"])

    def test_backwards_clock_and_failed_departure_preserve_state(self):
        state = self.restored()["ships"][SHIP]
        before = copy.deepcopy(state)
        with self.assertRaises(self.engine.VoyageError):
            self.catalog.resolve(state, 2, True)
        self.assertEqual(before, state)
        self.catalog.interrupt(state)
        before = copy.deepcopy(state)
        with self.assertRaises(self.engine.VoyageError):
            self.catalog.start(SHIP, state, ROUTE, 100, 49)
        self.assertEqual(before, state)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engine-dir", type=Path, default=ENGINE_DIR)
    parser.add_argument("--catalog-schema", type=int, choices=(1, 2), default=CATALOG_SCHEMA)
    args, unittest_args = parser.parse_known_args()
    ENGINE_DIR = args.engine_dir.resolve()
    CATALOG_SCHEMA = args.catalog_schema
    for name in ("navigation.py", "voyage_navigation.py"):
        payload = (ENGINE_DIR / name).read_bytes()
        blob = hashlib.sha1(b"blob " + str(len(payload)).encode() + b"\0" + payload).hexdigest()
        print(f"INPUT {name}: git-blob={blob}", file=sys.stderr)
    print(f"Python {sys.version.split()[0]}; catalogue schema {CATALOG_SCHEMA}; "
          "Python reference-model checks only", file=sys.stderr)
    unittest.main(argv=[sys.argv[0], *unittest_args])
