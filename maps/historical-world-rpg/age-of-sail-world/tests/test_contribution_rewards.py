import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent / "_shared" / "engine"))
from contribution_rewards import (ContributionRewardError, ContributionRewardRuntime,
                                  ContributionRewardSaveAdapter)


def definitions():
    return {"schemaVersion": 1, "polityProfiles": [
        {"id": "maritime_republic", "polityId": "maritime_republic",
         "startingMeans": {"liquidity": 85, "economic": 90, "territorial": 35,
                           "military": 45, "naval": 90, "institutional": 80},
         "rewards": [
             {"id": "ducats", "kind": "money", "threshold": 20, "baseValue": 100,
              "treasuryCost": 100, "repeatable": True},
             {"id": "arsenal_access", "kind": "access", "threshold": 30,
              "baseValue": 1, "contentId": "republic_arsenal", "repeatable": False},
             {"id": "galley_support", "kind": "naval_support", "threshold": 60,
              "baseValue": 3, "stockCost": 20, "repeatable": False}]},
        {"id": "highland_clans", "polityId": "highland_clans",
         "startingMeans": {"liquidity": 15, "economic": 25, "territorial": 55,
                           "military": 65, "naval": 10, "institutional": 45},
         "rewards": [
             {"id": "silver", "kind": "money", "threshold": 20, "baseValue": 100,
              "treasuryCost": 100, "repeatable": True},
             {"id": "clan_favor", "kind": "favor", "threshold": 20,
              "baseValue": 30, "repeatable": True},
             {"id": "march_wardenship", "kind": "office", "threshold": 60,
              "baseValue": 1, "officeId": "march_warden", "territoryId": "north_march",
              "repeatable": False}]},
    ]}


class ContributionRewardTests(unittest.TestCase):
    def setUp(self):
        self.runtime = ContributionRewardRuntime(
            definitions(), polity_ids=("maritime_republic", "highland_clans"))

    def offers(self, polity, state, magnitude=100, **kwargs):
        values = dict(origin_polity_id="highland_clans",
                      current_allegiance_polity_id=polity)
        values.update(kwargs)
        return {x.reward_id: x for x in self.runtime.offers(
            polity, "wartime_supply", magnitude, state, **values)}

    def test_materially_different_starting_polities_have_different_reward_shape(self):
        common = {"treasury": 1000, "materialStock": 100,
                  "controlledTerritoryIds": ["north_march"]}
        republic = self.offers("maritime_republic", common)
        clans = self.offers("highland_clans", common)
        self.assertGreater(republic["ducats"].value, clans["silver"].value)
        self.assertIn("arsenal_access", republic)
        self.assertIn("clan_favor", clans)
        self.assertNotEqual(set(republic), set(clans))

    def test_same_polity_responds_to_economic_territorial_and_war_change(self):
        strong = self.offers("maritime_republic", {"treasury": 1000, "materialStock": 100,
            "liquidity": 95, "economic": 95, "naval": 90, "warExhaustion": 0,
            "militaryCondition": 100, "controlledTerritoryIds": []})
        collapsed = self.offers("maritime_republic", {"treasury": 20, "materialStock": 0,
            "liquidity": 5, "economic": 10, "naval": 15, "warExhaustion": 90,
            "militaryCondition": 10, "controlledTerritoryIds": []})
        self.assertTrue(strong["ducats"].available)
        self.assertFalse(collapsed["ducats"].available)
        self.assertEqual("treasury", collapsed["ducats"].reason)
        self.assertGreater(strong["galley_support"].value, collapsed["galley_support"].value)
        # Political access remains useful when liquid/material capacity collapses.
        self.assertTrue(collapsed["arsenal_access"].available)

    def test_allegiance_origin_control_and_duplicate_guards(self):
        state = {"treasury": 1000, "materialStock": 100,
                 "controlledTerritoryIds": []}
        foreign = self.offers("highland_clans", state,
            current_allegiance_polity_id="maritime_republic")
        self.assertEqual("allegiance", foreign["clan_favor"].reason)
        local = self.offers("highland_clans", state)
        self.assertEqual("territory_not_controlled", local["march_wardenship"].reason)
        self.runtime.record_contribution("highland_clans", "wartime_supply", 100, "convoy_one")
        with self.assertRaisesRegex(ContributionRewardError, "already recorded"):
            self.runtime.record_contribution("highland_clans", "wartime_supply", 100, "convoy_one")
        granted = self.offers("highland_clans", {**state,
            "controlledTerritoryIds": ["north_march"]})["march_wardenship"]
        self.runtime.grant(granted, grant_key="warden_one", campaign_state={**state,
                           "controlledTerritoryIds": ["north_march"]}, origin_polity_id="highland_clans",
                           current_allegiance_polity_id="highland_clans")
        self.assertEqual("already_granted", self.offers("highland_clans", {**state,
            "controlledTerritoryIds": ["north_march"]})["march_wardenship"].reason)

    def test_save_load_and_map_transition_preserve_tracks_and_grants(self):
        self.runtime.record_contribution("maritime_republic", "wartime_supply", 70, "cargo_one")
        offer = self.offers("maritime_republic", {"treasury": 1000,
            "materialStock": 100, "controlledTerritoryIds": []})["arsenal_access"]
        self.runtime.grant(offer, grant_key="arsenal_one", campaign_state={"treasury": 1000,
                           "materialStock": 100, "controlledTerritoryIds": []}, origin_polity_id="highland_clans",
                           current_allegiance_polity_id="maritime_republic")
        state = ContributionRewardSaveAdapter(self.runtime, {"activeMapId": "west"}).capture_world()
        restored = ContributionRewardRuntime(definitions())
        adapter = ContributionRewardSaveAdapter(restored, {})
        reconstructed = adapter.reconstruct(copy.deepcopy(state))
        state["activeMapId"] = "east"
        adapter.activate(state, reconstructed)
        self.assertEqual(self.runtime.snapshot(), restored.snapshot())
        self.assertEqual("highland_clans", restored.grants[0]["originPolityId"])
        self.assertEqual("maritime_republic", restored.grants[0]["allegiancePolityId"])

    def test_profile_coverage_is_mandatory(self):
        with self.assertRaisesRegex(ContributionRewardError, "cover active polities exactly"):
            ContributionRewardRuntime(definitions(), polity_ids=("maritime_republic",))

    def test_grant_rechecks_authoritative_state_after_offer(self):
        offer = self.offers("highland_clans", {"treasury": 1000, "materialStock": 100,
            "controlledTerritoryIds": ["north_march"]})["march_wardenship"]
        with self.assertRaisesRegex(ContributionRewardError, "no longer controlled"):
            self.runtime.grant(offer, grant_key="stale_land", campaign_state={
                "treasury": 1000, "materialStock": 100, "controlledTerritoryIds": []},
                origin_polity_id="highland_clans",
                current_allegiance_polity_id="highland_clans")


if __name__ == "__main__":
    unittest.main()
