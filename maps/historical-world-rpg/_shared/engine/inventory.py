"""Authoritative, scenario-independent personal inventory model.

Warcraft item handles are presentation objects.  This module operates only on
stable IDs and JSON-compatible values so the same rules can be used by runtime
adapters, validators, save migration, and headless tests.
"""

from __future__ import annotations

import copy
import re
from dataclasses import dataclass
from typing import Any, Mapping, Sequence


OUTER_SLOT_COUNT = 6
MAX_ACTIVE_BACKPACKS = 6
MAX_BACKPACK_CAPACITY = 30
MAX_BACKPACK_STORAGE = MAX_ACTIVE_BACKPACKS * MAX_BACKPACK_CAPACITY
ID_RE = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")


class InventoryError(ValueError):
    """A catalog, inventory state, or operation is invalid."""


@dataclass(frozen=True)
class PickupResult:
    inventory: dict[str, Any]
    accepted_quantity: int
    excess_quantity: int


@dataclass(frozen=True)
class RecoveryResult:
    inventory: dict[str, Any]
    overflow: tuple[dict[str, Any], ...]


@dataclass(frozen=True)
class ResolvedSetBonus:
    """One reached set threshold, expressed only as stable derived references."""

    set_id: str
    threshold_id: str
    equipped_piece_count: int
    effect_ids: tuple[str, ...]


@dataclass(frozen=True)
class EquipmentDerivedBonuses:
    """Complete reconstructible input to the shared derived-modifier adapter."""

    item_instance_ids: tuple[str, ...]
    set_bonuses: tuple[ResolvedSetBonus, ...]
    effect_ids: tuple[str, ...]


def _fail(message: str) -> None:
    raise InventoryError(message)


def _id(value: Any, context: str) -> str:
    if not isinstance(value, str) or not ID_RE.fullmatch(value):
        _fail(f"{context}: invalid stable ID {value!r}")
    return value


def _positive_int(value: Any, context: str, *, minimum: int = 1) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        _fail(f"{context}: must be an integer >= {minimum}")
    return value


def _index(records: Sequence[Mapping[str, Any]], domain: str) -> dict[str, Mapping[str, Any]]:
    if not isinstance(records, (list, tuple)):
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


