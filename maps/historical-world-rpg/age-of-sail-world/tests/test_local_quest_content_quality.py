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
        self.assertTrue(both_market)
        # All 827 real settlements currently have markets. Check the actual
        # world AND the same real settlement with its market service removed;
        # do not invent a nonexistent real-world non-market settlement.
        without_market_service = dict(both_market[0])
        without_market_service["serviceIds"] = [
            item for item in both_market[0].get("serviceIds", []) if item != "market"
        ]
        for family_id in ("market_shortfall", "bales_and_balances"):
            family = self.runtime.families[family_id]
            self.assertFalse(self.runtime._eligible(without_market_service, family))
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


    def test_sealed_dispatch_cases_reject_generic_delivery_boilerplate(self):
        # Source-level editorial regression, not an authoritative in-game receipt.
        variants = self.runtime.families["sealed_dispatch"]["_variants"]
        self.assertEqual({"plain", "contested", "urgent", "scarce"}, set(variants))
        for field in ("title", "summary", "dialogue", "objectives", "alternate", "failure"):
            self.assertEqual(4, len({
                json.dumps(v[field], ensure_ascii=False) for v in variants.values()
            }), field)
        for case_id, v in variants.items():
            self.assertNotIn(": " + case_id.capitalize(), v["title"])
            prose = json.dumps(v, ensure_ascii=False).lower()
            for template in (
                "a routine request has become difficult",
                "two parties describe the same need differently",
                "ask for accountable help, not an unquestioned errand",
                "return to the originating settlement and make a witnessed accounting",
            ):
                self.assertNotIn(template, prose, case_id)

    def test_bale_shortfall_title_does_not_prejudge_fraud(self):
        v = self.runtime.families["bales_and_balances"]["_variants"]["scarce"]
        self.assertEqual("The Unfilled Bale Order", v["title"])
        self.assertNotIn("false weight", v["summary"].lower())


    def test_maritime_rigging_has_real_distinct_repairs_not_debug_labels(self):
        # Historical source/editorial gate. Not native proof that a ship, item,
        # timed hazard, objective receipt or fleet-supply consumer exists.
        family = self.runtime.families["tide_and_rigging"]
        variants = family["_variants"]
        self.assertEqual({"plain", "contested", "urgent", "scarce"}, set(variants))
        self.assertEqual({"maritime", "port"}, set(family["requiredAnyTags"]))
        for settlement in WORLD["settlements"]:
            is_port = "maritime" in self.runtime.settlement_context(settlement)
            self.assertEqual(is_port, self.runtime._eligible(settlement, family))
        for field in ("title", "summary", "dialogue", "objectives", "alternate", "failure",
                      "strategicAccomplishment"):
            rows = [json.dumps(v[field], ensure_ascii=False) for v in variants.values()]
            self.assertEqual(4, len(set(rows)), "repeated maritime " + field)
        for case, variant in variants.items():
            self.assertNotIn(": " + case.capitalize(), variant["title"])
            self.assertIn("trial", " ".join(variant["objectives"]).lower())
            self.assertEqual(["currency", "experience", "fleet_supply"],
                             [x["kind"] for x in variant["rewards"]])
            text = json.dumps(variant, ensure_ascii=False).lower()
            for filler in ("a routine request has become difficult",
                           "two parties describe the same need differently",
                           "ask for accountable help, not an unquestioned errand",
                           "return to the originating settlement and make a witnessed accounting"):
                self.assertNotIn(filler, text, case)


    def test_ledger_disputes_are_distinct_and_admin_eligible(self):
        # Editorial source gate. Actual hearings, receipts, stability effects
        # and native Warcraft presentation still need execution evidence.
        family = self.runtime.families["ledger_in_arrears"]
        variants = family["_variants"]
        self.assertEqual(["administration"], family["requiredAnyTags"])
        admin = [s for s in WORLD["settlements"]
                 if "administration" in self.runtime.settlement_context(s)]
        other = [s for s in WORLD["settlements"]
                 if "administration" not in self.runtime.settlement_context(s)]
        self.assertTrue(admin)
        self.assertTrue(other)
        self.assertTrue(all(self.runtime._eligible(s, family) for s in admin))
        self.assertTrue(all(not self.runtime._eligible(s, family) for s in other))
        self.assertEqual({"plain", "contested", "urgent", "scarce"}, set(variants))
        for field in ("title", "summary", "dialogue", "objectives",
                      "alternate", "failure", "strategicAccomplishment"):
            values = [json.dumps(v[field], ensure_ascii=False) for v in variants.values()]
            self.assertEqual(4, len(set(values)), "cloned administrative " + field)
        for case, variant in variants.items():
            self.assertNotIn(": " + case.capitalize(), variant["title"])
            prose = json.dumps(variant, ensure_ascii=False).lower()
            for filler in ("a routine request has become difficult",
                           "two parties describe the same need differently",
                           "ask for accountable help, not an unquestioned errand",
                           "return to the originating settlement and make a witnessed accounting"):
                self.assertNotIn(filler, prose, case)
            self.assertEqual(["currency", "experience", "stability"],
                             [x["kind"] for x in variant["rewards"]])



    def test_neighbor_aid_and_investigations_are_contextual_not_cloned(self):
        # Editorial source test only; neither WC3 interaction nor applied effects.
        expected = {
            "neighbors_in_need": ["currency", "experience", "settlement_reputation"],
            "marks_in_dust": ["currency", "experience", "reduced_unrest"],
        }
        for family_id, reward_kinds in expected.items():
            family = self.runtime.families[family_id]
            variants = family["_variants"]
            self.assertEqual({"plain", "contested", "urgent", "scarce"}, set(variants))
            for field in ("title", "summary", "dialogue", "objectives", "alternate", "failure"):
                values = [json.dumps(v[field], ensure_ascii=False) for v in variants.values()]
                self.assertEqual(4, len(set(values)), (family_id, field))
            for case, variant in variants.items():
                self.assertNotIn(": " + case.capitalize(), variant["title"])
                self.assertEqual(2, len(variant["objectives"]))
                self.assertEqual(reward_kinds, [r["kind"] for r in variant["rewards"]])
                prose = json.dumps(variant, ensure_ascii=False).lower()
                for boilerplate in (
                    "a routine request has become difficult",
                    "two parties describe the same need differently",
                    "a short deadline raises the cost of delay",
                    "ask for accountable help, not an unquestioned errand",
                    "return to the originating settlement and make a witnessed accounting",
                    "the giver is unavailable; use the witnessed alternate authority",
                ):
                    self.assertNotIn(boilerplate, prose, (family_id, case))


    def test_edge_of_chart_cases_preserve_known_boundaries_and_distinct_evidence(self):
        # Issue #600 editorial source gate only. Neither movement, native map
        # reveal nor survey-world mutation is established by these text checks.
        family = self.runtime.families["edge_of_the_chart"]
        variants = family["_variants"]
        self.assertEqual({"plain", "contested", "urgent", "scarce"}, set(variants))
        for field in ("title", "summary", "dialogue", "objectives", "alternate", "failure"):
            self.assertEqual(4, len({json.dumps(v[field], ensure_ascii=False)
                                     for v in variants.values()}), field)
        for case, variant in variants.items():
            self.assertEqual(2, len(variant["objectives"]), case)
            self.assertEqual(["currency", "experience"],
                             [reward["kind"] for reward in variant["rewards"]], case)
            self.assertFalse(variant["guidance"]["undiscoveredLeak"], case)
            self.assertNotIn(": " + case.capitalize(), variant["title"])
            prose = json.dumps(variant, ensure_ascii=False).lower()
            for filler in ("a routine request has become difficult",
                           "two parties describe the same need differently",
                           "a short deadline raises the cost of delay",
                           "ask for accountable help, not an unquestioned errand",
                           "return to the originating settlement and make a witnessed accounting"):
                self.assertNotIn(filler, prose, case)
        self.assertIn("unvisited ground", " ".join(variants["plain"]["objectives"]))
        self.assertIn("competing claims", " ".join(variants["contested"]["objectives"]))
        self.assertIn("without exposing unseen locations", " ".join(variants["urgent"]["objectives"]))

    def test_quiet_watch_cases_have_distinct_evidence_and_safe_dispositions(self):
        # Issue #600 source/editorial gate, not proof of production arrest,
        # watch movement, reduced-crime mutations, or native Warcraft UI.
        family = self.runtime.families["quiet_watch"]
        variants = family["_variants"]
        self.assertEqual(["security"], family["requiredAnyTags"])
        self.assertEqual({"plain", "contested", "urgent", "scarce"}, set(variants))
        for field in ("title", "summary", "dialogue", "objectives", "alternate", "failure"):
            self.assertEqual(4, len({json.dumps(v[field], ensure_ascii=False)
                                     for v in variants.values()}), field)
        for case, variant in variants.items():
            self.assertEqual(2, len(variant["objectives"]), case)
            self.assertEqual(["currency", "experience", "reduced_crime"],
                             [reward["kind"] for reward in variant["rewards"]], case)
            self.assertFalse(variant["guidance"]["undiscoveredLeak"], case)
            self.assertNotIn(": " + case.capitalize(), variant["title"])
            prose = json.dumps(variant, ensure_ascii=False).lower()
            for filler in ("a routine request has become difficult",
                           "two parties describe the same need differently",
                           "ask for accountable help, not an unquestioned errand",
                           "return to the originating settlement and make a witnessed accounting",
                           "the giver is unavailable; use the witnessed alternate authority"):
                self.assertNotIn(filler, prose, case)
        self.assertIn("exposed approach", variants["plain"]["objectives"][1])
        self.assertIn("authorized detention", variants["contested"]["objectives"][1])
        self.assertIn("maintaining a guard", variants["urgent"]["objectives"][1])


    def test_workshop_watch_boundaries_and_routes_are_distinct_authored_cases(self):
        # Text-only #600 gate; does not prove playable objective/reward effects.
        expected = {
            "master_and_apprentice": ["currency", "experience"],
            "stores_for_watch": ["currency", "experience", "garrison_readiness"],
            "boundary_stones": ["currency", "experience", "reduced_unrest"],
            "route_hazards": ["currency", "experience"],
        }
        for family_id, kinds in expected.items():
            variants = self.runtime.families[family_id]["_variants"]
            self.assertEqual({"plain", "contested", "urgent", "scarce"}, set(variants))
            for key in ("title", "summary", "dialogue", "objectives", "alternate", "failure"):
                self.assertEqual(4, len({json.dumps(v[key], ensure_ascii=False)
                                         for v in variants.values()}), (family_id, key))
            for case, variant in variants.items():
                self.assertEqual(2, len(variant["objectives"]))
                self.assertEqual(kinds, [r["kind"] for r in variant["rewards"]])
                self.assertFalse(variant["guidance"]["undiscoveredLeak"])
                self.assertNotIn(": " + case.capitalize(), variant["title"])
                prose = json.dumps(variant, ensure_ascii=False).lower()
                for filler in ("a routine request has become difficult",
                               "two parties describe the same need differently",
                               "a short deadline raises the cost of delay",
                               "ask for accountable help, not an unquestioned errand",
                               "return to the originating settlement and make a witnessed accounting",
                               "the giver is unavailable; use the witnessed alternate authority"):
                    self.assertNotIn(filler, prose, (family_id, case))


if __name__ == "__main__":
    unittest.main()
