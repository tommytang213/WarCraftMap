import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "_shared" / "engine"))
import economy
import trade


def fixtures():
    ec = {"schemaVersion": 1, "currencies": [{"id": "coin", "minorUnitsPerMajor": 100}],
          "goods": [{"id": "spice", "quantityUnitsPerDisplayUnit": 1, "itemTypeId": "spice_cargo"}],
          "stores": [
              {"id": "calicut_store", "kind": "settlement", "owner": {"kind": "settlement", "id": "calicut"}, "capacityUnits": 1000, "allowedGoodIds": ["spice"]},
              {"id": "london_store", "kind": "settlement", "owner": {"kind": "settlement", "id": "london"}, "capacityUnits": 1000, "allowedGoodIds": ["spice"]},
              {"id": "ship_hold", "kind": "ship", "owner": {"kind": "strategic_unit", "id": "ship"}, "capacityUnits": 30, "allowedGoodIds": ["spice"]},
              {"id": "warehouse", "kind": "warehouse", "owner": {"kind": "settlement", "id": "london"}, "capacityUnits": 200, "allowedGoodIds": ["spice"]}],
          "recipes": [], "producers": [], "consumers": [],
          "markets": [{"id": "calicut", "storeId": "calicut_store", "owner": {"kind": "settlement", "id": "calicut"}}, {"id": "london", "storeId": "london_store", "owner": {"kind": "settlement", "id": "london"}}],
          "prices": [], "obligations": [], "sourceRules": [], "sinkRules": []}
    state = {"schemaVersion": 1, "storeBalances": [
        {"id": "calicut_store", "storeId": "calicut_store", "goods": [{"goodId": "spice", "quantityUnits": 500}], "currencies": [{"currencyId": "coin", "amountMinor": 10000}]},
        {"id": "london_store", "storeId": "london_store", "goods": [{"goodId": "spice", "quantityUnits": 20}], "currencies": [{"currencyId": "coin", "amountMinor": 10000}]},
        {"id": "ship_hold", "storeId": "ship_hold", "goods": [], "currencies": [{"currencyId": "coin", "amountMinor": 10000}]},
        {"id": "warehouse", "storeId": "warehouse", "goods": [], "currencies": []}], "processedTransactionIds": []}
    tc = {"goods": [{"id": "spice", "name": "Pepper", "quantityUnitsPerDisplayUnit": 1, "basePriceMinor": 100, "priceElasticityPermille": 1000}],
          "marketRules": [{"marketId": x, "currencyId": "coin", "goodIds": ["spice"], "targetStockUnits": {"spice": 100}, "spreadPermille": 50, "priceFloorPermille": 300, "priceCeilingPermille": 4000} for x in ("calicut", "london")],
          "reputationTiers": [{"id": "known", "standingRequired": 100, "benefitIds": ["warehouse_access"]}, {"id": "factor", "standingRequired": 500, "benefitIds": ["major_contracts", "market_intelligence"]}]}
    return tc, ec, state