def validate_catalog(catalog: Mapping[str, Any]) -> None:
    """Validate reusable item, backpack, equipment-slot, and unlock data."""
    if not isinstance(catalog, Mapping) or catalog.get("schemaVersion") != 1:
        _fail("inventory catalog schemaVersion must currently be 1")
    item_types = _index(catalog.get("itemTypes", []), "itemTypes")
    backpack_types = _index(catalog.get("backpackTypes", []), "backpackTypes")
    equipment_slots = _index(catalog.get("equipmentSlots", []), "equipmentSlots")
    unlock_tiers = _index(catalog.get("backpackUnlockTiers", []), "backpackUnlockTiers")
    effects = _index(catalog.get("derivedEffects", []), "derivedEffects")
    pieces = _index(catalog.get("equipmentSetPieces", []), "equipmentSetPieces")
    sets = _index(catalog.get("equipmentSets", []), "equipmentSets")
    if not unlock_tiers:
        _fail("backpackUnlockTiers: at least one tier is required")
    allowed_categories = {
        "equipment", "consumable", "quest", "artifact", "tool", "book_map",
        "valuable", "trade_good", "backpack", "miscellaneous",
    }
    equipment_slot_types = set()
    for slot_id, slot in equipment_slots.items():
        slot_type = _id(slot.get("slotType"), f"equipment slot {slot_id}.slotType")
        equipment_slot_types.add(slot_type)
    for item_id, item in item_types.items():
        category = item.get("category")
        if category not in allowed_categories:
            _fail(f"item type {item_id}: invalid category {category!r}")
        stack_limit = _positive_int(item.get("stackLimit"), f"item type {item_id}.stackLimit")
        stackable = item.get("stackable")
        if not isinstance(stackable, bool):
            _fail(f"item type {item_id}.stackable: must be boolean")
        if stackable != (stack_limit > 1):
            _fail(f"item type {item_id}: stackable must agree with stackLimit")
        equip_types = item.get("equipmentSlotTypes", [])
        if not isinstance(equip_types, list) or len(equip_types) != len(set(equip_types)):
            _fail(f"item type {item_id}.equipmentSlotTypes: must contain unique values")
        if category == "equipment" and not equip_types:
            _fail(f"item type {item_id}: equipment needs an equipment slot type")
        if category != "equipment" and equip_types:
            _fail(f"item type {item_id}: only equipment may name equipment slots")
        for slot_type in equip_types:
            if slot_type not in equipment_slot_types:
                _fail(f"item type {item_id}: unknown equipment slot type {slot_type!r}")
        if category == "trade_good" and not stackable:
            _fail(f"item type {item_id}: trade goods must be stackable")
    for effect_id, effect in effects.items():
        # Payloads are deliberately opaque to inventory.  The modifier adapter owns
        # their meaning, while this catalog owns reference integrity.
        if set(effect) - {"id", "modifiers"}:
            _fail(f"derived effect {effect_id}: unknown fields")
        if not isinstance(effect.get("modifiers"), Mapping) or not effect["modifiers"]:
            _fail(f"derived effect {effect_id}.modifiers: must be a non-empty object")
    item_piece_ids: dict[str, set[str]] = {item_id: set() for item_id in item_types}
    for piece_id, piece in pieces.items():
        item_ids = piece.get("itemTypeIds")
        if not isinstance(item_ids, list) or not item_ids or len(item_ids) != len(set(item_ids)):
            _fail(f"equipment set piece {piece_id}.itemTypeIds: must be a unique non-empty array")
        slot_types = piece.get("equipmentSlotTypes", [])
        if not isinstance(slot_types, list) or len(slot_types) != len(set(slot_types)):
            _fail(f"equipment set piece {piece_id}.equipmentSlotTypes: must contain unique values")
        for slot_type in slot_types:
            _id(slot_type, f"equipment set piece {piece_id}.equipmentSlotTypes")
            if slot_type not in equipment_slot_types:
                _fail(f"equipment set piece {piece_id}: unknown equipment slot type {slot_type!r}")
        for item_id in item_ids:
            if item_id not in item_types:
                _fail(f"equipment set piece {piece_id}: missing item type {item_id!r}")
            item = item_types[item_id]
            if item["category"] != "equipment":
                _fail(f"equipment set piece {piece_id}: item {item_id!r} is not equipment")
            compatible = set(item["equipmentSlotTypes"])
            if slot_types and not compatible.intersection(slot_types):
                _fail(f"equipment set piece {piece_id}: item {item_id!r} has incompatible slots")
            if piece_id in item_piece_ids[item_id]:
                _fail(f"equipment set piece {piece_id}: duplicate item {item_id!r}")
            item_piece_ids[item_id].add(piece_id)
    for set_id, definition in sets.items():
        piece_ids = definition.get("pieceIds")
        if not isinstance(piece_ids, list) or not piece_ids or len(piece_ids) != len(set(piece_ids)):
            _fail(f"equipment set {set_id}.pieceIds: must be a unique non-empty array")
        for piece_id in piece_ids:
            if piece_id not in pieces:
                _fail(f"equipment set {set_id}: missing piece {piece_id!r}")
        allow_duplicates = definition.get("allowDuplicatePieces", False)
        if not isinstance(allow_duplicates, bool):
            _fail(f"equipment set {set_id}.allowDuplicatePieces: must be boolean")
        thresholds = _index(definition.get("thresholds", []), f"equipment set {set_id}.thresholds")
        if not thresholds:
            _fail(f"equipment set {set_id}.thresholds: at least one threshold is required")
        counts = set()
        replacement_graph: dict[str, tuple[str, ...]] = {}
        for threshold_id, threshold in thresholds.items():
            count = _positive_int(threshold.get("pieceCount"), f"equipment set {set_id} threshold {threshold_id}.pieceCount")
            if count in counts:
                _fail(f"equipment set {set_id}: duplicate threshold piece count {count}")
            if not allow_duplicates and count > len(piece_ids):
                _fail(f"equipment set {set_id} threshold {threshold_id}: piece count exceeds distinct pieces")
            counts.add(count)
            effect_ids = threshold.get("effectIds")
            if not isinstance(effect_ids, list) or not effect_ids or len(effect_ids) != len(set(effect_ids)):
                _fail(f"equipment set {set_id} threshold {threshold_id}.effectIds: must be a unique non-empty array")
            for effect_id in effect_ids:
                if effect_id not in effects:
                    _fail(f"equipment set {set_id} threshold {threshold_id}: missing effect {effect_id!r}")
            policy = threshold.get("tierPolicy", "cumulative")
            if policy not in {"cumulative", "exclusive", "replacement"}:
                _fail(f"equipment set {set_id} threshold {threshold_id}: invalid tier policy {policy!r}")
            replaces = threshold.get("replacesThresholdIds", [])
            if not isinstance(replaces, list) or len(replaces) != len(set(replaces)):
                _fail(f"equipment set {set_id} threshold {threshold_id}.replacesThresholdIds: must be unique")
            if policy != "replacement" and replaces:
                _fail(f"equipment set {set_id} threshold {threshold_id}: only replacement tiers may replace thresholds")
            if policy == "replacement" and not replaces:
                _fail(f"equipment set {set_id} threshold {threshold_id}: replacement tier must name replaced thresholds")
            replacement_graph[threshold_id] = tuple(replaces)
        if any(t.get("tierPolicy", "cumulative") == "exclusive" for t in thresholds.values()) and any(
                t.get("tierPolicy", "cumulative") != "exclusive" for t in thresholds.values()):
            _fail(f"equipment set {set_id}: exclusive tiers cannot be mixed with other tier policies")
        for threshold_id, replaced_ids in replacement_graph.items():
            for replaced_id in replaced_ids:
                if replaced_id not in thresholds:
                    _fail(f"equipment set {set_id} threshold {threshold_id}: missing replacement target {replaced_id!r}")
        visiting, visited = set(), set()

        def visit(threshold_id: str) -> None:
            if threshold_id in visiting:
                _fail(f"equipment set {set_id}: cyclic replacement at threshold {threshold_id!r}")
            if threshold_id in visited:
                return
            visiting.add(threshold_id)
            for replaced_id in replacement_graph[threshold_id]:
                visit(replaced_id)
            visiting.remove(threshold_id); visited.add(threshold_id)
        for threshold_id in thresholds:
            visit(threshold_id)
        for threshold_id, replaced_ids in replacement_graph.items():
            for replaced_id in replaced_ids:
                if thresholds[replaced_id]["pieceCount"] >= thresholds[threshold_id]["pieceCount"]:
                    _fail(f"equipment set {set_id} threshold {threshold_id}: replacement target must be a lower threshold")
    for backpack_id, backpack in backpack_types.items():
        capacity = _positive_int(backpack.get("capacity"), f"backpack type {backpack_id}.capacity")
        if capacity > MAX_BACKPACK_CAPACITY:
            _fail(f"backpack type {backpack_id}: capacity exceeds {MAX_BACKPACK_CAPACITY}")
        categories = backpack.get("allowedCategories", [])
        if not isinstance(categories, list) or not categories or len(categories) != len(set(categories)):
            _fail(f"backpack type {backpack_id}.allowedCategories: must be a unique non-empty array")
        unknown = set(categories) - allowed_categories
        if unknown:
            _fail(f"backpack type {backpack_id}: invalid allowed categories {sorted(unknown)!r}")
        if "backpack" in categories:
            _fail(f"backpack type {backpack_id}: nested backpacks are not supported")
        traits = backpack.get("traitIds", [])
        if not isinstance(traits, list) or len(traits) != len(set(traits)):
            _fail(f"backpack type {backpack_id}.traitIds: must contain unique IDs")
        for trait in traits:
            _id(trait, f"backpack type {backpack_id}.traitIds")
    tier_numbers = set()
    previous_number, previous_active, previous_slots = 0, 0, 0
    for tier_id, tier in unlock_tiers.items():
        number = _positive_int(tier.get("tier"), f"unlock tier {tier_id}.tier")
        active = _positive_int(tier.get("activeBackpackSlots"), f"unlock tier {tier_id}.activeBackpackSlots", minimum=0)
        slots = _positive_int(tier.get("maxUnlockedSlotsPerBackpack"), f"unlock tier {tier_id}.maxUnlockedSlotsPerBackpack", minimum=0)
        if number in tier_numbers:
            _fail(f"backpackUnlockTiers: duplicate tier {number}")
        if active > MAX_ACTIVE_BACKPACKS or slots > MAX_BACKPACK_CAPACITY:
            _fail(f"unlock tier {tier_id}: exceeds v1 backpack limits")
        if number <= previous_number or active < previous_active or slots < previous_slots:
            _fail("backpackUnlockTiers: tiers must be ordered and non-decreasing")
        tier_numbers.add(number)
        previous_number, previous_active, previous_slots = number, active, slots


