import copy, json, sys, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent / "_shared" / "engine"))
from piracy import PiracyError, PiracyRuntime, PiracySaveAdapter


class PiracyTests(unittest.TestCase):
    def setUp(self):
        self.defs = json.loads((ROOT / "scenario/naval/piracy.json").read_text())
        self.runtime = PiracyRuntime(self.defs)

    def action(self, ident="prize_one", **changes):
        row = {"id": ident, "playerId": "captain", "targetId": "merchant_one",
               "targetKind": "merchant_ship", "victimPolityId": "france", "regionId": "caribbean",
               "tick": 40, "authorityValidated": True, "cargo": [{"goodId": "sugar", "quantityUnits": 5}],
               "moneyMinor": 2000, "prisoners": 2, "prisonerOutcome": "ransom", "vesselOutcome": "capture"}
        row.update(changes); return row

    def test_privateering_is_lawful_and_distinct_from_piracy(self):
        self.runtime.issue_commission("english_marque", player_id="captain", issuer_polity_id="england",
            target_polity_ids=["france"], issued_tick=1, expires_tick=100, reward_permille=250)
        result = self.runtime.resolve_prize(self.action(commissionId="english_marque"))
        self.assertTrue(result.lawful_privateering); self.assertEqual(2500, result.money_minor)
        self.assertFalse(self.runtime.players["captain"]["outlaw"])
        self.assertEqual({"france": -4, "england": 2}, result.event["relationEffects"])
        self.runtime.revoke_commission("english_marque", 50)
        with self.assertRaisesRegex(PiracyError, "expired or revoked"):
            self.runtime.resolve_prize(self.action("late_prize", targetId="merchant_two", tick=51, commissionId="english_marque"))

    def test_unlicensed_prize_cargo_ship_notoriety_and_anti_duplication(self):
        result = self.runtime.resolve_prize(self.action())
        self.assertEqual(({"goodId": "sugar", "quantityUnits": 5},), result.cargo)
        self.assertEqual(("capture", False), (result.vessel_outcome, result.lawful_privateering))
        self.assertTrue(self.runtime.players["captain"]["outlaw"])
        before = self.runtime.snapshot()
        replay = self.runtime.resolve_prize(self.action())
        self.assertEqual(result, replay); self.assertEqual(before, self.runtime.snapshot())
        with self.assertRaisesRegex(PiracyError, "anti-farming"):
            self.runtime.resolve_prize(self.action("prize_two", tick=41))

    def test_haven_world_response_and_independent_polity_progression(self):
        for n in range(5):
            self.runtime.resolve_prize(self.action(f"raid_{n}", targetId=f"coast_{n}", targetKind="coastal_target",
                tick=40 + n, moneyMinor=2000, cargo=[], vesselOutcome="release"))
        self.runtime.use_haven("captain", "caribbean_free_haven", "fence", tick=50, amount_minor=500)
        contract = self.runtime.accept_contract("nassau_tip", player_id="captain", contract_type_id="treasure_intelligence",
            haven_id="caribbean_free_haven", target_id="wreck_one", expires_tick=90)
        self.assertEqual("wreck_one", contract["targetId"])
        self.runtime.complete_contract("nassau_tip", player_id="captain", tick=55, reward_minor=100, target_validated=True)
        response = self.runtime.world_response("caribbean", naval_strength=100, treaty_pressure=20, relation_hostility=10, current_wars=2)
        self.assertGreater(response["convoyChancePermille"], 0); self.assertGreater(response["pricePressurePermille"], 0)
        polity = self.runtime.found_polity("free_nassau", player_id="captain", government_form_id="free_republic",
            name="Free Nassau", title="First Captain", capital_settlement_id="nassau",
            territory_ids=["nassau"], tick=60)
        self.assertTrue(polity["ordinarySystemsEnabled"]); self.assertEqual("independent", polity["status"])
        self.runtime.set_recognition("free_nassau", "england", "tolerated", tick=61)
        self.runtime.set_recognition("free_nassau", "france", "embargoed", tick=61)
        self.assertEqual({"england": "tolerated", "france": "embargoed"}, self.runtime.polities["free_nassau"]["recognition"])

    def test_save_reconstruction_preserves_territory_diplomacy_and_cooldowns(self):
        self.runtime.resolve_prize(self.action())
        adapter = PiracySaveAdapter(self.runtime, {"calendar": {"tick": 40}})
        saved = adapter.capture_world(); resumed = PiracyRuntime(self.defs)
        PiracySaveAdapter(resumed, {}).activate(saved, copy.deepcopy(saved["piracyState"]))
        self.assertEqual(self.runtime.snapshot(), resumed.snapshot())
        with self.assertRaisesRegex(PiracyError, "anti-farming"):
            resumed.resolve_prize(self.action("after_load", tick=41))
        legacy = adapter.migrate_legacy_world({"calendar": {"tick": 1}})
        self.assertIn("piracyState", legacy); self.assertEqual({}, legacy["piracyState"]["players"])

    def test_illegal_targets_and_unvalidated_crime_are_rejected_atomically(self):
        baseline = self.runtime.snapshot()
        with self.assertRaisesRegex(PiracyError, "ineligible"):
            self.runtime.resolve_prize(self.action(targetKind="civilian_home"))
        with self.assertRaisesRegex(PiracyError, "authority"):
            self.runtime.resolve_prize(self.action(authorityValidated=False))
        self.assertEqual(baseline, self.runtime.snapshot())


if __name__ == "__main__": unittest.main()
