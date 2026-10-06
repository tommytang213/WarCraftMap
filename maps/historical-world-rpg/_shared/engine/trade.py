"""Scenario-neutral, persistent player-facing commodity trading.

This layer deliberately composes :mod:`economy`: stores, balances, capacity and
transaction replay protection remain authoritative there.  Trade state contains
only information which cannot be reconstructed from a balance (cost basis,
observed prices and dedicated merchant standing).
"""
from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any, Mapping

import economy


class TradeError(ValueError):
    pass


@dataclass(frozen=True)
class TradeResult:
    economy_state: dict[str, Any]
    trade_state: dict[str, Any]
    amount_minor: int
    realized_profit_minor: int
    standing_awarded: int


def initial_state() -> dict[str, Any]:
    return {"schemaVersion": 1, "players": {}, "marketHistory": {}}


def build_catalog(goods_catalog: Mapping[str, Any], market_profiles: list[Mapping[str, Any]],
                  progression: Mapping[str, Any]) -> dict[str, Any]:
    """Join scenario-authored goods and settlement profiles for the runtime."""
    defaults = progression["marketDefaults"]
    return {"goods": copy.deepcopy(goods_catalog["goods"]),
            "marketRules": [{"marketId": x["settlementId"], "currencyId": goods_catalog["currencyId"],
                              "goodIds": list(x["availableGoodIds"]),
                              "targetStockUnits": dict(x["inventoryUnits"]), **defaults}
                             for x in market_profiles],
            "reputationTiers": copy.deepcopy(progression["reputationTiers"])}


def _player(state: dict[str, Any], player_id: str) -> dict[str, Any]:
    return state["players"].setdefault(player_id, {
        "standing": 0, "lifetimeVolumeMinor": 0, "realizedProfitMinor": 0,
        "unlockedBenefitIds": [], "lots": [], "routeHistory": {},
    })


def validate_state(state: Mapping[str, Any]) -> None:
    if not isinstance(state, Mapping) or state.get("schemaVersion") != 1:
        raise TradeError("trade state schemaVersion must be 1")
    if not isinstance(state.get("players"), Mapping) or not isinstance(state.get("marketHistory"), Mapping):
        raise TradeError("trade state requires players and marketHistory objects")
    for pid, row in state["players"].items():
        if not isinstance(pid, str) or not isinstance(row, Mapping):
            raise TradeError("invalid player trade state")
        for key in ("standing", "lifetimeVolumeMinor", "realizedProfitMinor"):
            if isinstance(row.get(key), bool) or not isinstance(row.get(key), int) or row[key] < 0 and key != "realizedProfitMinor":
                raise TradeError(f"player {pid}: invalid {key}")
        if not isinstance(row.get("lots"), list) or not isinstance(row.get("routeHistory"), Mapping):
            raise TradeError(f"player {pid}: invalid lots or route history")