def _catalog_indexes(catalog: Mapping[str, Any]):
    validate_catalog(catalog)
    return (
        _index(catalog["itemTypes"], "itemTypes"),
        _index(catalog["backpackTypes"], "backpackTypes"),
        _index(catalog["equipmentSlots"], "equipmentSlots"),
    )


def _validate_stack(stack: Any, context: str, item_types: Mapping[str, Mapping[str, Any]]) -> None:
    if not isinstance(stack, Mapping):
        _fail(f"{context}: slot value must be an item stack or null")
    _id(stack.get("instanceId"), f"{context}.instanceId")
    item_id = stack.get("itemTypeId")
    if item_id not in item_types:
        _fail(f"{context}: unknown item type {item_id!r}")
    quantity = _positive_int(stack.get("quantity"), f"{context}.quantity")
    if quantity > item_types[item_id]["stackLimit"]:
        _fail(f"{context}: quantity {quantity} exceeds stack limit")


def validate_inventory(catalog: Mapping[str, Any], inventory: Mapping[str, Any]) -> None:
    """Validate authoritative owner state, including slot compatibility."""
    item_types, backpack_types, equipment_slots = _catalog_indexes(catalog)
    if not isinstance(inventory, Mapping):
        _fail("inventory must be an object")
    _id(inventory.get("ownerId"), "inventory.ownerId")
    unlock_tiers = _index(catalog["backpackUnlockTiers"], "backpackUnlockTiers")
    unlock_tier_id = inventory.get("backpackUnlockTierId")
    if unlock_tier_id not in unlock_tiers:
        _fail(f"inventory: unknown backpack unlock tier {unlock_tier_id!r}")
    unlock_tier = unlock_tiers[unlock_tier_id]
    outer = inventory.get("outerSlots")
    if not isinstance(outer, list) or len(outer) != OUTER_SLOT_COUNT:
        _fail(f"outerSlots must contain exactly {OUTER_SLOT_COUNT} slots")
    active = inventory.get("activeBackpacks")
    if not isinstance(active, list) or len(active) > min(MAX_ACTIVE_BACKPACKS, unlock_tier["activeBackpackSlots"]):
        _fail("activeBackpacks exceeds the current unlock tier")
    equipped = inventory.get("equipment")
    if not isinstance(equipped, Mapping) or set(equipped) != set(equipment_slots):
        _fail("equipment must contain exactly the catalog equipment slot IDs")
    seen_instances: set[str] = set()

    def check_stack(stack: Any, context: str, *, allowed_categories=None, equipment_type=None):
        if stack is None:
            return
        _validate_stack(stack, context, item_types)
        instance_id, item = stack["instanceId"], item_types[stack["itemTypeId"]]
        if instance_id in seen_instances:
            _fail(f"inventory: duplicate item instance ID {instance_id!r}")
        seen_instances.add(instance_id)
        if item["category"] == "backpack":
            _fail(f"{context}: backpacks must use activeBackpacks, not storage slots")
        if allowed_categories is not None and item["category"] not in allowed_categories:
            _fail(f"{context}: item category is incompatible with this backpack")
        if equipment_type is not None:
            if stack["quantity"] != 1 or equipment_type not in item.get("equipmentSlotTypes", []):
                _fail(f"{context}: incompatible equipment slot type")

    for index, stack in enumerate(outer):
        check_stack(stack, f"outerSlots[{index}]")
    seen_backpacks = set()
    for index, backpack in enumerate(active):
        context = f"activeBackpacks[{index}]"
        if not isinstance(backpack, Mapping):
            _fail(f"{context}: must be an object")
        instance_id = _id(backpack.get("instanceId"), f"{context}.instanceId")
        if instance_id in seen_instances or instance_id in seen_backpacks:
            _fail(f"inventory: duplicate item instance ID {instance_id!r}")
        seen_backpacks.add(instance_id)
        backpack_type = backpack_types.get(backpack.get("backpackTypeId"))
        if backpack_type is None:
            _fail(f"{context}: unknown backpack type {backpack.get('backpackTypeId')!r}")
        unlocked = _positive_int(backpack.get("unlockedSlots"), f"{context}.unlockedSlots")
        if unlocked > min(backpack_type["capacity"], unlock_tier["maxUnlockedSlotsPerBackpack"]):
            _fail(f"{context}: unlockedSlots exceeds backpack capacity or unlock tier")
        slots = backpack.get("slots")
        if not isinstance(slots, list) or len(slots) != unlocked:
            _fail(f"{context}.slots: must match unlockedSlots")
        for slot_index, stack in enumerate(slots):
            check_stack(stack, f"{context}.slots[{slot_index}]", allowed_categories=backpack_type["allowedCategories"])
    for slot_id, stack in equipped.items():
        check_stack(stack, f"equipment.{slot_id}", equipment_type=equipment_slots[slot_id]["slotType"])


