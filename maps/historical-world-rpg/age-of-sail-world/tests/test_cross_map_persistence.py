import copy
import json
import sys
import unittest
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT.parent / "_shared" / "engine"))
import cross_map_persistence as transfer


MANIFEST = {
    "format": "warcraftmap_physical_maps_v1", "formatVersion": 1,
    "physicalMaps": [
        {"id": "west", "packagePath": "Maps/West.w3x", "assignments": {
            "logicalRegionIds": ["europe"], "regionalInstanceIds": ["iberia"],
            "generatedTerrainIds": ["europe"]}},
        {"id": "east", "packagePath": "Maps/East.w3x", "assignments": {
            "logicalRegionIds": ["europe"], "regionalInstanceIds": ["balkans"],
            "generatedTerrainIds": ["europe"]}},
    ]}

CONTENT = {
    "west": {"physicalMap": {"id": "west", "logicalRegionIds": ["europe"],
        "regionalInstanceIds": ["iberia"]}, "settlementDefinitions": [{"id": "lisbon"}]},
    "east": {"physicalMap": {"id": "east", "logicalRegionIds": ["europe"],
        "regionalInstanceIds": ["balkans"]}, "settlementDefinitions": [{"id": "athens"}]},
}

STATE = {
    "characters": {"hero": {"mapId": "west", "partyId": "party"}},
    "parties": {"party": {"inventoryId": "hero_bag"}},
    "armies": {"army_1": {"mapId": "east", "strength": 100}},
    "fleets": {"fleet_1": {"mapId": "west", "strength": 20}},
    "inventory": {"hero_bag": {"items": ["sword_1"]}},
    "quests": {"quest_1": {"stageId": "started"}},
    "discovery": {"settlements": ["lisbon"]},
    "settlements": {"lisbon": {"ownerId": "portugal", "defense": 3}},
    "ownership": {"lisbon": "portugal"}, "control": {"lisbon": "portugal"},
    "diplomacy": {"portugal_castile": "peace"},
    "economy": {"markets": {"lisbon": {"grain": 5}}},
    "technology": {"portugal": ["navigation"]},
    "scheduledWork": {"rebuild_lisbon": {"dueDay": 4}},
}


class Harness:
    def __init__(self):
        self.state = copy.deepcopy(STATE); self.active = "west"; self.runtime = {}
        self.content = copy.deepcopy(CONTENT); self.storage = transfer.MemoryTransferStorage()
        self.reconstruction_order = []; self.fail_adapter = False

    def adapter(self, name, priority):
        def reconstruct(state, content, assignment):
            self.reconstruction_order.append(name)
            if self.fail_adapter and name == "military": raise RuntimeError("fixture failure")
            kind = "settlements" if name == "settlements" else name
            return tuple(sorted(state.get(kind, {})))
        return transfer.ReconstructionAdapter(name, reconstruct, priority)

    def manager(self, **overrides):
        values = dict(scenario_id="fixture", scenario_version="1", build_version="test.1",
            campaign_schema=3, manifest=transfer.PhysicalMapManifest(MANIFEST), storage=self.storage,
            capture_state=lambda: self.state, load_destination_content=lambda map_id: self.content[map_id],
            activate=self.activate, adapters=[self.adapter("military", 20), self.adapter("settlements", 10)],
            first_visit_defaults=lambda map_id, content: {"settlements": {
                item["id"]: {"ownerId": "defaults", "defense": 1}
                for item in content["settlementDefinitions"]}})
        values.update(overrides)
        return transfer.CrossMapTransferManager(**values)

    def activate(self, map_id, state, runtime):
        self.active, self.state, self.runtime = map_id, copy.deepcopy(state), runtime


class DeferredSave:
    def __init__(self): self.has_deferred_save = True; self.retries = 0
    def retry_deferred(self):
        self.retries += 1; self.has_deferred_save = False


