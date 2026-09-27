import copy
import json
import random
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "_shared" / "engine"))
import economy

DATA = Path(__file__).resolve().parents[1] / "scenario" / "economy" / "economy.json"
WORLD = Path(__file__).resolve().parents[1] / "scenario" / "world" / "world.json"


def fixture():
    return {
        "schemaVersion": 1,
        "currencies": [{"id": "coin", "minorUnitsPerMajor": 100}],
        "goods": [
            {"id": "grain", "quantityUnitsPerDisplayUnit": 10, "itemTypeId": "grain_bundle"},
            {"id": "flour", "quantityUnitsPerDisplayUnit": 10, "itemTypeId": "flour_bundle"},
            {"id": "bread", "quantityUnitsPerDisplayUnit": 1, "itemTypeId": "bread_loaf"},
        ],
        "stores": [
            {"id": "person", "kind": "personal_inventory", "owner": {"kind": "character", "id": "hero"}, "capacityUnits": 20, "allowedGoodIds": ["grain", "bread"]},
            {"id": "warehouse_a", "kind": "warehouse", "owner": {"kind": "settlement", "id": "town"}, "capacityUnits": 100, "allowedGoodIds": ["grain", "flour", "bread"]},
            {"id": "warehouse_b", "kind": "settlement", "owner": {"kind": "settlement", "id": "town"}, "capacityUnits": 100, "allowedGoodIds": ["grain", "flour", "bread"]},
            {"id": "ship_hold", "kind": "ship", "owner": {"kind": "strategic_unit", "id": "ship"}, "capacityUnits": 20, "allowedGoodIds": ["grain"]},
            {"id": "fleet_hold", "kind": "fleet", "owner": {"kind": "fleet", "id": "fleet"}, "capacityUnits": 30, "allowedGoodIds": ["grain"]},
        ],
        "recipes": [
            {"id": "mill_grain", "inputs": [{"goodId": "grain", "quantityUnits": 3}], "outputs": [{"goodId": "flour", "quantityUnits": 2}]},
            {"id": "eat_bread", "inputs": [{"goodId": "bread", "quantityUnits": 1}], "outputs": [{"goodId": "grain", "quantityUnits": 1}]},
        ],
        "producers": [{"id": "mill", "storeId": "warehouse_a", "recipeId": "mill_grain", "owner": {"kind": "settlement", "id": "town"}}],
        "consumers": [{"id": "households", "storeId": "warehouse_a", "recipeId": "eat_bread", "owner": {"kind": "settlement", "id": "town"}}],
        "markets": [{"id": "town_market", "storeId": "warehouse_a", "owner": {"kind": "settlement", "id": "town"}}],
        "prices": [{"id": "grain_price", "marketId": "town_market", "goodId": "grain", "currencyId": "coin", "quantityUnits": 3, "amountMinor": 10}],
        "obligations": [
            {"id": "tax", "payerStoreId": "warehouse_a", "payeeStoreId": "warehouse_b", "currencyId": "coin", "amountMinor": 25, "intervalTicks": 30},
            {"id": "upkeep", "payerStoreId": "warehouse_a", "sinkRuleId": "ordinary_upkeep", "currencyId": "coin", "amountMinor": 7, "intervalTicks": 10},
        ],
        "sourceRules": [{"id": "mint", "assetKind": "currency", "assetIds": ["coin"], "storeKinds": ["settlement"]}],
        "sinkRules": [{"id": "ordinary_upkeep", "assetKind": "currency", "assetIds": ["coin"], "storeKinds": ["warehouse"]}],
    }


def state(a_grain=30, a_coin=100, b_grain=0, b_coin=0):
    values = [("person", [], []), ("warehouse_a", [("grain", a_grain)], [("coin", a_coin)]),
              ("warehouse_b", [("grain", b_grain)], [("coin", b_coin)]), ("ship_hold", [], []), ("fleet_hold", [], [])]
    return {"schemaVersion": 1, "storeBalances": [
        {"id": ident, "storeId": ident,
         "goods": [{"goodId": key, "quantityUnits": value} for key, value in goods if value],
         "currencies": [{"currencyId": key, "amountMinor": value} for key, value in money if value]}
        for ident, goods, money in values], "processedTransactionIds": []}


def total(value, kind, asset):
    lines, key, amount = ("goods", "goodId", "quantityUnits") if kind == "good" else ("currencies", "currencyId", "amountMinor")
    return sum(line[amount] for store in value["storeBalances"] for line in store[lines] if line[key] == asset)