def _storage_slots(catalog: Mapping[str, Any], inventory: dict[str, Any]):
    item_types = _index(catalog["itemTypes"], "itemTypes")
    backpack_types = _index(catalog["backpackTypes"], "backpackTypes")
    for index in range(OUTER_SLOT_COUNT):
        yield inventory["outerSlots"], index, None
    for backpack in inventory["activeBackpacks"]:
        allowed = backpack_types[backpack["backpackTypeId"]]["allowedCategories"]
        for index in range(len(backpack["slots"])):
            yield backpack["slots"], index, allowed


def _eligible(item: Mapping[str, Any], allowed_categories: Sequence[str] | None) -> bool:
    return item["category"] != "backpack" and (
        allowed_categories is None or item["category"] in allowed_categories
    )


def pickup(
    catalog: Mapping[str, Any], inventory: Mapping[str, Any], incoming: Mapping[str, Any],
    *, split_instance_ids: Sequence[str] = (),
) -> PickupResult:
    """Route a pickup in canonical order without mutating input or deleting excess."""
    validate_inventory(catalog, inventory)
    item_types = _index(catalog["itemTypes"], "itemTypes")
    _validate_stack(incoming, "incoming", item_types)
    item = item_types[incoming["itemTypeId"]]
    if item["category"] == "backpack":
        _fail("backpacks are equipped through the backpack operation, not pickup routing")
    result = copy.deepcopy(dict(inventory))
    original = incoming["quantity"]
    remaining = original
    slots = list(_storage_slots(catalog, result))
    if item["stackable"]:
        for container, index, allowed in slots:
            stack = container[index]
            if not _eligible(item, allowed) or stack is None or stack["itemTypeId"] != incoming["itemTypeId"]:
                continue
            moved = min(remaining, item["stackLimit"] - stack["quantity"])
            stack["quantity"] += moved
            remaining -= moved
            if remaining == 0:
                break
    ids = [incoming["instanceId"], *split_instance_ids]
    existing_ids = {
        stack["instanceId"] for container, index, _ in slots
        if (stack := container[index]) is not None
    } | {stack["instanceId"] for stack in result["equipment"].values() if stack is not None}
    used = 0
    for container, index, allowed in slots:
        if remaining == 0:
            break
        if container[index] is not None or not _eligible(item, allowed):
            continue
        if used >= len(ids):
            _fail("not enough split_instance_ids for the required new stacks")
        instance_id = _id(ids[used], "new stack instance ID")
        if instance_id in existing_ids or instance_id in ids[:used]:
            _fail(f"duplicate item instance ID {instance_id!r}")
        quantity = min(remaining, item["stackLimit"])
        container[index] = {"instanceId": instance_id, "itemTypeId": incoming["itemTypeId"], "quantity": quantity}
        used += 1
        remaining -= quantity
    validate_inventory(catalog, result)
    return PickupResult(result, original - remaining, remaining)