class CrossMapPersistenceTests(unittest.TestCase):
    def setUp(self): self.h = Harness(); self.manager = self.h.manager()

    def test_two_map_round_trip_revisit_and_no_duplicate_global_entities(self):
        first = self.manager.transfer("west", "east", {"boundaryId": "west_east"}, "tx-1")
        self.assertEqual(("settlements", "military"), first.reconstructed)
        self.assertEqual(["settlements", "military"], self.h.reconstruction_order)
        self.assertEqual("defaults", self.h.state["settlements"]["athens"]["ownerId"])
        # Captured/rebuilt state and inactive-map simulation mutate the same authority.
        self.h.state["settlements"]["lisbon"].update(ownerId="castile", defense=9)
        self.h.state["armies"]["army_1"]["strength"] = 77
        self.h.state["quests"]["quest_1"]["stageId"] = "complete"
        self.h.reconstruction_order.clear()
        self.manager.transfer("east", "west", {"boundaryId": "east_west"}, "tx-2")
        self.manager.transfer("west", "east", {"boundaryId": "west_east"}, "tx-3")
        self.assertEqual("castile", self.h.state["settlements"]["lisbon"]["ownerId"])
        self.assertEqual(9, self.h.state["settlements"]["lisbon"]["defense"])
        self.assertEqual(77, self.h.state["armies"]["army_1"]["strength"])
        self.assertEqual("complete", self.h.state["quests"]["quest_1"]["stageId"])
        for domain in STATE: self.assertIn(domain, self.h.state)
        self.assertEqual(1, len(self.h.state["characters"]))
        resumed = self.h.manager().resume()
        self.assertEqual((self.h.state, "east"), resumed)

    def test_envelope_metadata_integrity_and_transient_rejection(self):
        self.manager.transfer("west", "east", {}, "tx-meta")
        document = json.loads(self.h.storage.read_committed())
        self.assertEqual({"id": "fixture", "version": "1"}, document["scenario"])
        for field in ("buildVersion", "schemaVersion", "campaignSchemaVersion", "sourceMapId",
                      "destinationMapId", "transition", "integrity", "transaction", "visitedMaps"):
            self.assertIn(field, document)
        self.assertNotIn("handle", json.dumps(document).lower())
        for bad in ({"unitHandle": 4}, {"camera": "main"}, {"timerId": "x"}, {"uiObject": {}}):
            with self.assertRaises(transfer.TransferError):
                transfer.serialize_transfer(scenario_id="fixture", scenario_version="1", build_version="test.1",
                    campaign_schema=3, source_map_id="west", destination_map_id="east", transition={},
                    transaction_id="bad", sequence=1, state=bad, visited_maps={})

    def test_all_precommit_failures_preserve_checkpoint_and_active_runtime(self):
        self.manager.transfer("west", "east", {}, "good")
        checkpoint = self.h.storage.read_committed(); baseline = copy.deepcopy((self.h.active, self.h.state, self.h.runtime))
        cases = []
        stale = copy.deepcopy(CONTENT["west"]); stale["physicalMap"]["regionalInstanceIds"] = ["wrong"]
        cases.append(lambda: self.h.manager(load_destination_content=lambda _id: stale).transfer("east", "west", {}, "stale"))
        cases.append(lambda: self.h.manager(load_destination_content=lambda _id: (_ for _ in ()).throw(KeyError("missing"))).transfer("east", "west", {}, "missing"))
        self.h.fail_adapter = True
        cases.append(lambda: self.h.manager().transfer("east", "west", {}, "adapter"))
        for operation in cases:
            with self.assertRaises(Exception): operation()
            self.assertEqual(checkpoint, self.h.storage.read_committed())
            self.assertEqual(baseline, (self.h.active, self.h.state, self.h.runtime))
        self.h.fail_adapter = False
        self.h.storage.fail_next_commit = True
        with self.assertRaises(transfer.TransferStorageError):
            self.h.manager().transfer("east", "west", {}, "interrupted")
        self.assertEqual(checkpoint, self.h.storage.read_committed())
        self.assertEqual(baseline, (self.h.active, self.h.state, self.h.runtime))

    def test_corrupt_incompatible_and_failed_migration_do_not_mutate_manager(self):
        self.manager.transfer("west", "east", {}, "good")
        raw = self.h.storage.read_committed(); baseline = (self.manager.sequence, copy.deepcopy(self.manager.visited_maps))
        corrupt = json.loads(raw); corrupt["integrity"]["checksum"] = "0" * 64
        self.h.storage._committed = json.dumps(corrupt).encode()
        with self.assertRaises(transfer.TransferIntegrityError): self.manager.resume()
        self.assertEqual(baseline, (self.manager.sequence, self.manager.visited_maps))
        self.h.storage._committed = raw
        with self.assertRaises(transfer.IncompatibleTransferError): self.h.manager(build_version="other").resume()
        old = json.loads(raw); old["schemaVersion"] = 0; old.pop("visitedMaps")
        old["integrity"]["checksum"] = transfer._checksum(old); self.h.storage._committed = json.dumps(old).encode()
        migrated = transfer.load_transfer(self.h.storage.read_committed(), scenario_id="fixture",
            scenario_version="1", build_version="test.1", campaign_schema=3)
        self.assertEqual(self.h.state, migrated["state"])
        self.assertEqual({}, migrated["visitedMaps"])
        registry = transfer.TransferMigrationRegistry(); registry._migrations[0] = lambda document: document
        with self.assertRaises(transfer.IncompatibleTransferError):
            transfer.load_transfer(self.h.storage.read_committed(), scenario_id="fixture",
                scenario_version="1", build_version="test.1", campaign_schema=3, registry=registry)

    def test_first_visit_defaults_never_overwrite_authority_and_sequences_are_deterministic(self):
        self.h.state["settlements"]["athens"] = {"ownerId": "byzantium", "defense": 8}
        self.manager.transfer("west", "east", {}, "tx-1")
        self.assertEqual({"ownerId": "byzantium", "defense": 8}, self.h.state["settlements"]["athens"])
        checkpoint = self.h.storage.read_committed()
        state, _ = self.h.manager().resume()
        self.assertEqual(transfer._canonical(self.h.state), transfer._canonical(state))
        self.assertEqual(checkpoint, self.h.storage.read_committed())

    def test_transfer_window_defers_autosave_and_retries_after_commit(self):
        deferred = DeferredSave(); observations = []
        manager = None
        def reconstruct(state, content, assignment):
            observations.append(manager.is_save_safe)
            return ()
        manager = self.h.manager(save_manager=deferred, adapters=[
            transfer.ReconstructionAdapter("fixture", reconstruct)])
        manager.transfer("west", "east", {}, "autosave-safe")
        self.assertEqual([False], observations)
        self.assertEqual(1, deferred.retries)
        self.assertTrue(manager.is_save_safe)


if __name__ == "__main__": unittest.main()
