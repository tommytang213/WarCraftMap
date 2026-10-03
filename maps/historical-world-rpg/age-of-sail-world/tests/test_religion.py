import copy
import json
import sys
import unittest
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
ROOT = PROJECT.parent
sys.path.insert(0, str(ROOT / "_shared/engine"))

from religion import ReligionError, ReligionRuntime, ReligionSaveAdapter
from timeline_simulation import TimelineHarness
sys.path.insert(0, str(ROOT / "_shared/tooling"))
from validate_religion import validate

DEFINITIONS = json.loads((PROJECT / "scenario/religion.json").read_text(encoding="utf-8"))


class ReligionTests(unittest.TestCase):
    def runtime(self): return ReligionRuntime(copy.deepcopy(DEFINITIONS))

    def test_scenario_cross_references_authoritative_world(self):
        validate(PROJECT / "scenario/religion.json", PROJECT / "scenario/world/world.json")

    def profess(self, runtime, faith="latin_christianity", investment=100):
        runtime.convert("player_captain", faith, campaign_tick=1, cost_units=50,
                        reputation_consequences=["former_community_disapproval"], new_investment=investment)

    def test_scenario_defines_open_ended_identities_and_distinct_profiles(self):
        runtime = self.runtime()
        self.assertGreater(len(runtime.faiths), 4)
        self.assertEqual({"tradition", "denomination", "syncretic", "local"},
                         {x["kind"] for x in runtime.faiths.values()})
        profiles = {fid: tuple(x["attributeId"] for x in faith["benefits"])
                    for fid, faith in runtime.faiths.items()}
        self.assertNotEqual(profiles["latin_christianity"], profiles["sunni_islam"])

    def test_character_polity_region_policy_and_institution_are_independent(self):
        runtime = self.runtime(); self.profess(runtime, "sunni_islam")
        context = runtime.interaction_context("player_captain", "england", "london")
        self.assertEqual("sunni_islam", context["faithId"])
        self.assertFalse(context["coReligionistGovernment"])
        self.assertEqual(100, context["localShareBasisPoints"])
        runtime.set_policy("england", "secular_non_aligned", [])
        self.assertEqual("sunni_islam", runtime.overview("player_captain")["faithId"])
        self.assertEqual("secular_non_aligned", runtime.interaction_context("player_captain", "england", "london")["policyId"])

    def test_benefits_require_and_scale_independently_with_personal_and_world_strength(self):
        low = self.runtime(); self.profess(low, investment=20)
        low.set_influence("latin_christianity", prestige_units=0, event_units=0)
        low_amount = low.benefits("player_captain")[0].amount_basis_points
        personal = self.runtime(); self.profess(personal, investment=200)
        personal_amount = personal.benefits("player_captain")[0].amount_basis_points
        world = self.runtime(); self.profess(world, investment=20)
        world.set_influence("latin_christianity", prestige_units=20_000, event_units=0)
        world_amount = world.benefits("player_captain")[0].amount_basis_points
        self.assertGreater(personal_amount, low_amount)
        self.assertGreater(world_amount, low_amount)
        self.assertEqual((), self.runtime().benefits("player_captain"))

    def test_diminishing_curves_are_bounded_under_extreme_dominance(self):
        runtime = self.runtime(); self.profess(runtime, investment=10**12)
        runtime.set_influence("latin_christianity", prestige_units=10**12, event_units=10**12)
        benefits = runtime.benefits("player_captain")
        self.assertTrue(all(0 <= x.amount_basis_points <= x.cap_basis_points for x in benefits))
        self.assertTrue(all(x.amount_basis_points >= x.cap_basis_points - 1 for x in benefits))

    def test_rise_decline_and_alternate_history_dynamically_change_effects(self):
        runtime = self.runtime(); self.profess(runtime, "reformed_christianity", 120)
        start = runtime.benefits("player_captain")[0].amount_basis_points
        runtime.set_influence("reformed_christianity", event_units=9000)
        rise = runtime.benefits("player_captain")[0].amount_basis_points
        runtime.set_influence("reformed_christianity", prestige_units=0, event_units=0)
        runtime.set_region_composition("london", [
            {"faithId":"latin_christianity","shareBasisPoints":9700},
            {"faithId":"reformed_christianity","shareBasisPoints":0},
            {"faithId":"sunni_islam","shareBasisPoints":100},
            {"faithId":"hindu_traditions","shareBasisPoints":100},
            {"faithId":"yoruba_traditions","shareBasisPoints":100}])
        decline = runtime.benefits("player_captain")[0].amount_basis_points
        self.assertGreater(rise, start); self.assertLess(decline, start)

    def test_mixed_region_validation_and_atomic_rejection(self):
        runtime = self.runtime(); before = runtime.snapshot()
        with self.assertRaisesRegex(ReligionError, "total"):
            runtime.set_region_composition("goa", [{"faithId":"hindu_traditions","shareBasisPoints":9000}])
        self.assertEqual(before, runtime.snapshot())
        self.assertGreater(len(next(x for x in before["regions"] if x["regionId"] == "goa")["composition"]), 2)

    def test_conversion_has_cost_history_and_no_reroll(self):
        runtime = self.runtime(); self.profess(runtime)
        event = runtime.convert("player_captain", "sunni_islam", campaign_tick=250,
                                cost_units=120, reputation_consequences=["latin_reputation_loss"], new_investment=10)
        self.assertEqual(2, event["sequence"])
        restored = self.runtime(); restored.restore(runtime.snapshot())
        self.assertEqual(runtime.snapshot(), restored.snapshot())
        with self.assertRaisesRegex(ReligionError, "invalid conversion"):
            restored.convert("player_captain", "sunni_islam", campaign_tick=250,
                             cost_units=120, reputation_consequences=[], new_investment=10)

    def test_overview_explains_current_magnitude(self):
        runtime = self.runtime(); self.profess(runtime)
        view = runtime.overview("player_captain")
        self.assertIn("personal investment", view["explanation"])
        self.assertIn("current campaign influence", view["explanation"])
        self.assertTrue(all({"amountBasisPoints", "capBasisPoints", "description"} <= set(x) for x in view["benefits"]))

    def test_save_adapter_and_legacy_migration(self):
        runtime = self.runtime(); self.profess(runtime)
        adapter = ReligionSaveAdapter(runtime, {"calendar":{"year":1450}})
        captured = adapter.capture_world(); expected = runtime.snapshot()
        runtime.set_influence("latin_christianity", event_units=999)
        reconstructed = adapter.reconstruct(captured); adapter.activate(captured, reconstructed)
        self.assertEqual(expected, runtime.snapshot())
        legacy = {"calendar":{"year":1450}}; migrated = adapter.migrate_legacy_world(legacy)
        self.assertNotIn("religionState", legacy); adapter.validate_world(migrated)

    def test_multi_century_resume_equivalence(self):
        initial = {"religion": self.runtime().snapshot()}
        def configure(harness):
            def step(state, context):
                runtime = self.runtime(); runtime.restore(state["religion"])
                current = next(x for x in runtime.snapshot()["influence"] if x["faithId"] == "reformed_christianity")
                runtime.set_influence("reformed_christianity", event_units=current["eventUnits"] + (3 if context.time < 1640 else 1))
                state["religion"] = runtime.snapshot()
            harness.register_step("religion", "faith_influence", step)
        full = TimelineHarness(seed=306, start_time=1450, state=initial); configure(full)
        expected = full.run(end_time=1820, step_size=1)
        partial = TimelineHarness(seed=306, start_time=1450, state=initial); configure(partial)
        partial.run(end_time=1640, step_size=1)
        resumed = TimelineHarness.from_checkpoint(partial.checkpoint()); configure(resumed)
        actual = resumed.run(end_time=1820, step_size=1)
        self.assertEqual(expected["stateHash"], actual["stateHash"])


if __name__ == "__main__": unittest.main()