class PlayableTradeTests(unittest.TestCase):
    def test_release_goods_and_settlement_profiles_build_playable_rules(self):
        tooling = Path(__file__).resolve().parents[1] / "tooling"
        sys.path.insert(0, str(tooling)); import global_goods
        goods = json.loads((Path(__file__).resolve().parents[1] / "scenario/economy/global-goods.json").read_text())
        progression = json.loads((Path(__file__).resolve().parents[1] / "scenario/economy/playable-trade.json").read_text())
        settlements, routes = global_goods.load_settlements()
        profiles = [global_goods.market_profile(goods, row) for row in settlements.values()]
        built = trade.build_catalog(goods, profiles, progression)
        self.assertEqual(len(settlements), len(built["marketRules"]))
        self.assertTrue(all(x["goodIds"] and x["targetStockUnits"] for x in built["marketRules"]))
        self.assertIn("trade_network_privileges", built["reputationTiers"][-1]["benefitIds"])

    def test_long_distance_buy_carry_sell_profit_and_unlock(self):
        tc, ec, es = fixtures(); ts = trade.initial_state()
        bought = trade.execute(tc, ec, es, ts, {"id": "buy_1", "playerId": "p1", "marketId": "calicut", "goodId": "spice", "side": "buy", "quantityUnits": 10, "storeId": "ship_hold"})
        sold = trade.execute(tc, ec, bought.economy_state, bought.trade_state, {"id": "sell_1", "playerId": "p1", "marketId": "london", "originMarketId": "calicut", "goodId": "spice", "side": "sell", "quantityUnits": 10, "storeId": "ship_hold", "routeDifficultyPermille": 2000})
        self.assertGreater(sold.realized_profit_minor, 0)
        self.assertGreater(sold.standing_awarded, 0)
        self.assertIn("warehouse_access", sold.trade_state["players"]["p1"]["unlockedBenefitIds"])
        self.assertEqual(0, next((x["quantityUnits"] for x in next(s for s in sold.economy_state["storeBalances"] if s["storeId"] == "ship_hold")["goods"] if x["goodId"] == "spice"), 0))

    def test_shortage_disruption_and_development_affect_live_quote(self):
        tc, ec, es = fixtures()
        peaceful = trade.quote(tc, ec, es, "london", "spice", "buy", 1)
        crisis = trade.quote(tc, ec, es, "london", "spice", "buy", 1, {"blockadePermille": 500, "warPermille": 300, "consumptionPermille": 1200})
        developed = trade.quote(tc, ec, es, "london", "spice", "buy", 1, {"tradeConnectivityPermille": 1500, "technologyPermille": 250, "institutionPermille": 100})
        self.assertGreater(crisis["amountMinor"], peaceful["amountMinor"])
        self.assertLess(developed["amountMinor"], peaceful["amountMinor"])

    def test_capacity_replay_and_stale_quote_exploits_fail(self):
        tc, ec, es = fixtures(); ts = trade.initial_state()
        with self.assertRaisesRegex(economy.EconomyError, "capacity"):
            trade.execute(tc, ec, es, ts, {"id": "too_big", "playerId": "p1", "marketId": "calicut", "goodId": "spice", "side": "buy", "quantityUnits": 31, "storeId": "ship_hold"})
        done = trade.execute(tc, ec, es, ts, {"id": "once", "playerId": "p1", "marketId": "calicut", "goodId": "spice", "side": "buy", "quantityUnits": 1, "storeId": "ship_hold"})
        with self.assertRaisesRegex(economy.EconomyError, "already processed"):
            trade.execute(tc, ec, done.economy_state, done.trade_state, {"id": "once", "playerId": "p1", "marketId": "calicut", "goodId": "spice", "side": "buy", "quantityUnits": 1, "storeId": "ship_hold"})
        before = trade.quote(tc, ec, es, "calicut", "spice", "buy", 10)
        after = trade.quote(tc, ec, done.economy_state, "calicut", "spice", "buy", 10)
        self.assertGreaterEqual(after["amountMinor"], before["amountMinor"])

    def test_saturation_anti_farming_and_uncosted_rewards(self):
        tc, ec, es = fixtures(); ts = trade.initial_state()
        awards = []
        for i in range(3):
            b = trade.execute(tc, ec, es, ts, {"id": f"b{i}", "playerId": "p1", "marketId": "calicut", "goodId": "spice", "side": "buy", "quantityUnits": 3, "storeId": "ship_hold"})
            s = trade.execute(tc, ec, b.economy_state, b.trade_state, {"id": f"s{i}", "playerId": "p1", "marketId": "london", "originMarketId": "calicut", "goodId": "spice", "side": "sell", "quantityUnits": 3, "storeId": "ship_hold"})
            awards.append(s.standing_awarded); es, ts = s.economy_state, s.trade_state
        self.assertGreater(awards[0], awards[1]); self.assertGreaterEqual(awards[1], awards[2])
        # Quest/reward cargo can be sold but cannot mint merchant standing without cost basis.
        reward = copy.deepcopy(es); next(x for x in reward["storeBalances"] if x["storeId"] == "ship_hold")["goods"] = [{"goodId": "spice", "quantityUnits": 1}]
        sold = trade.execute(tc, ec, reward, ts, {"id": "reward_sale", "playerId": "p1", "marketId": "london", "goodId": "spice", "side": "sell", "quantityUnits": 1, "storeId": "ship_hold"})
        self.assertEqual(0, sold.standing_awarded)

    def test_knowledge_trends_warehouse_transfer_and_save_resume_equivalence(self):
        tc, ec, es = fixtures(); ts = trade.initial_state()
        self.assertEqual([], trade.inspect_market(tc, ec, es, ts, "london", "p1", set()))
        rows = trade.inspect_market(tc, ec, es, ts, "london", "p1", {"spice"})
        self.assertEqual(("spice", "steady"), (rows[0]["goodId"], rows[0]["trend"]))
        bought = trade.execute(tc, ec, es, ts, {"id": "buy", "playerId": "p1", "marketId": "calicut", "goodId": "spice", "side": "buy", "quantityUnits": 5, "storeId": "ship_hold"})
        known = trade.inspect_market(tc, ec, bought.economy_state, bought.trade_state, "london", "p1", {"spice"})[0]
        self.assertEqual(5, known["heldUnits"])
        self.assertGreater(known["projectedProfitLossMinor"], 0)
        moved, moved_trade = trade.transfer_cargo(ec, bought.economy_state, bought.trade_state, "p1", "warehouse_move", "spice", 5, "ship_hold", "warehouse")
        self.assertEqual(5, next(x["quantityUnits"] for x in next(s for s in moved["storeBalances"] if s["storeId"] == "warehouse")["goods"] if x["goodId"] == "spice"))
        self.assertEqual("warehouse", moved_trade["players"]["p1"]["lots"][0]["storeId"])
        raw = json.dumps({"economy": moved, "trade": moved_trade}, sort_keys=True)
        resumed = json.loads(raw)
        self.assertEqual({"economy": moved, "trade": moved_trade}, resumed)
        self.assertEqual(trade.quote(tc, ec, moved, "london", "spice", "sell", 5), trade.quote(tc, ec, resumed["economy"], "london", "spice", "sell", 5))


if __name__ == "__main__": unittest.main()
