import copy
import json
import sys
import unittest
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT.parent / "_shared" / "engine"))

from world_integrity import (FieldMatch, IntegrityError, IntegrityPolicy, ReconstructionError,
                             RecordingReconstructionAdapter, Reference, recover, scan, state_hash)


DOMAINS = ("polities", "provinces", "settlements", "ownershipControl", "sovereignty",
           "diplomacy", "armies", "fleets", "characters", "economy", "technology",
           "quests", "treasures", "routes", "schedules", "persistenceIndexes")


def full_world_fixture():
    world = json.loads((PROJECT / "scenario/world/world.json").read_text())
    maps = json.loads((PROJECT / "physical-maps.json").read_text())["physicalMaps"]
    polities = [{"id": x["id"]} for x in world["polities"]]
    provinces = [{"id": x["id"], "controllerPolityId": x["controllerPolityId"]} for x in world["provinces"]]
    settlements = [{"id": x["id"], "provinceId": x["provinceId"],
                    "controllerPolityId": x["controllerPolityId"], "serviceIds": x["serviceIds"],
                    "cityCoreId": x.get("cityCoreId"), "defenseLayoutId": x.get("defenseLayoutId"),
                    "objectKinds": ["city_core", "defense", "civilian", "unit", "effect"]}
                   for x in world["settlements"]]
    authority = {
        "polities": polities, "provinces": provinces, "settlements": settlements,
        "ownershipControl": [{"id": f"control_{x['id']}", "settlementId": x["id"],
                              "controllerPolityId": x["controllerPolityId"], "captureCooldownUntil": 0}
                             for x in settlements],
        "sovereignty": [{"id": x["id"], "polityId": x["legalOwner"]["id"]} for x in world["territorialHoldings"]],
        "diplomacy": [{"id": "war_fixture", "firstPolityId": "england", "secondPolityId": "france", "status": "active"}],
        "armies": [{"id": x["id"], "ownerPolityId": x["legalOwnerPolityId"]} for x in world["armies"]],
        "fleets": [{"id": x["id"], "ownerPolityId": x["legalOwnerPolityId"]} for x in world["fleets"]],
        "characters": [{"id": x["id"], "polityId": x["allegiancePolityId"]} for x in world["characters"]],
        "economy": [{"id": "global_market", "settlementId": settlements[0]["id"], "stock": 100}],
        "technology": [{"id": x["id"]} for x in world["technologies"]],
        "quests": [{"id": x["id"]} for x in world["quests"]],
        "treasures": [{"id": x["id"]} for x in json.loads((PROJECT / "scenario/treasures/age-of-sail.json").read_text())["treasures"]],
        "routes": [{"id": "integrity_route", "originSettlementId": settlements[0]["id"], "destinationSettlementId": settlements[-1]["id"]}],
        "schedules": [{"id": "integrity_schedule", "targetPolityId": polities[0]["id"], "due": 100}],
        "persistenceIndexes": [{"id": f"map_{x['id']}", "mapId": x["id"], "visited": x.get("bootstrap", False)} for x in maps],
    }
    return {"format": "warcraftmap_world_integrity_v1", "schemaVersion": 1,
            "authoritative": authority, "transactions": [], "indexes": {},
            "runtimeRepresentations": {}, "reconstruction": {"status": "interrupted"}}


POLICY = IntegrityPolicy(
    DOMAINS,
    references=(
        Reference("provinces", "controllerPolityId", "polities"),
        Reference("settlements", "provinceId", "provinces"), Reference("settlements", "controllerPolityId", "polities"),
        Reference("ownershipControl", "settlementId", "settlements"), Reference("ownershipControl", "controllerPolityId", "polities"),
        Reference("sovereignty", "polityId", "polities"), Reference("diplomacy", "firstPolityId", "polities"),
        Reference("diplomacy", "secondPolityId", "polities"), Reference("armies", "ownerPolityId", "polities"),
        Reference("fleets", "ownerPolityId", "polities"), Reference("characters", "polityId", "polities"),
        Reference("economy", "settlementId", "settlements"), Reference("routes", "originSettlementId", "settlements"),
        Reference("routes", "destinationSettlementId", "settlements"), Reference("schedules", "targetPolityId", "polities"),
    ),
    field_matches=(FieldMatch("settlements", "provinceId", "provinces", "controllerPolityId"),),
    representation_domains=("settlements",), maximum_diagnostics=12,
    maximum_active_objects=800, maximum_scan_ms=1500,
)


class WorldIntegrityRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.fixture = full_world_fixture()

    def recover(self, fixture=None, adapter=None):
        return recover(fixture or self.fixture, POLICY, adapter or RecordingReconstructionAdapter())

    def test_full_world_loss_reconstructs_identically_and_is_idempotent(self):
        authoritative = state_hash(self.fixture, authoritative_only=True)
        first, report = self.recover()
        second, repeated = self.recover(first)
        self.assertEqual(authoritative, state_hash(first, authoritative_only=True))
        self.assertEqual(first, second)
        self.assertEqual((0, 0, 739), (report["fatalCount"], report["repairableCount"], report["activeObjectCount"]))
        self.assertEqual(report["authoritativeHash"], repeated["authoritativeHash"])

    def test_every_runtime_loss_class_and_stale_map_object_is_repaired(self):
        healthy, _ = self.recover()
        for lost_kind in ("city_core", "defense", "civilian", "unit", "effect"):
            damaged = copy.deepcopy(healthy)
            representation = damaged["runtimeRepresentations"]["london"]
            representation["specification"]["authoritative"]["objectKinds"].remove(lost_kind)
            damaged["runtimeRepresentations"]["destroyed_effect"] = copy.deepcopy(representation)
            damaged["indexes"] = {"settlements": {"london": 999}}
            damaged["reconstruction"] = {"status": "interrupted"}
            before = state_hash(damaged, authoritative_only=True)
            self.assertGreater(scan(damaged, POLICY)["repairableCount"], 0)
            repaired, report = self.recover(damaged)
            self.assertEqual(before, state_hash(repaired, authoritative_only=True))
            self.assertNotIn("destroyed_effect", repaired["runtimeRepresentations"])
            self.assertEqual(0, report["repairableCount"])
            self.assertEqual(["city_core", "defense", "civilian", "unit", "effect"],
                             repaired["runtimeRepresentations"]["london"]["specification"]["authoritative"]["objectKinds"])

    def test_capture_cooldown_services_market_quest_route_and_visit_survive(self):
        captured = copy.deepcopy(self.fixture)
        province_id = next(x["provinceId"] for x in captured["authoritative"]["settlements"] if x["id"] == "london")
        next(x for x in captured["authoritative"]["settlements"] if x["id"] == "london")["controllerPolityId"] = "france"
        next(x for x in captured["authoritative"]["provinces"] if x["id"] == province_id)["controllerPolityId"] = "france"
        control = next(x for x in captured["authoritative"]["ownershipControl"] if x["settlementId"] == "london")
        control.update(controllerPolityId="france", captureCooldownUntil=105)
        captured["authoritative"]["economy"][0]["stock"] = 73
        captured["authoritative"]["quests"][0]["stage"] = "active"
        captured["authoritative"]["routes"][0]["blocked"] = True
        captured["authoritative"]["persistenceIndexes"][1]["visited"] = True
        expected = copy.deepcopy(captured["authoritative"])
        recovered, _ = self.recover(captured)
        self.assertEqual(expected, recovered["authoritative"])

    def test_corruption_matrix_rejects_without_partial_mutation_and_bounds_report(self):
        corruptions = []
        orphan = copy.deepcopy(self.fixture); orphan["authoritative"]["armies"][0]["ownerPolityId"] = "missing_polity"; corruptions.append(orphan)
        duplicate = copy.deepcopy(self.fixture); duplicate["authoritative"]["quests"].append(copy.deepcopy(duplicate["authoritative"]["quests"][0])); corruptions.append(duplicate)
        contradiction = copy.deepcopy(self.fixture); contradiction["authoritative"]["settlements"][0]["controllerPolityId"] = "france"; corruptions.append(contradiction)
        location = copy.deepcopy(self.fixture); location["authoritative"]["settlements"][0]["provinceId"] = "invalid_location"; corruptions.append(location)
        partial = copy.deepcopy(self.fixture); partial["transactions"] = [{"id": "capture_1", "status": "prepared"}]; corruptions.append(partial)
        for value in corruptions:
            original = copy.deepcopy(value)
            with self.assertRaises(IntegrityError): self.recover(value)
            self.assertEqual(original, value)
            report = scan(value, POLICY)
            self.assertGreater(report["fatalCount"], 0)
            self.assertLessEqual(len(report["diagnostics"]), POLICY.maximum_diagnostics)
            self.assertTrue(all(x["stableId"] for x in report["diagnostics"]))

    def test_interrupted_adapter_and_serialized_boundary_are_transactional(self):
        adapter = RecordingReconstructionAdapter(); adapter.fail_after = 3
        original = copy.deepcopy(self.fixture)
        with self.assertRaises(ReconstructionError): self.recover(self.fixture, adapter)
        self.assertEqual(original, self.fixture); self.assertEqual({}, adapter.current)
        checkpoint = json.loads(json.dumps(self.fixture, sort_keys=True))
        resumed, _ = self.recover(checkpoint)
        direct, _ = self.recover(self.fixture)
        self.assertEqual(direct, resumed)

    def test_inactive_region_mutation_cross_map_revisit_and_physical_map_coverage(self):
        changed = copy.deepcopy(self.fixture)
        changed["authoritative"]["economy"][0]["inactiveRegionAccrual"] = 17
        changed["authoritative"]["persistenceIndexes"][-1]["visited"] = True
        recovered, _ = self.recover(changed)
        self.assertEqual(17, recovered["authoritative"]["economy"][0]["inactiveRegionAccrual"])
        maps = json.loads((PROJECT / "physical-maps.json").read_text())["physicalMaps"]
        self.assertEqual({x["id"] for x in maps}, {x["mapId"] for x in recovered["authoritative"]["persistenceIndexes"]})

    def test_finalized_budgets_are_enforced(self):
        report = scan(self.fixture, POLICY)
        self.assertLessEqual(report["scanMilliseconds"], POLICY.maximum_scan_ms)
        strict = IntegrityPolicy(POLICY.domains, POLICY.references, POLICY.field_matches,
                                 POLICY.representation_domains, POLICY.maximum_diagnostics, 1, POLICY.maximum_scan_ms)
        with self.assertRaisesRegex(IntegrityError, "active object budget"): recover(self.fixture, strict, RecordingReconstructionAdapter())


if __name__ == "__main__":
    unittest.main()
