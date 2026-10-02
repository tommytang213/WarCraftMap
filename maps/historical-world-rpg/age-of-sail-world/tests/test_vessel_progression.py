import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent / "_shared" / "engine"))

import campaign_save
from vessel_progression import (RecordingVesselAdapter, RefitContext, VesselProgressionError,
    VesselProgressionRuntime, VesselSaveAdapter, initial_state, migrate_state_v0, validate_catalog,
    validate_state)

CATALOG_PATH = ROOT / "scenario" / "naval" / "vessel-progression.json"


def catalog(): return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


def runtime():
    data = catalog()
    return VesselProgressionRuntime(data, initial_state(data, data["initialVessels"]), RecordingVesselAdapter())


def context(**changes):
    values = dict(year=1680, polity_id="england", region_id="europe_atlantic",
        dockyard_id="dover_dockyard", dockyard_capability=4,
        technology_ids=frozenset({"cast_cannon", "naval_gunnery", "dockyard_logistics",
                                  "standardized_charts", "battlefleet_doctrine"}),
        institution_ids=frozenset({"naval_administration"}),
        requirement_ids=frozenset({"fleet_flagship_authority"}))
    values.update(changes)
    return RefitContext(**values)


def account():
    return {"money": 10000, "resources": {"timber": 100, "arms": 100,
        "canvas": 100, "copper": 100, "ship_provisions": 100}}


