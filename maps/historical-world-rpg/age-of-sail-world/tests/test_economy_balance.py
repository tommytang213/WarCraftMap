import json
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tooling"))
import economy_balance as eb

class EconomyBalanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg=eb.load(eb.CONFIG);cls.settlements,cls.routes=eb.load_world()

    def test_authoritative_balance_and_every_settlement_validate(self):
        eb.validate_config(self.cfg,self.settlements,self.routes)
        world=json.loads((ROOT/"scenario/world/world.json").read_text())
        self.assertLessEqual(set(self.settlements),{x["id"] for x in world["settlements"]})
        for row in self.settlements.values():
            p=eb.profile(self.cfg,row)
            self.assertLessEqual(len(p["goods"]),self.cfg["performanceBudgets"]["maximumSettlementGoods"])
            self.assertLess(p["logistics"]["personal"],p["logistics"]["ship"])
            self.assertLess(p["logistics"]["ship"],p["logistics"]["army"])
            self.assertLess(p["logistics"]["army"],p["logistics"]["warehouse"])

    def test_all_scenarios_seeds_and_execution_modes_meet_envelopes(self):
        report=eb.run_all(self.cfg,self.settlements,self.routes)
        self.assertEqual(len(self.cfg["scenarios"])*len(self.cfg["simulationSeeds"]),report["runCount"])
        self.assertEqual(set(eb.REGIONS),set(report["regional"]))
        self.assertEqual(len(self.settlements),len(report["settlements"]))
        self.assertEqual([],report["outliers"])
        self.assertTrue(all(not value for value in report["diagnostics"].values() if isinstance(value,bool)))

    def test_accounting_covers_finance_goods_and_actual_connectivity(self):
        state,metrics,_=eb.simulate(self.cfg,self.settlements,"wartime",1450,routes=self.routes)
        self.assertEqual(set(self.cfg["authorizedSources"]+self.cfg["authorizedSinks"]),set(state["ledger"]))
        self.assertTrue(all(value>=0 for value in state["ledger"].values()))
        self.assertTrue(all(value>=0 for value in state["treasury"].values()))
        self.assertGreaterEqual(metrics["connectedSettlementPermille"],self.cfg["envelopes"]["connectedSettlementPermille"]["minimum"])
        # Authored signature goods survive derivation into each market basket.
        for ident,row in self.settlements.items():
            p=eb.profile(self.cfg,row)
            self.assertLessEqual(set(row["identity"]["production"]),set(p["startingStockByGood"]))

    def test_conservation_rejects_unauthorized_source_or_sink(self):
        bad=json.loads(json.dumps(self.cfg));bad["authorizedSources"].remove("historical_import")
        with self.assertRaises(eb.BalanceError): eb.validate_config(bad,self.settlements,self.routes)
        bad=json.loads(json.dumps(self.cfg));bad["authorizedSinks"].remove("obligation")
        with self.assertRaises(eb.BalanceError): eb.validate_config(bad,self.settlements,self.routes)

if __name__=="__main__": unittest.main()
