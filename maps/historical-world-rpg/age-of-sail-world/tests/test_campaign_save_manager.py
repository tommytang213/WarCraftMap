import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "_shared" / "engine"))
import campaign_save as save


WORLD = {"fleets": {"atlantic_patrol": {"shipIds": ["stable_ship_id"]}}}
PLAYERS = {"main": {"characterId": "stable_character_id", "money": 7}}


class Harness:
    def __init__(self):
        self.world = copy.deepcopy(WORLD)
        self.players = copy.deepcopy(PLAYERS)
        self.runtime = {"old": True}
        self.safe = True
        self.reconstruct_calls = 0

    def manager(self, storage, registry=None):
        def validate(world, players):
            if world.get("invalid"):
                raise save.SaveError("invalid authoritative state")
            self.assert_handle_free(world)
            self.assert_handle_free(players)

        def reconstruct(world, players):
            self.reconstruct_calls += 1
            return {"fleetIds": sorted(world.get("fleets", {}))}

        def activate(world, players, runtime):
            self.world, self.players, self.runtime = world, players, runtime

        return save.CampaignSaveManager(
            build_version="1.2.3+test",
            scenario_id="test_scenario",
            scenario_version="4",
            storage=storage,
            capture_state=lambda: (self.world, self.players),
            validate_state=validate,
            reconstruct_runtime=reconstruct,
            activate_state=activate,
            is_save_safe=lambda: self.safe,
            registry=registry,
        )

    def assert_handle_free(self, value):
        self.serialized = json.dumps(value)
        if "handle" in self.serialized.lower():
            raise AssertionError("transient handle found")


class CampaignSaveManagerTests(unittest.TestCase):
    def setUp(self):
        self.harness = Harness()
        self.storage = save.MemorySaveStorage()
        self.manager = self.harness.manager(self.storage)
        self.slot = save.SaveSlot("manual", 1)

    def test_all_slot_categories_round_trip_through_stable_ids(self):
        slots = [save.SaveSlot("manual", 2), save.SaveSlot("autosave", 3),
                 save.SaveSlot("session_start"), save.SaveSlot("major_milestone")]
        for slot in slots:
            self.manager.save(slot, "2026-09-27T12:00:00Z")
            document = json.loads(self.storage.read(slot.stable_id))
            self.assertEqual(slot.stable_id, document["slot"]["id"])
            self.assertNotIn("handle", json.dumps(document["state"]).lower())
        self.harness.world = {}
        self.manager.load(slots[-1])
        self.assertEqual(WORLD, self.harness.world)
        self.assertEqual({"fleetIds": ["atlantic_patrol"]}, self.harness.runtime)

    def test_unsafe_save_defers_and_retries_without_capturing_partial_state(self):
        self.harness.safe = False
        result = self.manager.save(self.slot, "now")
        self.assertEqual("deferred", result.status)
        self.assertIsNone(self.storage.read(self.slot.stable_id))
        self.harness.world = copy.deepcopy(WORLD)
        self.harness.safe = True
        self.assertTrue(self.manager.retry_deferred().succeeded)
        self.assertFalse(self.manager.has_deferred_save)
        self.assertIsNone(self.manager.retry_deferred())

    def test_transaction_failure_does_not_replace_previous_payload(self):
        self.manager.save(self.slot, "first")
        previous = self.storage.read(self.slot.stable_id)
        self.harness.world["changed"] = True
        self.storage.fail_next_write = True
        with self.assertRaisesRegex(save.StorageError, "transactional write failed"):
            self.manager.save(self.slot, "second")
        self.assertEqual(previous, self.storage.read(self.slot.stable_id))

    def test_corrupt_or_incompatible_metadata_preserves_active_state(self):
        self.manager.save(self.slot, "now")
        baseline = copy.deepcopy((self.harness.world, self.harness.players, self.harness.runtime))
        for field, value in (("checksum", "0" * 64),):
            document = json.loads(self.storage.read(self.slot.stable_id))
            document["integrity"][field] = value
            self.storage._slots[self.slot.stable_id] = json.dumps(document).encode()
            with self.assertRaises(save.IntegrityError):
                self.manager.load(self.slot)
            self.assertEqual(baseline, (self.harness.world, self.harness.players, self.harness.runtime))
        for path, value in ((("scenario", "id"), "other"), (("scenario", "version"), "5"),
                            (("buildVersion",), "2.0")):
            raw = save.serialize_save(
                build_version=value if path == ("buildVersion",) else "1.2.3+test",
                scenario_id=value if path == ("scenario", "id") else "test_scenario",
                scenario_version=value if path == ("scenario", "version") else "4",
                slot=self.slot, created_at="now", world_state=WORLD, player_state=PLAYERS)
            self.storage._slots[self.slot.stable_id] = raw
            with self.assertRaises(save.IncompatibleSaveError):
                self.manager.load(self.slot)
            self.assertEqual(baseline, (self.harness.world, self.harness.players, self.harness.runtime))

    def test_migration_success_and_failure_are_atomic(self):
        old = json.loads(save.serialize_save(
            build_version="1.2.3+test", scenario_id="test_scenario", scenario_version="4",
            slot=self.slot, created_at="now", world_state=WORLD, player_state=PLAYERS))
        old["schemaVersion"] = 0
        old["state"]["player"] = old["state"].pop("players")
        old["integrity"]["checksum"] = save._checksum(old)
        self.storage._slots[self.slot.stable_id] = json.dumps(old).encode()
        registry = save.MigrationRegistry()
        def migrate(document):
            document["schemaVersion"] = 1
            document["state"]["players"] = document["state"].pop("player")
            return document
        registry.register(0, migrate)
        self.harness.manager(self.storage, registry).load(self.slot)
        self.assertEqual(PLAYERS, self.harness.players)

        baseline = copy.deepcopy((self.harness.world, self.harness.players, self.harness.runtime))
        bad_registry = save.MigrationRegistry()
        bad_registry.register(0, lambda document: document)
        with self.assertRaises(save.IncompatibleSaveError):
            self.harness.manager(self.storage, bad_registry).load(self.slot)
        self.assertEqual(baseline, (self.harness.world, self.harness.players, self.harness.runtime))

    def test_validation_or_reconstruction_failure_never_activates(self):
        self.manager.save(self.slot, "now")
        baseline = copy.deepcopy((self.harness.world, self.harness.players, self.harness.runtime))
        raw = save.serialize_save(
            build_version="1.2.3+test", scenario_id="test_scenario", scenario_version="4",
            slot=self.slot, created_at="now", world_state={"invalid": True}, player_state=PLAYERS)
        self.storage._slots[self.slot.stable_id] = raw
        with self.assertRaisesRegex(save.SaveError, "invalid authoritative"):
            self.manager.load(self.slot)
        self.assertEqual(baseline, (self.harness.world, self.harness.players, self.harness.runtime))


if __name__ == "__main__":
    unittest.main()