class EconomyTests(unittest.TestCase):
    def test_scenario_data_and_cross_contract_stable_ids_validate(self):
        payload = json.loads(DATA.read_text())
        world = json.loads(WORLD.read_text())
        external = {name: {x["id"] for x in world[field]} for name, field in {
            "polity": "polities", "province": "provinces", "settlement": "settlements", "strategic_unit": "strategicUnits",
            "army": "armies", "fleet": "fleets", "territorial_holding": "territorialHoldings", "character": "characters"}.items()}
        economy.validate_catalog(payload["catalog"], external)
        economy.validate_state(payload["catalog"], payload["state"])
        self.assertNotIn("handle", DATA.read_text().lower())

    def test_balanced_goods_and_money_transfers_conserve_exactly(self):
        for kind, asset, amount in [("good", "grain", 7), ("currency", "coin", 31)]:
            before = state()
            result = economy.apply_transfer(fixture(), before, {"id": f"move_{kind}", "assetKind": kind, "assetId": asset, "amount": amount, "sourceStoreId": "warehouse_a", "destinationStoreId": "warehouse_b"})
            self.assertEqual(total(before, kind, asset), total(result.state, kind, asset))
            self.assertEqual([], before["processedTransactionIds"], "operations are atomic and immutable")

    def test_production_consumption_and_recurring_tax_upkeep(self):
        produced = economy.execute_recipe(fixture(), state(), {"id": "production_one", "actorKind": "producer", "actorId": "mill", "batches": 2})
        self.assertEqual(24, total(produced.state, "good", "grain"))
        self.assertEqual(4, total(produced.state, "good", "flour"))
        taxed = economy.settle_obligation(fixture(), produced.state, "tax", "tax_one")
        self.assertEqual(100, total(taxed.state, "currency", "coin"))
        upkeep = economy.settle_obligation(fixture(), taxed.state, "upkeep", "upkeep_one")
        self.assertEqual(93, total(upkeep.state, "currency", "coin"))

    def test_insufficient_funds_capacity_and_incompatible_goods_are_atomic(self):
        cases = [
            {"id": "too_much_money", "assetKind": "currency", "assetId": "coin", "amount": 101, "sourceStoreId": "warehouse_a", "destinationStoreId": "warehouse_b"},
            {"id": "too_much_cargo", "assetKind": "good", "assetId": "grain", "amount": 21, "sourceStoreId": "warehouse_a", "destinationStoreId": "ship_hold"},
            {"id": "wrong_cargo", "assetKind": "good", "assetId": "flour", "amount": 1, "sourceStoreId": "warehouse_a", "destinationStoreId": "ship_hold"},
        ]
        base = state()
        base["storeBalances"][1]["goods"].append({"goodId": "flour", "quantityUnits": 1})
        for operation in cases:
            with self.subTest(operation["id"]), self.assertRaises(economy.EconomyError):
                economy.apply_transfer(fixture(), base, operation)
        self.assertEqual([], base["processedTransactionIds"])

    def test_unauthorized_creation_destruction_overdraw_and_replay_fail(self):
        with self.assertRaises(economy.EconomyError):
            economy.apply_authorized_adjustment(fixture(), state(), {"id": "bad_mint", "direction": "source", "ruleId": "ordinary_upkeep", "storeId": "warehouse_a", "assetKind": "currency", "assetId": "coin", "amount": 1})
        with self.assertRaises(economy.EconomyError):
            economy.apply_authorized_adjustment(fixture(), state(a_coin=1), {"id": "overdraw", "direction": "sink", "ruleId": "ordinary_upkeep", "storeId": "warehouse_a", "assetKind": "currency", "assetId": "coin", "amount": 2})
        done = economy.apply_transfer(fixture(), state(), {"id": "once", "assetKind": "good", "assetId": "grain", "amount": 1, "sourceStoreId": "warehouse_a", "destinationStoreId": "warehouse_b"})
        with self.assertRaisesRegex(economy.EconomyError, "already processed"):
            economy.apply_transfer(fixture(), done.state, {"id": "once", "assetKind": "good", "assetId": "grain", "amount": 1, "sourceStoreId": "warehouse_a", "destinationStoreId": "warehouse_b"})

    def test_integer_rounding_is_deterministic_half_up(self):
        price = fixture()["prices"][0]
        self.assertEqual([3, 7, 10, 13], [economy.quote_amount_minor(price, q) for q in (1, 2, 3, 4)])
        self.assertEqual(2997, sum(economy.quote_amount_minor(price, 1) for _ in range(999)))

    def test_invalid_duplicates_references_numbers_capacities_and_recipes(self):
        mutations = []
        bad = fixture(); bad["goods"].append(copy.deepcopy(bad["goods"][0])); mutations.append(bad)
        bad = fixture(); bad["prices"][0]["goodId"] = "missing"; mutations.append(bad)
        bad = fixture(); bad["stores"][1]["capacityUnits"] = -1; mutations.append(bad)
        bad = fixture(); bad["prices"][0]["amountMinor"] = float("inf"); mutations.append(bad)
        bad = fixture(); bad["recipes"][0]["inputs"] = []; mutations.append(bad)
        bad = fixture(); bad["recipes"][0]["outputs"][0]["goodId"] = "missing"; mutations.append(bad)
        for bad in mutations:
            with self.subTest(bad=bad), self.assertRaises(economy.EconomyError):
                economy.validate_catalog(bad)

    def test_generated_sequence_checks_invariants_after_every_operation(self):
        rng, current = random.Random(32), state(a_grain=50)
        for index in range(100):
            source, destination = ("warehouse_a", "warehouse_b") if rng.randrange(2) == 0 else ("warehouse_b", "warehouse_a")
            available = next((x["quantityUnits"] for s in current["storeBalances"] if s["storeId"] == source for x in s["goods"] if x["goodId"] == "grain"), 0)
            if not available:
                continue
            before = total(current, "good", "grain")
            current = economy.apply_transfer(fixture(), current, {"id": f"generated_{index}", "assetKind": "good", "assetId": "grain", "amount": rng.randint(1, available), "sourceStoreId": source, "destinationStoreId": destination}).state
            economy.validate_state(fixture(), current)
            self.assertEqual(before, total(current, "good", "grain"))


if __name__ == "__main__":
    unittest.main()