def equipment_bonus_item_ids(catalog: Mapping[str, Any], inventory: Mapping[str, Any]) -> tuple[str, ...]:
    """Return only actively equipped item instances that may grant gear bonuses."""
    validate_inventory(catalog, inventory)
    return tuple(
        inventory["equipment"][slot_id]["instanceId"]
        for slot_id in sorted(inventory["equipment"])
        if inventory["equipment"][slot_id] is not None
    )


def resolve_equipment_bonuses(catalog: Mapping[str, Any], inventory: Mapping[str, Any]) -> EquipmentDerivedBonuses:
    """Rebuild ordinary and set-derived bonuses from authoritative equip state.

    Nothing returned here is authoritative or suitable for persistence.  Calling it
    after load, ownership restoration, or Warcraft object reconstruction produces the
    same normalized result as calling it immediately after an equipment operation.
    """
    validate_inventory(catalog, inventory)
    pieces = _index(catalog.get("equipmentSetPieces", []), "equipmentSetPieces")
    sets = _index(catalog.get("equipmentSets", []), "equipmentSets")
    equipment_slots = _index(catalog["equipmentSlots"], "equipmentSlots")
    item_piece_ids: dict[str, list[str]] = {}
    for piece_id, piece in pieces.items():
        for item_id in piece["itemTypeIds"]:
            item_piece_ids.setdefault(item_id, []).append(piece_id)
    qualified: list[str] = []
    for slot_id in sorted(inventory["equipment"]):
        stack = inventory["equipment"][slot_id]
        if stack is None:
            continue
        slot_type = equipment_slots[slot_id]["slotType"]
        for piece_id in item_piece_ids.get(stack["itemTypeId"], ()):
            permitted = pieces[piece_id].get("equipmentSlotTypes", [])
            if not permitted or slot_type in permitted:
                qualified.append(piece_id)
    resolved: list[ResolvedSetBonus] = []
    for set_id in sorted(sets):
        definition = sets[set_id]
        allowed = set(definition["pieceIds"])
        matches = [piece_id for piece_id in qualified if piece_id in allowed]
        count = len(matches) if definition.get("allowDuplicatePieces", False) else len(set(matches))
        thresholds = _index(definition["thresholds"], f"equipment set {set_id}.thresholds")
        reached = {threshold_id for threshold_id, threshold in thresholds.items() if threshold["pieceCount"] <= count}
        if reached and all(thresholds[x].get("tierPolicy", "cumulative") == "exclusive" for x in thresholds):
            reached = {max(reached, key=lambda x: (thresholds[x]["pieceCount"], x))}
        replaced: set[str] = set()
        pending = [target for threshold_id in reached for target in thresholds[threshold_id].get("replacesThresholdIds", [])]
        while pending:
            target = pending.pop()
            if target in replaced:
                continue
            replaced.add(target); pending.extend(thresholds[target].get("replacesThresholdIds", []))
        for threshold_id in sorted(reached - replaced, key=lambda x: (thresholds[x]["pieceCount"], x)):
            resolved.append(ResolvedSetBonus(set_id, threshold_id, count, tuple(thresholds[threshold_id]["effectIds"])))
    effect_ids = tuple(effect_id for bonus in resolved for effect_id in bonus.effect_ids)
    return EquipmentDerivedBonuses(equipment_bonus_item_ids(catalog, inventory), tuple(resolved), effect_ids)


