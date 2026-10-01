import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tooling"))
import global_goods


class GlobalGoodsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = global_goods.load(global_goods.CATALOG)
        cls.settlements, cls.routes = global_goods.load_settlements()
        cls.goods, cls.refs = global_goods.validate_catalog(cls.catalog, cls.settlements, cls.routes)

    def test_every_authored_identity_resolves_and_every_good_is_reachable(self):
        referenced = set(self.refs)
        exceptions = {x["id"] for x in self.catalog["abstractExceptions"]}
        self.assertEqual(set(self.goods), referenced - exceptions)
        self.assertGreaterEqual(len(self.goods), 80)
        self.assertTrue(all(g["itemTypeId"] for g in self.goods.values()))

    def test_settlement_markets_retain_local_identity_and_port_imports(self):
        profiles = {sid: global_goods.market_profile(self.catalog, row) for sid, row in self.settlements.items()}
        for sid, row in self.settlements.items():
            profile = profiles[sid]
            self.assertLessEqual(set(row["economyIdentity"]["production"]), set(profile["availableGoodIds"]))
            self.assertLess(profile["logistics"]["personal_inventory"], profile["logistics"]["ship"])
            self.assertLess(profile["logistics"]["ship"], profile["logistics"]["warehouse"])
        distinct = {tuple(x["availableGoodIds"]) for x in profiles.values()}
        self.assertGreater(len(distinct), len(global_goods.REGIONS) * 3)
        imported_ports = [x for sid, x in profiles.items() if self.settlements[sid].get("port") and x["importGoodIds"]]
        self.assertTrue(imported_ports)
        self.assertTrue(all(set(x["importGoodIds"]) <= set(x["availableGoodIds"]) for x in imported_ports))

    def test_storage_price_units_and_integrations_are_valid(self):
        for good in self.goods.values():
            self.assertGreater(good["basePriceMinor"], 0)
            self.assertGreater(good["quantityUnitsPerDisplayUnit"], 0)
            self.assertTrue(set(good["cargoKinds"]) <= set(good["storageKinds"]))
            self.assertIn("blockade", good["logisticsHooks"])
        self.assertEqual({"warehouses","shipCargo","fleetCargo","provisioning","questsEventsRewards","tradeUi","campaignPersistence","remoteManagement"}, set(self.catalog["integrations"]))

    def test_long_campaign_disruption_and_recovery_are_bounded(self):
        report = global_goods.build_report(self.catalog, self.settlements, self.routes)
        simulations = {x["scenario"]: x for x in report["simulations"]}
        self.assertEqual(set(global_goods.SCENARIOS), set(simulations))
        self.assertGreater(simulations["recovery"]["finalStock"], simulations["blockade"]["finalStock"])
        self.assertTrue(all(x["minimumStock"] > 0 for x in simulations.values()))
        maximum_base = max(x["basePriceMinor"] for x in self.goods.values())
        self.assertTrue(all(x["maximumPriceMinor"] <= maximum_base * 4 for x in simulations.values()))
        self.assertEqual({"unresolvedReferences":0,"unreachableGoods":0,"invalidCargoMappings":0,"missingItemRepresentations":0}, report["diagnostics"])


if __name__ == "__main__": unittest.main()