def _indexes(catalog: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    goods = {x["id"]: x for x in catalog.get("goods", [])}
    rules = {x["marketId"]: x for x in catalog.get("marketRules", [])}
    tiers = sorted(catalog.get("reputationTiers", []), key=lambda x: x["standingRequired"])
    return goods, rules, tiers


def _balance(economy_state: Mapping[str, Any], store_id: str) -> Mapping[str, Any]:
    try:
        return next(x for x in economy_state["storeBalances"] if x["storeId"] == store_id)
    except StopIteration as exc:
        raise TradeError(f"missing store {store_id!r}") from exc


def _quantity(balance: Mapping[str, Any], good_id: str) -> int:
    return next((x["quantityUnits"] for x in balance["goods"] if x["goodId"] == good_id), 0)


def quote(catalog: Mapping[str, Any], economy_catalog: Mapping[str, Any], economy_state: Mapping[str, Any],
          market_id: str, good_id: str, side: str, quantity_units: int,
          campaign: Mapping[str, Any] | None = None) -> dict[str, int]:
    """Return a deterministic quote from current stock and campaign conditions.

    Prices are recomputed for every transaction, so a displayed quote is never
    authority. Sum marginal prices on the traversed stock interval: the midpoint
    of each indivisible quantity unit is rounded toward the upper stock endpoint
    for BOTH directions. This is additive across partitions, including price
    bounds and rounding steps. Rounding one midpoint for an entire order is not.
    All arithmetic is integer-only. Quantity-to-currency conversion is rounded
    only at final settlement, after the per-edge base-price and spread rounding.
    """
    if side not in {"buy", "sell"} or quantity_units < 1:
        raise TradeError("quote requires buy/sell and a positive quantity")
    goods, rules, _ = _indexes(catalog)
    rule, good = rules.get(market_id), goods.get(good_id)
    if rule is None or good is None or good_id not in rule["goodIds"]:
        raise TradeError("good is not traded at this market")
    market = next((x for x in economy_catalog["markets"] if x["id"] == market_id), None)
    if market is None:
        raise TradeError("market is absent from the authoritative economy catalog")
    stock = _quantity(_balance(economy_state, market["storeId"]), good_id)
    target = max(1, rule.get("targetStockUnits", {}).get(good_id, good["quantityUnitsPerDisplayUnit"] * 10))
    elasticity = good.get("priceElasticityPermille", 1000)
    condition = campaign or {}
    disruption = sum(int(condition.get(k, 0)) for k in ("blockadePermille", "warPermille", "occupationPermille", "eventPermille", "shortagePermille"))
    connectivity = int(condition.get("tradeConnectivityPermille", 1000))
    production = int(condition.get("productionPermille", 1000))
    consumption = int(condition.get("consumptionPermille", 1000))
    development = int(condition.get("technologyPermille", 0)) + int(condition.get("institutionPermille", 0))
    spread = rule.get("spreadPermille", 80)
    display_units = good["quantityUnitsPerDisplayUnit"]
    if elasticity < 0 or not 0 <= spread <= 1000 or display_units < 1:
        raise TradeError("invalid marginal pricing configuration")
    adjustment = disruption + (consumption - production) // 2 - (connectivity - 1000) // 3 - development

    def marginal(upper_stock: int) -> tuple[int, int]:
        scarcity = max(-750, min(2000, (target - upper_stock) * elasticity // target))
        pressure = max(rule.get("priceFloorPermille", 350), min(rule.get("priceCeilingPermille", 4000), 1000 + scarcity + adjustment))
        unit = max(1, (good["basePriceMinor"] * pressure + 500) // 1000)
        return max(1, unit * (1000 + spread if side == "buy" else 1000 - spread) // 1000), pressure

    low, high = (stock - quantity_units, stock) if side == "buy" else (stock, stock + quantity_units)
    cursor, numerator = low + 1, 0
    while cursor <= high:
        unit, _ = marginal(cursor)
        # Equal-price runs keep work bounded by the 2,751 scarcity bands, even
        # for enormous orders. Prices are monotone for nonnegative elasticity.
        left, right = cursor, high
        while left < right:
            middle = left + (right - left + 1) // 2
            if marginal(middle)[0] == unit:
                left = middle
            else:
                right = middle - 1
        numerator += unit * (left - cursor + 1)
        cursor = left + 1
    amount = ((numerator + display_units - 1) // display_units
              if side == "buy" else numerator // display_units)
    if amount < 1:
        raise TradeError("quantity is below the minimum currency settlement unit")
    # Informational average; amountMinor is the authoritative settlement.
    return {"unitPriceMinor": numerator // quantity_units, "amountMinor": amount, "stockUnits": stock, "targetStockUnits": target, "pressurePermille": marginal(low + (quantity_units + 1) // 2)[1]}


def inspect_market(catalog: Mapping[str, Any], economy_catalog: Mapping[str, Any], economy_state: Mapping[str, Any],
                   trade_state: Mapping[str, Any], market_id: str, player_id: str,
                   known_good_ids: set[str], campaign: Mapping[str, Any] | None = None) -> list[dict[str, Any]]:
    """Knowledge-filtered rows for UI; undiscovered goods and exact causes stay hidden."""
    goods, rules, _ = _indexes(catalog); rule = rules.get(market_id)
    if rule is None:
        raise TradeError("unknown market")
    history = trade_state.get("marketHistory", {}).get(market_id, {})
    player = trade_state.get("players", {}).get(player_id, {})
    rows = []
    for gid in rule["goodIds"]:
        if gid not in known_good_ids:
            continue
        current = quote(catalog, economy_catalog, economy_state, market_id, gid, "buy", 1, campaign)
        previous = history.get(gid, {}).get("unitPriceMinor", current["unitPriceMinor"])
        trend = "rising" if current["unitPriceMinor"] > previous else "falling" if current["unitPriceMinor"] < previous else "steady"
        held_lots = [x for x in player.get("lots", []) if x["goodId"] == gid]
        held, cost = sum(x["quantityUnits"] for x in held_lots), sum(x["costMinor"] for x in held_lots)
        projected = None
        if held:
            try:
                projected = quote(catalog, economy_catalog, economy_state, market_id, gid, "sell", held, campaign)["amountMinor"] - cost
            except TradeError:
                pass
        rows.append({"goodId": gid, "name": goods[gid].get("name", gid), "availableUnits": current["stockUnits"],
                     "buyUnitPriceMinor": current["unitPriceMinor"], "trend": trend,
                     "lastObservedUnitPriceMinor": previous, "heldUnits": held,
                     "knownCostMinor": cost if held else None, "projectedProfitLossMinor": projected})
    return rows


def execute(catalog: Mapping[str, Any], economy_catalog: Mapping[str, Any], economy_state: Mapping[str, Any],
            trade_state: Mapping[str, Any], action: Mapping[str, Any], campaign: Mapping[str, Any] | None = None) -> TradeResult:
    """Buy or sell cargo atomically, then update cost basis and merchant standing."""
    validate_state(trade_state); economy.validate_state(economy_catalog, economy_state)
    result = copy.deepcopy(dict(trade_state)); player_id = action["playerId"]
    market_id, good_id, side = action["marketId"], action["goodId"], action["side"]
    quantity = action["quantityUnits"]; transaction_id = action["id"]
    q = quote(catalog, economy_catalog, economy_state, market_id, good_id, side, quantity, campaign)
    _, rules, tiers = _indexes(catalog); rule = rules[market_id]
    market_store = next(x["storeId"] for x in economy_catalog["markets"] if x["id"] == market_id)
    cargo_store = action["storeId"]; currency_id = rule["currencyId"]
    # One economy transaction id is the anti-duplicate authority across save/load.
    if side == "buy":
        first = economy.apply_transfer(economy_catalog, economy_state, {"id": transaction_id + "_money", "assetKind": "currency", "assetId": currency_id, "amount": q["amountMinor"], "sourceStoreId": cargo_store, "destinationStoreId": market_store}).state
        committed = economy.apply_transfer(economy_catalog, first, {"id": transaction_id, "assetKind": "good", "assetId": good_id, "amount": quantity, "sourceStoreId": market_store, "destinationStoreId": cargo_store}).state
        realized = 0
    else:
        first = economy.apply_transfer(economy_catalog, economy_state, {"id": transaction_id + "_goods", "assetKind": "good", "assetId": good_id, "amount": quantity, "sourceStoreId": cargo_store, "destinationStoreId": market_store}).state
        committed = economy.apply_transfer(economy_catalog, first, {"id": transaction_id, "assetKind": "currency", "assetId": currency_id, "amount": q["amountMinor"], "sourceStoreId": market_store, "destinationStoreId": cargo_store}).state
        realized = 0
    player = _player(result, player_id); lots = player["lots"]
    if side == "buy":
        lots.append({"goodId": good_id, "storeId": cargo_store, "quantityUnits": quantity, "costMinor": q["amountMinor"], "originMarketId": market_id})
    else:
        remaining, cost = quantity, 0
        for lot in lots:
            if remaining and lot["goodId"] == good_id and lot["storeId"] == cargo_store:
                take = min(remaining, lot["quantityUnits"]); allocated = lot["costMinor"] * take // lot["quantityUnits"]
                lot["quantityUnits"] -= take; lot["costMinor"] -= allocated; remaining -= take; cost += allocated
        player["lots"] = [x for x in lots if x["quantityUnits"]]
        costed_quantity = quantity - remaining
        realized = q["amountMinor"] - cost
    player["lifetimeVolumeMinor"] += q["amountMinor"]
    player["realizedProfitMinor"] += realized
    award = 0
    if side == "sell" and realized > 0 and costed_quantity == quantity:
        origin = action.get("originMarketId", "unknown")
        route = f"{origin}>{market_id}>{good_id}"
        repetitions = player["routeHistory"].get(route, 0)
        difficulty = max(500, min(2500, int(action.get("routeDifficultyPermille", 1000))))
        diversity = min(500, len({x.split(">")[-1] for x in player["routeHistory"]}) * 50)
        award = max(1, realized * difficulty // 1000 * 1000 // (1000 + repetitions * 500) * (1000 + diversity) // 1000)
        player["routeHistory"][route] = repetitions + 1
        player["standing"] += award
    unlocked = [benefit for tier in tiers if player["standing"] >= tier["standingRequired"] for benefit in tier.get("benefitIds", [])]
    player["unlockedBenefitIds"] = list(dict.fromkeys(unlocked))
    observed = quote(catalog, economy_catalog, committed, market_id, good_id, "buy", 1, campaign)
    result["marketHistory"].setdefault(market_id, {})[good_id] = {"unitPriceMinor": observed["unitPriceMinor"], "tick": int((campaign or {}).get("currentTick", 0))}
    validate_state(result)
    return TradeResult(committed, result, q["amountMinor"], realized, award)


def transfer_cargo(economy_catalog: Mapping[str, Any], economy_state: Mapping[str, Any],
                   trade_state: Mapping[str, Any], player_id: str, transaction_id: str,
                   good_id: str, quantity_units: int, source_store_id: str,
                   destination_store_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
    """Move cargo and its FIFO cost basis across ship/fleet/warehouse stores."""
    validate_state(trade_state)
    moved = economy.apply_transfer(economy_catalog, economy_state, {
        "id": transaction_id, "assetKind": "good", "assetId": good_id,
        "amount": quantity_units, "sourceStoreId": source_store_id,
        "destinationStoreId": destination_store_id,
    }).state
    result = copy.deepcopy(dict(trade_state)); player = _player(result, player_id)
    remaining = quantity_units; additions = []
    for lot in player["lots"]:
        if remaining and lot["goodId"] == good_id and lot["storeId"] == source_store_id:
            take = min(remaining, lot["quantityUnits"]); allocated = lot["costMinor"] * take // lot["quantityUnits"]
            lot["quantityUnits"] -= take; lot["costMinor"] -= allocated; remaining -= take
            additions.append({**lot, "storeId": destination_store_id, "quantityUnits": take, "costMinor": allocated})
    player["lots"] = [x for x in player["lots"] if x["quantityUnits"]] + additions
    validate_state(result)
    return moved, result
