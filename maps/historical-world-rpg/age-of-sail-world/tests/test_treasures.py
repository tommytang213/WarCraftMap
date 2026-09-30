import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "_shared" / "engine"))
import treasures


class TreasureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = json.loads((PROJECT / "scenario/treasures/age-of-sail.json").read_text())
        treasures.validate_catalog(cls.catalog)

    def test_same_seed_is_identical_and_resolution_never_rerolls(self):
        a = treasures.TreasureCampaign(self.catalog, "campaign-42")
        b = treasures.TreasureCampaign(self.catalog, "campaign-42")
        tid = "treasure_order_of_christ_archive"
        self.assertEqual(a.resolve(tid), b.resolve(tid))
        first = a.resolve(tid)
        self.assertEqual(first, a.resolve(tid, unavailable_candidate_ids=[first["candidateLocationId"]]))
        resumed = treasures.TreasureCampaign(self.catalog, "campaign-42", json.loads(json.dumps(a.export_state())))
        self.assertEqual(first, resumed.resolve(tid))

    def test_supported_seeds_vary_weighted_candidates_and_fallback_rejects(self):
        seen = {treasures.TreasureCampaign(self.catalog, x).resolve("secret_pacific_wreck_salvage")["candidateLocationId"] for x in range(30)}
        self.assertEqual(2, len(seen))
        campaign = treasures.TreasureCampaign(self.catalog, 1)
        with self.assertRaises(treasures.ResolutionError):
            campaign.resolve("secret_pacific_wreck_salvage", unavailable_candidate_ids=list(seen))

    def test_unique_anchors_and_global_coverage(self):
        unique = [x for x in self.catalog["treasures"] if x["kind"] == "unique"]
        self.assertEqual({"europe", "africa", "middle_east_india", "southeast_asia", "east_asia", "americas_caribbean"}, {r for x in unique for r in x["anchorRegionIds"]})
        self.assertTrue(all(x["historicalEvidence"] for x in unique))
        self.assertIn("pacific", {c["regionId"] for c in self.catalog["candidateLocations"]})

    def test_clues_never_leak_more_than_earned_and_match_resolution(self):
        campaign = treasures.TreasureCampaign(self.catalog, "clues")
        tid = "treasure_mali_royal_goldwork"
        self.assertEqual({"precision": "hidden"}, campaign.guidance(tid))
        region = campaign.apply_clue(tid, "clue_region")
        self.assertEqual({"precision": "region", "regionId": "africa"}, region)
        approximate = campaign.apply_clue(tid, "clue_approximate")
        self.assertNotIn("position", approximate)
        narrowed = campaign.apply_clue(tid, "clue_narrowed")
        self.assertLess(narrowed["searchArea"]["radius"], approximate["searchArea"]["radius"])
        exact = campaign.apply_clue(tid, "clue_exact")
        self.assertEqual(campaign.resolve(tid)["candidateLocationId"], exact["candidateLocationId"])
        self.assertEqual("exact", campaign.apply_clue(tid, "clue_region")["precision"])

    def test_atomic_collection_overflow_duplicates_and_repeatability(self):
        campaign = treasures.TreasureCampaign(self.catalog, "collect")
        tid = "treasure_ming_voyage_register"
        before = campaign.export_state()
        def fail(state, outcomes):
            state["money"] = 999
            raise ValueError("inventory unavailable")
        with self.assertRaises(treasures.CollectionError):
            campaign.collect(tid, {"money": 1}, fail)
        # Resolution is allowed to commit exactly once; collection mutations are not.
        self.assertEqual(0, campaign.export_state()["collectionCounts"][tid])
        def apply(state, outcomes):
            state["applied"] = copy.deepcopy(outcomes)
            return state, [{"type": "inventory", "handling": "existing_overflow_rules"}]
        result = campaign.collect(tid, {"money": 1}, apply)
        self.assertEqual(1, len(result.overflow))
        with self.assertRaises(treasures.CollectionError): campaign.collect(tid, {}, apply)
        generic = "secret_pacific_wreck_salvage"
        campaign.collect(generic, {}, apply); campaign.collect(generic, {}, apply)
        with self.assertRaises(treasures.CollectionError): campaign.collect(generic, {}, apply)

    def test_inactive_regions_spawn_nothing_and_reconstruct_bounded_records(self):
        campaign = treasures.TreasureCampaign(self.catalog, "runtime")
        self.assertEqual((), campaign.runtime_records("africa", active=False))
        records = campaign.runtime_records("africa")
        self.assertLessEqual(len(records), len(self.catalog["treasures"]))
        resumed = treasures.TreasureCampaign(self.catalog, "runtime", campaign.export_state())
        self.assertEqual(records, resumed.runtime_records("africa"))


if __name__ == "__main__": unittest.main()
