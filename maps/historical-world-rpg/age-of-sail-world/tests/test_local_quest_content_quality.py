"""Source-authored harbor rescue quality and eligibility gates for issue #600.

These tests do not prove retail Warcraft III presentation or live action receipts.
"""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent / "_shared" / "engine"))
from local_quest import LocalQuestRuntime

SOURCE = json.loads((ROOT / "scenario" / "local-random-quests.json").read_text(encoding="utf-8"))
WORLD = json.loads((ROOT / "scenario" / "world" / "world.json").read_text(encoding="utf-8"))


class HarborRescueContentQualityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runtime = LocalQuestRuntime(
            SOURCE, WORLD["settlements"], campaign_seed="issue_600_content_gate"
        )
        cls.family = cls.runtime.families["harbor_missing"]
        cls.variants = cls.family["_variants"]

    def test_rescue_eligibility_is_maritime_in_actual_world(self):
        # "civilian" is present everywhere, so adding it to an ANY-tag filter
        # silently leaks harbor rescues into inland settlement noticeboards.
        self.assertEqual(["maritime"], self.family["requiredAnyTags"])
        coastal, inland = [], []
        for settlement in WORLD["settlements"]:
            tags = self.runtime.settlement_context(settlement)
            (coastal if "maritime" in tags else inland).append(settlement)
        self.assertTrue(coastal, "no real maritime settlements to exercise")
        self.assertTrue(inland, "no real inland settlements to exercise")
        self.assertTrue(all(self.runtime._eligible(s, self.family) for s in coastal))
        self.assertTrue(all(not self.runtime._eligible(s, self.family) for s in inland))

    def test_four_cases_are_editorially_distinct_and_without_debug_titles(self):
        self.assertEqual({"plain", "contested", "urgent", "scarce"}, set(self.variants))
        for field in ("title", "summary", "dialogue", "objectives", "alternate", "failure"):
            values = [json.dumps(v[field], ensure_ascii=False) for v in self.variants.values()]
            self.assertEqual(4, len(set(values)), f"cloned harbor rescue {field}")
        for key, variant in self.variants.items():
            self.assertNotIn(": " + key.capitalize(), variant["title"])
            text = json.dumps(variant, ensure_ascii=False).lower()
            self.assertNotIn("substitute only a context-appropriate material", text)
            self.assertNotIn("ask for accountable help, not an unquestioned errand", text)

    def test_saved_legacy_inland_offer_is_not_silently_rerolled(self):
        # A historical offer might have been allocated inland under the old
        # "maritime OR civilian" rule. Retain its stable identity on restore,
        # even though new offers are restricted to maritime settlements.
        snapshot = self.runtime.snapshot()
        first_inland = next(
            s for s in WORLD["settlements"]
            if "maritime" not in self.runtime.settlement_context(s)
        )
        offer = next(
            x for x in snapshot["offers"]
            if x["settlementId"] == first_inland["id"]
        )
        offer["familyId"] = self.family["id"]
        offer["variantId"] = "scarce"
        offer["category"] = self.family["category"]
        replacement = LocalQuestRuntime(
            SOURCE, WORLD["settlements"],
            campaign_seed="issue_600_content_gate", state=snapshot
        )
        self.assertEqual(snapshot, replacement.snapshot())
        self.assertEqual(offer["id"], next(
            x["id"] for x in replacement.snapshot()["offers"]
            if x["settlementId"] == first_inland["id"] and x["slot"] == offer["slot"]
        ))


    def test_scarce_variants_have_individual_context_and_no_template_language(self):
        scarce = {f["id"]: next(v for v in f["variants"] if v["id"] == "scarce") for f in SOURCE["families"]}
        self.assertEqual(16, len(scarce))
        for field in ("title", "summary", "dialogue", "objectives", "alternate", "failure"):
            rows = [json.dumps(v[field], ensure_ascii=False) for v in scarce.values()]
            self.assertEqual(16, len(set(rows)), "cloned scarce " + field)
        for family_id, v in scarce.items():
            self.assertNotIn(": Scarce", v["title"], family_id)
            prose = json.dumps(v, ensure_ascii=False).lower()
            for phrase in ("substitute only a context-appropriate material",
                           "scarcity makes quality, price, and allocation",
                           "ask for accountable help, not an unquestioned errand",
                           "return to the originating settlement and make a witnessed accounting"):
                self.assertNotIn(phrase, prose, family_id)
        # Non-material investigations, rescues, surveys and disputes cannot
        # satisfy their objectives by substituting a generic material.
        for family_id in ("harbor_missing", "marks_in_dust", "ledger_in_arrears",
                          "quiet_watch", "edge_of_the_chart", "boundary_stones"):
            self.assertNotIn("substitute", scarce[family_id]["alternate"].lower())


    def test_market_exchange_cases_are_authored_and_market_only(self):
        # Commerce incidents cannot spawn in settlements without a market.
        both_market = [s for s in WORLD["settlements"] if "market" in s.get("serviceIds", [])]
        without_market = [s for s in WORLD["settlements"] if "market" not in s.get("serviceIds", [])]
        self.assertTrue(both_market)
        self.assertTrue(without_market)
        for family_id in ("market_shortfall", "bales_and_balances"):
            family = self.runtime.families[family_id]
            for settlement in WORLD["settlements"]:
                self.assertEqual(
                    "market" in settlement.get("serviceIds", []),
                    self.runtime._eligible(settlement, family),
                    (family_id, settlement["id"]),
                )
            variants = family["_variants"]
            for field in ("title", "summary", "dialogue", "objectives", "alternate", "failure"):
                values = [
                    json.dumps(variants[case][field], ensure_ascii=False)
                    for case in ("plain", "contested", "urgent")
                ]
                self.assertEqual(3, len(set(values)), (family_id, field))
            for case in ("plain", "contested", "urgent"):
                variant = variants[case]
                self.assertNotIn(": " + case.capitalize(), variant["title"])
                prose = json.dumps(variant, ensure_ascii=False).lower()
                for phrase in (
                    "a routine request has become difficult",
                    "two parties describe the same need differently",
                    "a short deadline raises the cost of delay",
                    "ask for accountable help, not an unquestioned errand",
                    "return to the originating settlement and make a witnessed accounting",
                    "the giver is unavailable; use the witnessed alternate authority",
                ):
                    self.assertNotIn(phrase, prose, (family_id, case))


if __name__ == "__main__":
    unittest.main()
