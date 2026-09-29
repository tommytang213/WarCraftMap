"""Deterministic, scenario-neutral economy contracts and transaction engine.

All quantities are integer ``quantityUnits`` and all money is integer currency
minor units.  Decimal display values never enter authoritative state.
"""

from __future__ import annotations

import copy
import re
from dataclasses import dataclass
from typing import Any, Mapping, Sequence


ID_RE = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")
STORE_KINDS = {"personal_inventory", "settlement", "warehouse", "ship", "fleet"}
OWNER_KINDS = {"character", "polity", "province", "settlement", "strategic_unit", "army", "fleet", "territorial_holding"}


class EconomyError(ValueError):
    """Raised before an invalid catalog, state, or atomic operation can commit."""


@dataclass(frozen=True)
class OperationResult:
    state: dict[str, Any]
    transaction_id: str


@dataclass(frozen=True)
class TickResult:
    """Result of advancing campaign time through every due economic event."""

    state: dict[str, Any]
    transaction_ids: tuple[str, ...]


def _fail(message: str) -> None:
    raise EconomyError(message)


def _id(value: Any, context: str) -> str:
    if not isinstance(value, str) or not ID_RE.fullmatch(value):
        _fail(f"{context}: invalid stable ID {value!r}")
    return value


def _integer(value: Any, context: str, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        _fail(f"{context}: must be an integer >= {minimum}")
    return value


def _index(records: Any, domain: str) -> dict[str, Mapping[str, Any]]:
    if not isinstance(records, list):
        _fail(f"{domain}: must be an array")
    result: dict[str, Mapping[str, Any]] = {}
    for record in records:
        if not isinstance(record, Mapping):
            _fail(f"{domain}: every entry must be an object")
        ident = _id(record.get("id"), f"{domain}.id")
        if ident in result:
            _fail(f"{domain}: duplicate ID {ident!r}")
        result[ident] = record
    return result


def _unique_ids(values: Any, context: str, targets: Mapping[str, Any], *, allow_empty: bool = True) -> tuple[str, ...]:
    if not isinstance(values, list) or (not allow_empty and not values):
        _fail(f"{context}: must be {'a non-empty' if not allow_empty else 'an'} array")
    result = []
    for value in values:
        ident = _id(value, context)
        if ident in result:
            _fail(f"{context}: duplicate reference {ident!r}")
        if ident not in targets:
            _fail(f"{context}: missing reference {ident!r}")
        result.append(ident)
    return tuple(result)


def _validate_owner(owner: Any, context: str, external_ids: Mapping[str, set[str]] | None) -> None:
    if not isinstance(owner, Mapping) or owner.get("kind") not in OWNER_KINDS:
        _fail(f"{context}: invalid owner reference")
    kind, ident = owner["kind"], _id(owner.get("id"), f"{context}.id")
    if external_ids is not None:
        available = external_ids.get(kind)
        if available is None or ident not in available:
            _fail(f"{context}: missing {kind} reference {ident!r}")


def _recipe_lines(lines: Any, context: str, goods: Mapping[str, Any], *, allow_empty: bool) -> dict[str, int]:
    if not isinstance(lines, list) or (not allow_empty and not lines):
        _fail(f"{context}: must be {'a non-empty' if not allow_empty else 'an'} array")
    result: dict[str, int] = {}
    for line in lines:
        if not isinstance(line, Mapping):
            _fail(f"{context}: every line must be an object")
        good_id = _id(line.get("goodId"), f"{context}.goodId")
        if good_id not in goods:
            _fail(f"{context}: missing good {good_id!r}")
        if good_id in result:
            _fail(f"{context}: duplicate good {good_id!r}")
        result[good_id] = _integer(line.get("quantityUnits"), f"{context} {good_id}.quantityUnits", 1)
    return result


def validate_catalog(catalog: Mapping[str, Any], external_ids: Mapping[str, set[str]] | None = None) -> None:
    """Validate static definitions; ``external_ids`` proves cross-domain stable IDs."""
    if not isinstance(catalog, Mapping) or catalog.get("schemaVersion") != 1:
        _fail("economy catalog schemaVersion must currently be 1")
    currencies = _index(catalog.get("currencies", []), "currencies")
    goods = _index(catalog.get("goods", []), "goods")
    stores = _index(catalog.get("stores", []), "stores")
    recipes = _index(catalog.get("recipes", []), "recipes")
    producers = _index(catalog.get("producers", []), "producers")
    consumers = _index(catalog.get("consumers", []), "consumers")
    markets = _index(catalog.get("markets", []), "markets")
    prices = _index(catalog.get("prices", []), "prices")
    obligations = _index(catalog.get("obligations", []), "obligations")
    source_rules = _index(catalog.get("sourceRules", []), "sourceRules")
    sink_rules = _index(catalog.get("sinkRules", []), "sinkRules")
    if not currencies or not goods:
        _fail("economy catalog requires at least one currency and good")

    for ident, currency in currencies.items():
        _integer(currency.get("minorUnitsPerMajor"), f"currency {ident}.minorUnitsPerMajor", 1)
    for ident, good in goods.items():
        _integer(good.get("quantityUnitsPerDisplayUnit"), f"good {ident}.quantityUnitsPerDisplayUnit", 1)
        if "itemTypeId" in good:
            _id(good["itemTypeId"], f"good {ident}.itemTypeId")

    for ident, store in stores.items():
        kind = store.get("kind")
        if kind not in STORE_KINDS:
            _fail(f"store {ident}: invalid kind {kind!r}")
        _validate_owner(store.get("owner"), f"store {ident}.owner", external_ids)
        capacity = _integer(store.get("capacityUnits"), f"store {ident}.capacityUnits", 0)
        allowed = _unique_ids(store.get("allowedGoodIds"), f"store {ident}.allowedGoodIds", goods, allow_empty=False)
        if capacity == 0:
            _fail(f"store {ident}: capacity must be positive")
        if kind == "personal_inventory" and any("itemTypeId" not in goods[g] for g in allowed):
            _fail(f"store {ident}: personal inventory goods require shared itemTypeId mappings")

    for ident, recipe in recipes.items():
        inputs = _recipe_lines(recipe.get("inputs"), f"recipe {ident}.inputs", goods, allow_empty=False)
        outputs = _recipe_lines(recipe.get("outputs"), f"recipe {ident}.outputs", goods, allow_empty=False)
        if inputs == outputs:
            _fail(f"recipe {ident}: inputs and outputs cannot be identical")

    for domain, actors in (("producer", producers), ("consumer", consumers)):
        for ident, actor in actors.items():
            store_id = actor.get("storeId")
            recipe_id = actor.get("recipeId")
            if store_id not in stores:
                _fail(f"{domain} {ident}: missing store {store_id!r}")
            if stores[store_id].get("kind") == "personal_inventory":
                _fail(f"{domain} {ident}: personal inventory cannot be a bulk recipe store")
            if recipe_id not in recipes:
                _fail(f"{domain} {ident}: missing recipe {recipe_id!r}")
            _validate_owner(actor.get("owner"), f"{domain} {ident}.owner", external_ids)

    for ident, market in markets.items():
        store_id = market.get("storeId")
        if store_id not in stores or stores[store_id].get("kind") == "personal_inventory":
            _fail(f"market {ident}: requires a bulk store")
        _validate_owner(market.get("owner"), f"market {ident}.owner", external_ids)
    for ident, price in prices.items():
        if price.get("marketId") not in markets or price.get("goodId") not in goods or price.get("currencyId") not in currencies:
            _fail(f"price {ident}: missing market, good, or currency reference")
        _integer(price.get("quantityUnits"), f"price {ident}.quantityUnits", 1)
        _integer(price.get("amountMinor"), f"price {ident}.amountMinor", 0)

    for ident, obligation in obligations.items():
        if obligation.get("currencyId") not in currencies:
            _fail(f"obligation {ident}: missing currency reference")
        if obligation.get("payerStoreId") not in stores:
            _fail(f"obligation {ident}: missing payer store")
        destination = obligation.get("payeeStoreId")
        sink = obligation.get("sinkRuleId")
        if (destination is None) == (sink is None):
            _fail(f"obligation {ident}: exactly one payeeStoreId or sinkRuleId is required")
        if destination is not None and destination not in stores:
            _fail(f"obligation {ident}: missing payee store {destination!r}")
        if sink is not None and sink not in sink_rules:
            _fail(f"obligation {ident}: missing sink rule {sink!r}")
        _integer(obligation.get("amountMinor"), f"obligation {ident}.amountMinor", 1)
        _integer(obligation.get("intervalTicks"), f"obligation {ident}.intervalTicks", 1)

    for domain, rules in (("source rule", source_rules), ("sink rule", sink_rules)):
        for ident, rule in rules.items():
            asset_kind = rule.get("assetKind")
            targets = currencies if asset_kind == "currency" else goods if asset_kind == "good" else None
            if targets is None:
                _fail(f"{domain} {ident}: invalid assetKind")
            _unique_ids(rule.get("assetIds"), f"{domain} {ident}.assetIds", targets, allow_empty=False)
            kinds = rule.get("storeKinds")
            if not isinstance(kinds, list) or not kinds or len(kinds) != len(set(kinds)) or set(kinds) - STORE_KINDS:
                _fail(f"{domain} {ident}.storeKinds: invalid or duplicate store kind")


def _catalog_indexes(catalog: Mapping[str, Any]) -> dict[str, dict[str, Mapping[str, Any]]]:
    return {name: _index(catalog.get(name, []), name) for name in (
        "currencies", "goods", "stores", "recipes", "producers", "consumers",
        "markets", "prices", "obligations", "sourceRules", "sinkRules")}


def validate_state(catalog: Mapping[str, Any], state: Mapping[str, Any]) -> None:
    """Validate authoritative balances, capacity, references, and transaction IDs."""
    validate_catalog(catalog)
    if not isinstance(state, Mapping) or state.get("schemaVersion") != 1:
        _fail("economy state schemaVersion must currently be 1")
    indexes = _catalog_indexes(catalog)
    balances = _index(state.get("storeBalances", []), "storeBalances")
    if set(balances) != set(indexes["stores"]):
        missing, extra = set(indexes["stores"]) - set(balances), set(balances) - set(indexes["stores"])
        _fail(f"storeBalances: must cover stores exactly (missing={sorted(missing)!r}, extra={sorted(extra)!r})")
    for store_id, balance in balances.items():
        if balance.get("storeId") != store_id:
            _fail(f"store balance {store_id}: id and storeId must match")
        store = indexes["stores"][store_id]
        goods = _recipe_lines(balance.get("goods"), f"store balance {store_id}.goods", indexes["goods"], allow_empty=True)
        currencies = _recipe_lines(
            [{"goodId": x.get("currencyId"), "quantityUnits": x.get("amountMinor")} for x in balance.get("currencies", [])]
            if isinstance(balance.get("currencies"), list) else balance.get("currencies"),
            f"store balance {store_id}.currencies", indexes["currencies"], allow_empty=True,
        )
        unknown = set(goods) - set(store.get("allowedGoodIds", []))
        if unknown:
            _fail(f"store balance {store_id}: incompatible goods {sorted(unknown)!r}")
        if sum(goods.values()) > store["capacityUnits"]:
            _fail(f"store balance {store_id}: goods exceed capacity")
        for value in currencies.values():
            _integer(value, f"store balance {store_id}.amountMinor", 0)
    processed = state.get("processedTransactionIds")
    if not isinstance(processed, list) or len(processed) != len(set(processed)):
        _fail("processedTransactionIds: must be a unique array")
    for ident in processed:
        _id(ident, "processedTransactionIds")


    current_tick = _integer(state.get("currentTick", 0), "currentTick", 0)
    pending = state.get("pendingObligations", [])
    if not isinstance(pending, list):
        _fail("pendingObligations: must be an array")
    seen: set[str] = set()
    for entry in pending:
        if not isinstance(entry, Mapping):
            _fail("pendingObligations: every entry must be an object")
        obligation_id = entry.get("obligationId")
        if obligation_id not in indexes["obligations"] or obligation_id in seen:
            _fail(f"pendingObligations: invalid or duplicate obligation {obligation_id!r}")
        seen.add(obligation_id)
        next_tick = _integer(entry.get("nextDueTick"), f"pending obligation {obligation_id}.nextDueTick", 1)
        _integer(entry.get("occurrencesSettled"), f"pending obligation {obligation_id}.occurrencesSettled", 0)
        if next_tick <= current_tick:
            _fail(f"pending obligation {obligation_id}: due tick was not processed")
    if pending and seen != set(indexes["obligations"]):
        _fail("pendingObligations: must cover all obligations when scheduling is enabled")


def _mutable_balances(state: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {record["storeId"]: record for record in state["storeBalances"]}


def _asset_lines(balance: dict[str, Any], asset_kind: str) -> tuple[list[dict[str, Any]], str, str]:
    return (balance["goods"], "goodId", "quantityUnits") if asset_kind == "good" else (balance["currencies"], "currencyId", "amountMinor")


def _amount(balance: dict[str, Any], asset_kind: str, asset_id: str) -> int:
    lines, key, amount_key = _asset_lines(balance, asset_kind)
    return next((line[amount_key] for line in lines if line[key] == asset_id), 0)


def _change(balance: dict[str, Any], asset_kind: str, asset_id: str, delta: int) -> None:
    lines, key, amount_key = _asset_lines(balance, asset_kind)
    for line in lines:
        if line[key] == asset_id:
            line[amount_key] += delta
            if line[amount_key] == 0:
                lines.remove(line)
            return
    if delta:
        lines.append({key: asset_id, amount_key: delta})
        lines.sort(key=lambda line: line[key])


def _start(catalog: Mapping[str, Any], state: Mapping[str, Any], transaction_id: Any) -> tuple[dict[str, Any], dict[str, Any], str]:
    validate_state(catalog, state)
    ident = _id(transaction_id, "transaction.id")
    if ident in state["processedTransactionIds"]:
        _fail(f"transaction {ident}: already processed")
    result = copy.deepcopy(state)
    return result, _mutable_balances(result), ident


def _finish(catalog: Mapping[str, Any], result: dict[str, Any], ident: str) -> OperationResult:
    result["processedTransactionIds"].append(ident)
    validate_state(catalog, result)
    return OperationResult(result, ident)


def apply_transfer(catalog: Mapping[str, Any], state: Mapping[str, Any], transfer: Mapping[str, Any]) -> OperationResult:
    """Atomically move an exact good or currency amount without creation/destruction."""
    result, balances, ident = _start(catalog, state, transfer.get("id"))
    indexes = _catalog_indexes(catalog)
    kind = transfer.get("assetKind")
    asset_id = transfer.get("assetId")
    amount = _integer(transfer.get("amount"), f"transfer {ident}.amount", 1)
    targets = indexes["goods"] if kind == "good" else indexes["currencies"] if kind == "currency" else {}
    if asset_id not in targets:
        _fail(f"transfer {ident}: missing {kind!r} asset {asset_id!r}")
    source, destination = transfer.get("sourceStoreId"), transfer.get("destinationStoreId")
    if source not in balances or destination not in balances or source == destination:
        _fail(f"transfer {ident}: invalid source or destination store")
    if _amount(balances[source], kind, asset_id) < amount:
        _fail(f"transfer {ident}: insufficient balance")
    if kind == "good":
        destination_store = indexes["stores"][destination]
        if asset_id not in destination_store["allowedGoodIds"]:
            _fail(f"transfer {ident}: destination is incompatible with good {asset_id!r}")
        used = sum(x["quantityUnits"] for x in balances[destination]["goods"])
        if used + amount > destination_store["capacityUnits"]:
            _fail(f"transfer {ident}: insufficient destination capacity")
    before = sum(_amount(b, kind, asset_id) for b in balances.values())
    _change(balances[source], kind, asset_id, -amount)
    _change(balances[destination], kind, asset_id, amount)
    after = sum(_amount(b, kind, asset_id) for b in balances.values())
    if before != after:
        _fail(f"transfer {ident}: conservation failure")
    return _finish(catalog, result, ident)


def execute_recipe(catalog: Mapping[str, Any], state: Mapping[str, Any], operation: Mapping[str, Any]) -> OperationResult:
    """Apply one declared recipe; no undeclared transformation is permitted."""
    result, balances, ident = _start(catalog, state, operation.get("id"))
    indexes = _catalog_indexes(catalog)
    actor_kind = operation.get("actorKind")
    actors = indexes["producers"] if actor_kind == "producer" else indexes["consumers"] if actor_kind == "consumer" else {}
    actor = actors.get(operation.get("actorId"))
    if actor is None:
        _fail(f"recipe operation {ident}: missing {actor_kind!r} actor")
    recipe = indexes["recipes"][actor["recipeId"]]
    store_id, batches = actor["storeId"], _integer(operation.get("batches"), f"recipe operation {ident}.batches", 1)
    inputs = _recipe_lines(recipe["inputs"], f"recipe {recipe['id']}.inputs", indexes["goods"], allow_empty=False)
    outputs = _recipe_lines(recipe["outputs"], f"recipe {recipe['id']}.outputs", indexes["goods"], allow_empty=False)
    for good_id, quantity in inputs.items():
        if _amount(balances[store_id], "good", good_id) < quantity * batches:
            _fail(f"recipe operation {ident}: insufficient {good_id!r}")
    final = {g: _amount(balances[store_id], "good", g) - inputs.get(g, 0) * batches + outputs.get(g, 0) * batches for g in set(inputs) | set(outputs)}
    if any(value < 0 for value in final.values()):
        _fail(f"recipe operation {ident}: would overdraw goods")
    total = sum(x["quantityUnits"] for x in balances[store_id]["goods"])
    total += (sum(outputs.values()) - sum(inputs.values())) * batches
    store = indexes["stores"][store_id]
    if total > store["capacityUnits"]:
        _fail(f"recipe operation {ident}: insufficient capacity")
    if set(outputs) - set(store["allowedGoodIds"]):
        _fail(f"recipe operation {ident}: output is incompatible with store")
    for good_id, quantity in inputs.items():
        _change(balances[store_id], "good", good_id, -quantity * batches)
    for good_id, quantity in outputs.items():
        _change(balances[store_id], "good", good_id, quantity * batches)
    return _finish(catalog, result, ident)


def apply_authorized_adjustment(catalog: Mapping[str, Any], state: Mapping[str, Any], adjustment: Mapping[str, Any]) -> OperationResult:
    """Create or destroy assets only through an explicit matching source/sink rule."""
    result, balances, ident = _start(catalog, state, adjustment.get("id"))
    indexes = _catalog_indexes(catalog)
    direction = adjustment.get("direction")
    rules = indexes["sourceRules"] if direction == "source" else indexes["sinkRules"] if direction == "sink" else {}
    rule = rules.get(adjustment.get("ruleId"))
    if rule is None:
        _fail(f"adjustment {ident}: missing authorized {direction!r} rule")
    store_id, kind, asset_id = adjustment.get("storeId"), adjustment.get("assetKind"), adjustment.get("assetId")
    amount = _integer(adjustment.get("amount"), f"adjustment {ident}.amount", 1)
    if store_id not in balances or kind != rule["assetKind"] or asset_id not in rule["assetIds"]:
        _fail(f"adjustment {ident}: asset or store reference does not match rule")
    store = indexes["stores"][store_id]
    if store["kind"] not in rule["storeKinds"]:
        _fail(f"adjustment {ident}: store kind is not authorized")
    if direction == "sink" and _amount(balances[store_id], kind, asset_id) < amount:
        _fail(f"adjustment {ident}: insufficient balance")
    if direction == "source" and kind == "good":
        used = sum(x["quantityUnits"] for x in balances[store_id]["goods"])
        if asset_id not in store["allowedGoodIds"] or used + amount > store["capacityUnits"]:
            _fail(f"adjustment {ident}: incompatible good or insufficient capacity")
    _change(balances[store_id], kind, asset_id, amount if direction == "source" else -amount)
    return _finish(catalog, result, ident)


def settle_obligation(catalog: Mapping[str, Any], state: Mapping[str, Any], obligation_id: str, transaction_id: str) -> OperationResult:
    """Settle one fixed recurring tax/upkeep amount as a transfer or authorized sink."""

    validate_catalog(catalog)
    obligation = _catalog_indexes(catalog)["obligations"].get(obligation_id)
    if obligation is None:
        _fail(f"missing obligation {obligation_id!r}")
    common = {"id": transaction_id, "assetKind": "currency", "assetId": obligation["currencyId"], "amount": obligation["amountMinor"]}
    if "payeeStoreId" in obligation:
        return apply_transfer(catalog, state, {**common, "sourceStoreId": obligation["payerStoreId"], "destinationStoreId": obligation["payeeStoreId"]})
    return apply_authorized_adjustment(catalog, state, {**common, "direction": "sink", "ruleId": obligation["sinkRuleId"], "storeId": obligation["payerStoreId"]})

def execute_trade(catalog: Mapping[str, Any], state: Mapping[str, Any], trade: Mapping[str, Any]) -> OperationResult:
    """Atomically exchange a market-priced good and currency between two stores."""
    result, balances, ident = _start(catalog, state, trade.get("id"))
    indexes = _catalog_indexes(catalog)
    price = indexes["prices"].get(trade.get("priceId"))
    if price is None:
        _fail(f"trade {ident}: missing price reference")
    buyer = trade.get("buyerStoreId")
    market_store = indexes["markets"][price["marketId"]]["storeId"]
    if buyer not in balances or buyer == market_store:
        _fail(f"trade {ident}: invalid buyer store")
    quantity = _integer(trade.get("quantityUnits"), f"trade {ident}.quantityUnits", 1)
    charge = quote_amount_minor(price, quantity)
    good_id, currency_id = price["goodId"], price["currencyId"]
    buyer_store = indexes["stores"][buyer]
    if good_id not in buyer_store["allowedGoodIds"]:
        _fail(f"trade {ident}: buyer store is incompatible with good {good_id!r}")
    if _amount(balances[market_store], "good", good_id) < quantity:
        _fail(f"trade {ident}: market has insufficient goods")
    if _amount(balances[buyer], "currency", currency_id) < charge:
        _fail(f"trade {ident}: buyer has insufficient funds")
    used = sum(line["quantityUnits"] for line in balances[buyer]["goods"])
    if used + quantity > buyer_store["capacityUnits"]:
        _fail(f"trade {ident}: buyer has insufficient capacity")
    _change(balances[market_store], "good", good_id, -quantity)
    _change(balances[buyer], "good", good_id, quantity)
    if charge:
        _change(balances[buyer], "currency", currency_id, -charge)
        _change(balances[market_store], "currency", currency_id, charge)
    return _finish(catalog, result, ident)


def transfer_personal_inventory(catalog: Mapping[str, Any], state: Mapping[str, Any], transfer: Mapping[str, Any]) -> OperationResult:
    """Cross the personal/bulk boundary using the good's typed item mapping."""
    indexes = _catalog_indexes(catalog)
    source, destination = transfer.get("sourceStoreId"), transfer.get("destinationStoreId")
    if source not in indexes["stores"] or destination not in indexes["stores"]:
        _fail("personal inventory transfer: invalid store reference")
    personal = indexes["stores"][source]["kind"] == "personal_inventory", indexes["stores"][destination]["kind"] == "personal_inventory"
    if personal[0] == personal[1]:
        _fail("personal inventory transfer: exactly one store must be personal inventory")
    good = indexes["goods"].get(transfer.get("goodId"))
    if good is None or good.get("itemTypeId") != transfer.get("itemTypeId"):
        _fail("personal inventory transfer: itemTypeId does not match the scenario good mapping")
    return apply_transfer(catalog, state, {"id": transfer.get("id"), "assetKind": "good", "assetId": transfer.get("goodId"), "amount": transfer.get("quantityUnits"), "sourceStoreId": source, "destinationStoreId": destination})


def initialize_scheduling(catalog: Mapping[str, Any], state: Mapping[str, Any], current_tick: int = 0) -> dict[str, Any]:
    """Add persistent recurring-obligation cursors to existing authoritative state."""
    validate_state(catalog, state)
    tick = _integer(current_tick, "currentTick", 0)
    result = copy.deepcopy(dict(state)); result["currentTick"] = tick
    result["pendingObligations"] = [{"obligationId": ident, "nextDueTick": tick + rule["intervalTicks"], "occurrencesSettled": 0} for ident, rule in sorted(_catalog_indexes(catalog)["obligations"].items())]
    return result


def process_economy_until(catalog: Mapping[str, Any], state: Mapping[str, Any], target_tick: int) -> TickResult:
    """Atomically settle every obligation due through a campaign-time tick."""
    validate_state(catalog, state)
    target = _integer(target_tick, "targetTick", 0)
    current_tick, pending = state.get("currentTick"), state.get("pendingObligations")
    if current_tick is None or not isinstance(pending, list):
        _fail("economy state scheduling is not initialized")
    if target < current_tick:
        _fail("targetTick cannot precede currentTick")
    result = copy.deepcopy(dict(state)); completed: list[str] = []
    obligations = _catalog_indexes(catalog)["obligations"]
    cursors = {entry["obligationId"]: entry for entry in result["pendingObligations"]}
    if set(cursors) != set(obligations):
        _fail("pendingObligations must cover every obligation")
    while True:
        due = sorted((entry["nextDueTick"], obligation_id) for obligation_id, entry in cursors.items() if entry["nextDueTick"] <= target)
        if not due:
            break
        due_tick, obligation_id = due[0]
        cursor = cursors[obligation_id]; occurrence = cursor["occurrencesSettled"] + 1
        transaction_id = f"obligation_{obligation_id}_{occurrence}"
        result = settle_obligation(catalog, result, obligation_id, transaction_id).state
        cursor = next(entry for entry in result["pendingObligations"] if entry["obligationId"] == obligation_id)
        cursors[obligation_id] = cursor
        cursor["occurrencesSettled"] = occurrence
        cursor["nextDueTick"] = due_tick + obligations[obligation_id]["intervalTicks"]
        completed.append(transaction_id)
    result["currentTick"] = target
    validate_state(catalog, result)
    return TickResult(result, tuple(completed))


def extension_snapshot(catalog: Mapping[str, Any], state: Mapping[str, Any]) -> dict[str, Any]:
    """Stable-ID state boundary for later taxation, diplomacy, warfare, and AI."""
    validate_state(catalog, state)
    return copy.deepcopy({"currentTick": state.get("currentTick", 0), "storeBalances": state["storeBalances"], "pendingObligations": state.get("pendingObligations", [])})


def quote_amount_minor(price: Mapping[str, Any], quantity_units: int) -> int:
    """Round half up using integers; avoids binary floating-point drift."""
    quantity = _integer(quantity_units, "quantityUnits", 0)
    basis = _integer(price.get("quantityUnits"), "price.quantityUnits", 1)
    amount = _integer(price.get("amountMinor"), "price.amountMinor", 0)
    numerator = quantity * amount
    return (numerator + basis // 2) // basis
