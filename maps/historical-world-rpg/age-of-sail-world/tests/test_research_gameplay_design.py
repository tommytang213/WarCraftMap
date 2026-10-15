"""Validate owner-approved research designs without claiming live gameplay binding.

This suite is a design-contract guard. Existing research-unbound release
findings remain unresolved until real production consumers are implemented.
"""
import json
from pathlib import Path
import unittest

PROJECT = Path(__file__).resolve().parents[1]
EFFECTS = PROJECT / "scenario/progression/gameplay-effect-design.json"
RESEARCH = PROJECT / "scenario/progression/catalog.json"
POLITICS = PROJECT / "scenario/politics"
DOC = PROJECT / "docs/HISTORICAL_BALANCE_AND_RESEARCH_EFFECTS.md"
LOCK = PROJECT / "docs/DESIGN_LOCK.md"
EXPECTED_NODES = {
    "abolitionist_public_sphere", "agrarian_improvement",
    "agricultural_mechanization", "agricultural_societies",
    "anatomy_and_medicine", "arquebus_volley_drill", "artillery_offices",
    "artillery_train", "auction_markets", "barometric_measurement",
    "battlefleet_doctrine", "bayonet_system", "bill_of_exchange_networks",
    "blast_furnace_practice", "boring_mills", "botanical_collecting",
    "brokerage_houses", "cadastral_survey", "calculus_methods",
    "campaign_bakeries", "canal_logistics", "canal_tolls_finance",
    "careening_stations", "carronade_batteries", "carvel_hull_construction",
}
REGIONS = (
    "africa-1450.json", "americas-caribbean-1450.json",
    "east-asia-1450.json", "europe-1450.json",
    "middle-east-india-1450.json", "pacific-1450.json",
    "southeast-asia-1450.json",
)


class ResearchGameplayDesignTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = json.loads(RESEARCH.read_text(encoding="utf-8"))
        cls.design = json.loads(EFFECTS.read_text(encoding="utf-8"))

    def test_all_26_are_valid_and_unique_authored_research_unlocks(self):
        records = self.design["effects"]
        self.assertEqual(26, len(records))
        self.assertEqual(EXPECTED_NODES, {x["nodeId"] for x in records})
        self.assertEqual(1, self.design["schemaVersion"])
        self.assertEqual("1450-01-01", self.design["baselineDate"])
        self.assertEqual(10000, self.design["basisPointsDenominator"])
        nodes = {item["id"]: item for item in [
            *self.catalog["technologies"], *self.catalog["institutions"]
        ]}
        seen = set()
        for item in records:
            with self.subTest(node=item["nodeId"], unlock=item["unlock"]):
                source = nodes[item["nodeId"]]
                kind, identity = item["unlock"]["kind"], item["unlock"]["contentId"]
                self.assertIn([kind, identity], source["unlocks"])
                pair = (kind, identity)
                self.assertNotIn(pair, seen)
                seen.add(pair)
                self.assertIn(kind, {"modifier", "policy", "building", "unit", "ability"})
                self.assertEqual("approved_unimplemented", item["designStatus"])
                self.assertTrue(item["recipient"].strip())
                self.assertTrue(item["metric"].strip())
                self.assertTrue(item["rules"].strip())
                bp = item["bonusBasisPoints"]
                self.assertIs(type(bp), int)
                self.assertGreaterEqual(bp, 0)
                self.assertLessEqual(bp, 2500)
                if kind == "unit":
                    self.assertEqual(0, bp)
                    self.assertEqual("commissioning_unlock", item["activation"])
                if kind == "building":
                    self.assertEqual("build_per_settlement", item["activation"])
                if kind == "ability":
                    self.assertEqual("active_settlement_action", item["activation"])
                if kind == "policy":
                    self.assertEqual("policy_choice", item["activation"])

    def test_effect_scope_and_historical_source_remain_unambiguous(self):
        shared = self.design["balanceRules"]
        for key in (
            "researchOwnership", "layers", "effects", "policies",
            "policiesCosts", "buildingsCosts", "abilitiesCosts", "surveysCosts",
            "numeric", "stacking", "historicalAvailability", "status",
        ):
            self.assertIn(key, shared)
            self.assertTrue(shared[key])
        for item in self.design["effects"]:
            self.assertNotEqual("all_objects", item["recipient"])
            self.assertNotEqual("all_players", item["recipient"])
            self.assertNotIn("give_free_gold", item["metric"])
        self.assertIn("not", self.design["authority"].lower())
        self.assertTrue(DOC.exists())

    def test_all_seven_real_1450_political_sources_remain_present(self):
        for region in REGIONS:
            with self.subTest(region=region):
                self.assertEqual(
                    "1450-01-01",
                    json.loads((POLITICS / region).read_text())["campaignStartDate"],
                )
        locked = LOCK.read_text(encoding="utf-8")
        policy = DOC.read_text(encoding="utf-8")
        self.assertIn("AI territorial warfare doctrine", locked)
        self.assertIn("Release-scale content density targets", locked)
        self.assertIn("Owner-delegated historical balance", policy)
        self.assertIn("weaker start", policy)
        self.assertIn("1 January 1450", policy)
        self.assertIn("two meaningful", policy)
        self.assertIn("production", policy.lower())
        self.assertIn("not", self.design["authority"].lower())


if __name__ == "__main__":
    unittest.main()
