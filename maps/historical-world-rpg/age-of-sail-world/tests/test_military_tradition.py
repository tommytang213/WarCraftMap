import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "_shared/engine"))
sys.path.insert(0, str(ROOT / "_shared/tooling"))
from military_tradition import (MilitaryTraditionRuntime, MilitaryTraditionSaveAdapter,
    RecordingTraditionAdapter, TraditionError)
from validate_military_traditions import validate

DEFINITIONS = PROJECT / "scenario/military-traditions.json"
WORLD = PROJECT / "scenario/world/world.json"


class MilitaryTraditionTests(unittest.TestCase):
    def setUp(self):
        self.defs = json.loads(DEFINITIONS.read_text())
        self.adapter = RecordingTraditionAdapter()
        self.runtime = MilitaryTraditionRuntime(self.defs, self.adapter)

    @staticmethod
    def contribution(unit="english_guard_formation", source="enemy_kill", amount=100, enemy="france"):
        return {"sourceId": source, "unitId": unit, "enemyControllerId": enemy, "amount": amount}

    def test_contract_and_cross_references(self):
        validate(DEFINITIONS, WORLD)
        self.assertEqual(4, len(self.runtime.snapshot()["tracks"]))

    def test_controller_category_isolation_weighting_and_rejections_are_atomic(self):
        self.runtime.award([self.contribution(amount=100), self.contribution(source="combat_assist", amount=100)])
        self.assertEqual(150, self.runtime.view("england", "land_formation").experience)
        self.assertEqual(0, self.runtime.view("england", "sailing_naval").experience)
        self.assertEqual(0, self.runtime.view("france", "land_formation").experience)
        before = self.runtime.snapshot()
        for bad in (self.contribution(enemy="england"), self.contribution(source="missing"),
                    self.contribution(unit="missing"), self.contribution(amount=0)):
            with self.assertRaises(TraditionError): self.runtime.award([self.contribution(), bad])
            self.assertEqual(before, self.runtime.snapshot())

    def test_ordering_continuous_growth_large_totals_and_no_cap(self):
        values = [self.contribution(amount=10), self.contribution(source="combat_assist", amount=20)]
        a = MilitaryTraditionRuntime(self.defs, RecordingTraditionAdapter()); a.award(values)
        b = MilitaryTraditionRuntime(self.defs, RecordingTraditionAdapter()); b.award(list(reversed(values)))
        self.assertEqual(a.snapshot(), b.snapshot())
        before = a.view("england", "land_formation").modifiers["attack_basis_points"]
        a.award([self.contribution(amount=1)])
        self.assertGreater(a.view("england", "land_formation").modifiers["attack_basis_points"], before)
        a.award([self.contribution(amount=10**12)])
        self.assertGreater(a.view("england", "land_formation").experience, 10**12)

    def test_add_upgrade_replacement_simultaneous_crossing_and_continued_growth(self):
        self.runtime.award([self.contribution(amount=3500)])
        view = self.runtime.view("england", "land_formation")
        self.assertEqual(("platoon_fire",), view.effects)
        first = view.modifiers["attack_basis_points"]
        self.runtime.award([self.contribution(amount=1)])
        self.assertGreater(self.runtime.view("england", "land_formation").modifiers["attack_basis_points"], first)

    def test_transfer_category_inactive_instantiation_reconstruction_and_layer_removal(self):
        self.runtime.award([self.contribution(amount=1000)])
        self.runtime.set_runtime_active("english_guard_formation", True)
        self.adapter.unrelated_effects["english_guard_formation"] = "weather"
        self.runtime.change_unit("english_guard_formation", controller_id="france")
        self.assertEqual(0, self.adapter.layers["english_guard_formation"]["modifiers"]["attack_basis_points"])
        self.assertEqual(1000, self.runtime.view("england", "land_formation").experience)
        self.runtime.change_unit("english_guard_formation", controller_id="england", category_id="sailing_naval")
        self.assertIn("naval_damage_basis_points", self.adapter.layers["english_guard_formation"]["modifiers"])
        self.runtime.reconstruct(["english_patrol_ship"])
        self.assertNotIn("english_guard_formation", self.adapter.layers)
        self.assertEqual("weather", self.adapter.unrelated_effects["english_guard_formation"])

    def test_save_load_migration_checkpoint_and_long_timeline_equivalence(self):
        adapter = MilitaryTraditionSaveAdapter(self.runtime, {"tick": 3})
        migrated = adapter.migrate_legacy_world({"tick": 2})
        self.assertIn("militaryTraditionState", migrated)
        self.runtime.award([self.contribution(amount=100)])
        checkpoint = adapter.capture_world()
        resumed = MilitaryTraditionRuntime(self.defs, RecordingTraditionAdapter())
        resumed.restore(checkpoint["militaryTraditionState"])
        for runtime in (self.runtime, resumed):
            for _ in range(100): runtime.award([self.contribution(amount=10)])
        self.assertEqual(self.runtime.snapshot(), resumed.snapshot())

    def test_invalid_definitions_and_snapshots(self):
        mutations = []
        bad = copy.deepcopy(self.defs); bad["traditions"][0]["coefficients"][0]["denominator"] = 0; mutations.append(bad)
        bad = copy.deepcopy(self.defs); bad["traditions"][0]["milestones"][1]["threshold"] = 1000; mutations.append(bad)
        bad = copy.deepcopy(self.defs); bad["unitAssignments"][0]["categoryId"] = "missing"; mutations.append(bad)
        for definition in mutations:
            with self.assertRaises(TraditionError): MilitaryTraditionRuntime(definition, RecordingTraditionAdapter())
        bad_state = self.runtime.snapshot(); bad_state["tracks"].pop()
        with self.assertRaises(TraditionError): self.runtime.restore(bad_state)


if __name__ == "__main__": unittest.main()