def recover_over_capacity(catalog: Mapping[str, Any], inventory: Mapping[str, Any]) -> RecoveryResult:
    """Recover old/invalid capacity by preserving canonical items or returning overflow.

    This deliberately accepts extra outer/backpack slots and excessive unlocked slot
    counts.  Valid destinations are rebuilt using current catalog limits.  Items that
    cannot fit are returned to the caller for a recovery chest/mailbox; none vanish.
    """
    item_types, backpack_types, equipment_slots = _catalog_indexes(catalog)
    source = copy.deepcopy(dict(inventory))
    _id(source.get("ownerId"), "inventory.ownerId")
    unlock_tiers = _index(catalog["backpackUnlockTiers"], "backpackUnlockTiers")
    unlock_tier_id = source.get("backpackUnlockTierId")
    if unlock_tier_id not in unlock_tiers:
        _fail(f"inventory: unknown backpack unlock tier {unlock_tier_id!r}")
    unlock_tier = unlock_tiers[unlock_tier_id]
    outer = source.get("outerSlots", [])
    active = source.get("activeBackpacks", [])
    if not isinstance(outer, list) or not isinstance(active, list):
        _fail("recovery source slots must be arrays")
    kept_backpacks = active[:min(MAX_ACTIVE_BACKPACKS, unlock_tier["activeBackpackSlots"])]
    recovered = {
        "ownerId": source["ownerId"],
        "backpackUnlockTierId": unlock_tier_id,
        "outerSlots": [None] * OUTER_SLOT_COUNT,
        "activeBackpacks": [],
        "equipment": copy.deepcopy(source.get("equipment", {slot_id: None for slot_id in equipment_slots})),
    }
    displaced: list[dict[str, Any]] = []
    overflow: list[dict[str, Any]] = []
    displaced.extend(stack for stack in outer if stack is not None)
    for backpack_index, backpack in enumerate(active):
        if not isinstance(backpack, Mapping):
            _fail("recovery backpack entry must be an object")
        backpack_type = backpack_types.get(backpack.get("backpackTypeId"))
        slots = backpack.get("slots", [])
        if backpack_index < len(kept_backpacks) and backpack_type is not None:
            unlocked = min(len(slots), backpack_type["capacity"], unlock_tier["maxUnlockedSlotsPerBackpack"], MAX_BACKPACK_CAPACITY)
            recovered["activeBackpacks"].append({
                "instanceId": backpack["instanceId"], "backpackTypeId": backpack["backpackTypeId"],
                "unlockedSlots": unlocked, "slots": [None] * unlocked,
            })
        else:
            overflow.append({"kind": "backpack", "instanceId": backpack.get("instanceId"), "backpackTypeId": backpack.get("backpackTypeId")})
        displaced.extend(stack for stack in slots if stack is not None)
    generated = 0
    for stack in displaced:
        _validate_stack(stack, "recovery item", item_types)
        if item_types[stack["itemTypeId"]]["category"] == "backpack":
            overflow.append(stack)
            continue
        while stack["quantity"] > 0:
            generated += 1
            candidate = copy.deepcopy(stack)
            candidate["instanceId"] = stack["instanceId"]
            candidate["quantity"] = stack["quantity"]
            try:
                routed = pickup(catalog, recovered, candidate, split_instance_ids=tuple(f"recovered_{generated}_{n}" for n in range(2, 32)))
            except InventoryError:
                overflow.append(copy.deepcopy(stack))
                break
            recovered = routed.inventory
            if routed.excess_quantity:
                excess = copy.deepcopy(stack)
                excess["quantity"] = routed.excess_quantity
                overflow.append(excess)
            break
    validate_inventory(catalog, recovered)
    return RecoveryResult(recovered, tuple(overflow))
