import copy
import json
import random
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent / "_shared" / "engine"))

import campaign_save
from military import MilitaryError, MilitaryRuntime, MilitarySaveAdapter, RecordingMilitaryAdapter

WORLD_PATH = ROOT / "scenario" / "world" / "world.json"


def source():
    return json.loads(WORLD_PATH.read_text(encoding="utf-8"))


class MilitaryRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.world = source()
        self.objects = RecordingMilitaryAdapter()
        self.wars = set()
        self.runtime = MilitaryRuntime(
            self.world, self.objects,
            lambda left, right: frozenset((left, right)) in self.wars,
        )

    def test_authoritative_fields_and_strength_are_independent_of_objects(self):
        guard = self.runtime.unit("english_guard_formation")
        self.assertEqual(("england", "england", 800, 80, 75, 85),
            (guard.legal_owner_polity_id, guard.controller_polity_id,
             guard.represented_strength, guard.morale, guard.supply, guard.readiness))
        self.assertEqual(0, guard.represented_object_count)
        self.runtime.set_locally_relevant("english_guard_formation", True)
        guard = self.runtime.unit("english_guard_formation")
        self.assertEqual(800, guard.represented_strength)
        self.assertEqual(3, guard.represented_object_count)
        self.assertNotIn("food", json.dumps(self.runtime.snapshot()).lower())

    def test_membership_changes_are_deterministic_and_preserve_unassigned_units(self):
        expanded = source()
        reserve = copy.deepcopy(expanded["strategicUnits"][0])
        reserve["id"] = "english_reserve_formation"
        reserve["name"] = "English Reserve Formation"
        expanded["strategicUnits"].append(reserve)
        runtime = MilitaryRuntime(expanded, RecordingMilitaryAdapter(), lambda a, b: False)
        runtime.set_members("english_home_army", ["english_reserve_formation", "english_guard_formation"])
        members = next(x for x in runtime.snapshot()["groups"] if x["id"] == "english_home_army")["memberUnitIds"]
        self.assertEqual(["english_reserve_formation", "english_guard_formation"], members)
        runtime.set_members("english_home_army", ["english_reserve_formation"])
        self.assertEqual(800, runtime.unit("english_guard_formation").represented_strength)

    def test_membership_command_ownership_and_operational_transitions(self):
        self.assertFalse(self.runtime.set_members("english_home_army", ["english_guard_formation"]))
        self.assertTrue(self.runtime.assign_command("english_guard_formation", None))
        self.assertTrue(self.runtime.assign_command("english_guard_formation", "english_field_officer"))
        self.assertTrue(self.runtime.update_unit("english_guard_formation", represented_strength=700, morale=61, supply=62, readiness=63))
        self.assertTrue(self.runtime.consume_supply("english_guard_formation", 2))
        self.assertTrue(self.runtime.update_operational("english_home_army", morale=70, readiness=71))
        self.assertEqual((700, 61, 60, 63), tuple(getattr(self.runtime.unit("english_guard_formation"), x) for x in ("represented_strength", "morale", "supply", "readiness")))
        self.assertTrue(self.runtime.set_ownership("english_home_army", "france", "france"))
        self.assertEqual(("france", "france"), (self.runtime.unit("english_guard_formation").legal_owner_polity_id, self.runtime.unit("english_guard_formation").controller_polity_id))

    def test_invalid_references_kinds_duplicates_and_operations_are_atomic(self):
        baseline = self.runtime.snapshot()
        invalid = (
            lambda: self.runtime.set_members("english_home_army", ["missing_unit"]),
            lambda: self.runtime.set_members("english_home_army", ["english_patrol_ship"]),
            lambda: self.runtime.set_members("english_home_army", ["english_guard_formation", "english_guard_formation"]),
            lambda: self.runtime.assign_command("english_home_army", "english_naval_officer"),
            lambda: self.runtime.update_unit("english_guard_formation", morale=101),
            lambda: self.runtime.consume_supply("english_guard_formation", 100),
            lambda: self.runtime.set_ownership("english_guard_formation", "missing", "england"),
        )
        for operation in invalid:
            with self.subTest(operation=operation), self.assertRaises(MilitaryError):
                operation()
            self.assertEqual(baseline, self.runtime.snapshot())

    def test_duplicate_membership_across_groups_is_rejected_atomically(self):
        candidate = self.runtime.snapshot()
        duplicate = copy.deepcopy(candidate["groups"][0])
        duplicate["id"] = "reserve_army"
        with self.assertRaises(MilitaryError):
            self.runtime.validate_snapshot({**candidate, "groups": candidate["groups"] + [duplicate]})
        self.assertEqual(candidate, self.runtime.snapshot())

    def test_movement_supply_and_legal_conflict_gate(self):
        self.runtime.move("english_patrol_ship", "north_sea_atlantic", supply_cost=4)
        self.assertEqual(("north_sea_atlantic", 66), (self.runtime.unit("english_patrol_ship").location_id, self.runtime.unit("english_patrol_ship").supply))
        baseline = self.runtime.snapshot()
        with self.assertRaisesRegex(MilitaryError, "active legal conflict"):
            self.runtime.move("english_patrol_ship", "english_channel", hostile_to_polity_id="france")
        self.assertEqual(baseline, self.runtime.snapshot())
        self.wars.add(frozenset(("england", "france")))
        self.runtime.move("english_patrol_ship", "english_channel", hostile_to_polity_id="france", supply_cost=1)
        self.assertEqual("english_channel", self.runtime.unit("english_patrol_ship").location_id)
        with self.assertRaises(MilitaryError):
            self.runtime.move("english_patrol_ship", "decorative_lake")

    def test_group_movement_failure_does_not_partially_consume_supply(self):
        baseline = self.runtime.snapshot()
        with self.assertRaises(MilitaryError):
            self.runtime.move("english_home_army", "english_channel", supply_cost=3)
        self.assertEqual(baseline, self.runtime.snapshot())

    def test_abstract_active_retirement_and_unexpected_destruction_recovery(self):
        before = self.runtime.snapshot()
        self.runtime.reconstruct_representations()
        self.assertEqual(1, self.runtime.unit("english_patrol_ship").represented_object_count)
        handle = next(op[3] for op in self.objects.operations if op[0] == "create")
        self.objects.destroy_unexpectedly(handle)
        self.runtime.recover_representations()
        self.assertEqual(1, self.runtime.unit("english_patrol_ship").represented_object_count)
        self.assertEqual(before, self.runtime.snapshot())
        self.runtime.set_locally_relevant("english_patrol_ship", False)
        self.assertEqual(0, self.runtime.unit("english_patrol_ship").represented_object_count)
        self.assertEqual(["create", "create", "retire"], [x[0] for x in self.objects.operations])

    def test_campaign_save_round_trip_reconstructs_without_handles_or_state_change(self):
        adapter = MilitarySaveAdapter(self.runtime, {"calendar": {"day": 1}})
        storage = campaign_save.MemorySaveStorage()
        manager = campaign_save.CampaignSaveManager(
            build_version="1", scenario_id="test", scenario_version="1", storage=storage,
            capture_state=lambda: (adapter.capture_world(), {}),
            validate_state=lambda world, players: adapter.validate_world(world),
            reconstruct_runtime=lambda world, players: adapter.reconstruct(world),
            activate_state=lambda world, players, rebuilt: adapter.activate(world, rebuilt),
            is_save_safe=lambda: True,
        )
        self.runtime.update_unit("english_patrol_ship", morale=55, supply=54, readiness=53)
        saved = self.runtime.snapshot()
        slot = campaign_save.SaveSlot("manual", 1)
        manager.save(slot, "now")
        payload = storage.read(slot.stable_id)
        self.assertNotIn(b"military_object", payload)
        self.runtime.update_unit("english_patrol_ship", morale=1)
        manager.load(slot)
        self.assertEqual(saved, self.runtime.snapshot())
        self.assertEqual(1, self.runtime.unit("english_patrol_ship").represented_object_count)

    def test_legacy_world_migration_is_explicit_and_non_mutating(self):
        adapter = MilitarySaveAdapter(self.runtime, {})
        legacy = {"calendar": {"day": 3}}
        migrated = adapter.migrate_legacy_world(legacy)
        self.assertNotIn("militaryState", legacy)
        self.assertEqual(self.runtime.snapshot(), migrated["militaryState"])

    def test_deterministic_campaign_simulation_and_checkpoint_resume(self):
        def run(seed, checkpoint=None):
            rng = random.Random(seed)
            runtime = MilitaryRuntime(source(), RecordingMilitaryAdapter(), lambda a, b: True)
            for tick in range(120):
                runtime.consume_supply("english_patrol_ship", 0 if runtime.unit("english_patrol_ship").supply == 0 else rng.randrange(2))
                runtime.update_unit("english_patrol_ship", readiness=max(0, runtime.unit("english_patrol_ship").readiness - (tick % 3 == 0)))
                if checkpoint == tick:
                    state = json.loads(json.dumps(runtime.snapshot()))
                    runtime.restore(state, reconstruct=False)
            return runtime.snapshot()
        self.assertEqual(run(76), run(76))
        self.assertEqual(run(76), run(76, checkpoint=60))


if __name__ == "__main__":
    unittest.main()