class VesselProgressionTests(unittest.TestCase):
    def test_catalog_and_initial_individual_vessels(self):
        data = catalog(); validate_catalog(data)
        state = initial_state(data, data["initialVessels"])
        self.assertEqual(3, len(state["vessels"]))
        self.assertNotEqual(state["vessels"][0]["archetypeId"], state["vessels"][1]["archetypeId"])

    def test_valid_install_replace_remove_repair_and_atomic_costs(self):
        rt = runtime(); funds = account()
        remaining = rt.install_refit("english_patrol_vessel", "cast_bronze_battery", context(year=1600), funds, "install_one")
        self.assertEqual(9100, remaining["money"])
        self.assertEqual(88, remaining["resources"]["timber"])
        self.assertEqual(10000, funds["money"])
        remaining = rt.install_refit("english_patrol_vessel", "standardized_broadside_drill", context(), remaining,
                                     "replace_one", replace_refit_id="cast_bronze_battery")
        self.assertEqual(("standardized_broadside_drill",), rt.view("english_patrol_vessel").installed_refit_ids)
        remaining_money = rt.remove_refit("english_patrol_vessel", "standardized_broadside_drill", remaining["money"], 1681,
                                          "dover_dockyard", "remove_one")
        self.assertLess(remaining_money, remaining["money"])
        rt.update("english_patrol_vessel", hull_condition=70)
        after = rt.repair("english_patrol_vessel", None, 20, remaining_money, "repair_hull")
        self.assertEqual(90, rt.view("english_patrol_vessel").hull_condition)
        self.assertEqual(remaining_money - 240, after)

    def test_damage_refit_repair_and_maintenance_restoration_are_atomic(self):
        rt = runtime(); funds = account()
        funds = rt.install_refit("english_patrol_vessel", "cast_bronze_battery", context(year=1600), funds, "fit_damage")
        rt.apply_damage("english_patrol_vessel", hull=11, maintenance=17,
                        refit_damage={"cast_bronze_battery": 23})
        vessel = rt.snapshot()["vessels"][0]
        self.assertEqual((81, 69, 77), (vessel["hullCondition"], vessel["maintenance"],
                                      vessel["installedRefits"][0]["condition"]))
        funds["money"] = rt.repair("english_patrol_vessel", "cast_bronze_battery", 23,
                                   funds["money"], "repair_refit")
        funds["money"] = rt.restore_maintenance("english_patrol_vessel", 17, funds["money"], "restore_maintenance")
        vessel = rt.snapshot()["vessels"][0]
        self.assertEqual((86, 100), (vessel["maintenance"], vessel["installedRefits"][0]["condition"]))
        before = rt.snapshot()
        with self.assertRaises(VesselProgressionError):
            rt.apply_damage("english_patrol_vessel", refit_damage={"missing_refit": 10})
        self.assertEqual(before, rt.snapshot())

    def test_rejected_refits_and_rollback(self):
        cases = [
            ("incompatible", "kilwa_trade_vessel", "cast_bronze_battery", context(year=1600)),
            ("year", "english_patrol_vessel", "cast_bronze_battery", context(year=1450)),
            ("tech", "english_patrol_vessel", "cast_bronze_battery", context(year=1600, technology_ids=frozenset())),
            ("dockyard", "english_patrol_vessel", "cast_bronze_battery", context(year=1600, dockyard_capability=1)),
        ]
        for tx, vessel, refit, ctx in cases:
            rt = runtime(); before = rt.snapshot(); funds = account()
            with self.subTest(tx=tx), self.assertRaises(VesselProgressionError):
                rt.install_refit(vessel, refit, ctx, funds, tx)
            self.assertEqual(before, rt.snapshot()); self.assertEqual(account(), funds)
        rt = runtime(); before = rt.snapshot(); poor = {"money": 1, "resources": account()["resources"]}
        with self.assertRaisesRegex(VesselProgressionError, "insufficient"):
            rt.install_refit("english_patrol_vessel", "cast_bronze_battery", context(year=1600), poor, "poor")
        self.assertEqual(before, rt.snapshot())

    def test_slot_conflict_duplicate_and_free_replacement_are_rejected(self):
        rt = runtime(); funds = account()
        funds = rt.install_refit("english_patrol_vessel", "cast_bronze_battery", context(year=1600), funds, "first")
        before = rt.snapshot()
        for kwargs in ({}, {"replace_refit_id": "missing_refit"}):
            with self.assertRaises(VesselProgressionError):
                rt.install_refit("english_patrol_vessel", "standardized_broadside_drill", context(), funds, "conflict", **kwargs)
            self.assertEqual(before, rt.snapshot())
        with self.assertRaises(VesselProgressionError):
            rt.install_refit("english_patrol_vessel", "cast_bronze_battery", context(year=1600), funds, "duplicate")

    def test_experience_is_deterministic_deduplicated_and_crosses_milestones(self):
        one, two = runtime(), runtime()
        for rt in (one, two):
            for number in range(7):
                rt.award("english_patrol_vessel", "battle_victory", f"victory_{number}", {"victories": 1})
            self.assertFalse(rt.award("english_patrol_vessel", "battle_victory", "victory_0", {"victories": 1}))
        self.assertEqual(one.snapshot(), two.snapshot())
        self.assertEqual((700, "veteran", 7), (one.view("english_patrol_vessel").experience,
            one.view("english_patrol_vessel").milestone_id,
            one.snapshot()["vessels"][0]["history"]["victories"]))

    def test_continuous_adjacent_values_diminishing_returns_and_envelope(self):
        rt = runtime(); values = []
        for index in range(80):
            rt.award("english_patrol_vessel", "battle_fought", history={"battles": 1})
            values.append(sum(max(0, x) for x in rt.derived_effects("english_patrol_vessel").values()))
        self.assertTrue(all(a <= b for a, b in zip(values, values[1:])))
        self.assertGreater(values[3], 200)
        self.assertLess(values[-1] - values[-2], values[1] - values[0])
        self.assertLessEqual(max(rt.derived_effects("english_patrol_vessel").values()), 4000)

    def test_role_effects_specialization_and_hull_remains_primary(self):
        combat, explore = runtime(), runtime()
        for index in range(20):
            combat.award("english_patrol_vessel", "battle_victory", f"battle_{index}")
            explore.award("pacific_voyaging_vessel", "discovery_recorded", f"discovery_{index}")
        combat.choose_specialization("english_patrol_vessel", "gunnery_ship")
        explore.choose_specialization("pacific_voyaging_vessel", "blue_water_explorer")
        self.assertGreater(combat.derived_effects("english_patrol_vessel")["accuracy"],
                           combat.derived_effects("english_patrol_vessel").get("range", 0))
        self.assertGreater(explore.derived_effects("pacific_voyaging_vessel")["range"],
                           explore.derived_effects("pacific_voyaging_vessel").get("accuracy", 0))
        self.assertEqual((700, 220), (combat.comparison("english_patrol_vessel")["hullPowerRating"],
                                     explore.comparison("pacific_voyaging_vessel")["hullPowerRating"]))
        self.assertLessEqual(max(explore.derived_effects("pacific_voyaging_vessel").values()), 4000)

    def test_crew_assignment_transfer_capture_damage_and_history(self):
        rt = runtime()
        rt.update("english_patrol_vessel", crew_quality=76, captain_character_id="horatio_nelson",
                  admiral_character_id="elizabeth_i", fleet_id=None, owner_polity_id="france",
                  controller_polity_id="france", hull_condition=43, maintenance=51)
        view = rt.view("english_patrol_vessel")
        self.assertEqual((76, None, "france", "france", 43, 51), (view.crew_quality, view.fleet_id,
            view.owner_polity_id, view.controller_polity_id, view.hull_condition, view.maintenance))
        rt.award("english_patrol_vessel", "battle_victory", "captured_prize", {"defeatedShips": 1})
        rt.award("english_patrol_vessel", "battle_fought", history={"commandersServedUnder": "horatio_nelson"})
        history = rt.snapshot()["vessels"][0]["history"]
        self.assertEqual((1, ["horatio_nelson"]), (history["defeatedShips"], history["commandersServedUnder"]))

    def test_abstract_runtime_loss_retirement_and_reconstruction_do_not_change_authority(self):
        rt = runtime(); before = rt.snapshot(); rt.reconstruct()
        self.assertTrue(rt.view("english_patrol_vessel").represented)
        self.assertFalse(rt.view("kilwa_trade_vessel").represented)
        handle = rt.representations["english_patrol_vessel"]
        rt.adapter.destroy_unexpectedly(handle); rt.reconstruct()
        self.assertEqual(before, rt.snapshot())
        rt.update("english_patrol_vessel", retired=True)
        self.assertFalse(rt.view("english_patrol_vessel").represented)

    def test_save_load_migration_and_repeated_resave(self):
        rt = runtime(); rt.award("english_patrol_vessel", "battle_victory", "save_victory")
        adapter = VesselSaveAdapter(rt, {"calendar": {"year": 1600}})
        storage = campaign_save.MemorySaveStorage()
        manager = campaign_save.CampaignSaveManager(build_version="1", scenario_id="test", scenario_version="1",
            storage=storage, capture_state=lambda: (adapter.capture_world(), {}),
            validate_state=lambda world, players: adapter.validate_world(world),
            reconstruct_runtime=lambda world, players: adapter.reconstruct(world),
            activate_state=lambda world, players, rebuilt: adapter.activate(world, rebuilt), is_save_safe=lambda: True)
        slot = campaign_save.SaveSlot("manual", 1); manager.save(slot, "one"); expected = rt.snapshot()
        manager.load(slot); manager.save(slot, "two"); manager.load(slot)
        self.assertEqual(expected, rt.snapshot())
        old = copy.deepcopy(expected); old["schemaVersion"] = 0; old.pop("processedTransactionIds")
        migrated = migrate_state_v0(old)
        self.assertEqual(1, migrated["schemaVersion"]); self.assertEqual(0, old["schemaVersion"])
        validate_state(catalog(), migrated)

    def test_bounded_service_history(self):
        rt = runtime(); limit = catalog()["tuning"]["historyEventLimit"]
        for _ in range(limit + 20): rt.award("english_patrol_vessel", "battle_fought", history={"battles": 1})
        vessel = rt.snapshot()["vessels"][0]
        self.assertEqual(limit, len(vessel["history"]["events"]))
        self.assertEqual(limit + 20, vessel["history"]["battles"])


if __name__ == "__main__": unittest.main()
