import copy
import sys
import unittest
from pathlib import Path

CATEGORY_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(CATEGORY_ROOT / "_shared" / "engine"))
import inventory


def catalog():
    return {
        "schemaVersion": 1,
        "itemTypes": [
            {"id": "healing_draught", "category": "consumable", "stackable": True, "stackLimit": 10, "equipmentSlotTypes": []},
            {"id": "trade_bundle", "category": "trade_good", "stackable": True, "stackLimit": 20, "equipmentSlotTypes": []},
            {"id": "field_blade", "category": "equipment", "stackable": False, "stackLimit": 1, "equipmentSlotTypes": ["main_hand"]},
            {"id": "travel_pack", "category": "backpack", "stackable": False, "stackLimit": 1, "equipmentSlotTypes": []},
        ],
        "backpackTypes": [
            {"id": "general_pack", "capacity": 3, "allowedCategories": ["equipment", "consumable", "quest", "artifact", "tool", "book_map", "valuable", "trade_good", "miscellaneous"], "traitIds": ["weatherproof"]},
            {"id": "medicine_case", "capacity": 2, "allowedCategories": ["consumable"], "traitIds": []},
        ],
        "equipmentSlots": [{"id": "weapon_slot", "slotType": "main_hand"}],
        "backpackUnlockTiers": [
            {"id": "novice_carrying", "tier": 1, "activeBackpackSlots": 1, "maxUnlockedSlotsPerBackpack": 2},
            {"id": "master_carrying", "tier": 2, "activeBackpackSlots": 6, "maxUnlockedSlotsPerBackpack": 30},
        ],
    }


def empty_inventory(backpack_count=2):
    return {
        "ownerId": "player_character",
        "backpackUnlockTierId": "master_carrying",
        "outerSlots": [None] * 6,
        "activeBackpacks": [
            {"instanceId": f"pack_{index}", "backpackTypeId": "general_pack", "unlockedSlots": 3, "slots": [None] * 3}
            for index in range(1, backpack_count + 1)
        ],
        "equipment": {"weapon_slot": None},
    }


def stack(instance_id, item_type_id, quantity=1):
    return {"instanceId": instance_id, "itemTypeId": item_type_id, "quantity": quantity}


def set_catalog(policy="cumulative", allow_duplicates=False):
    data = catalog()
    data["equipmentSlots"] = [
        {"id": "weapon_slot", "slotType": "main_hand"},
        {"id": "head_slot", "slotType": "head"},
        {"id": "chest_slot", "slotType": "chest"},
        {"id": "ring_left", "slotType": "ring"},
        {"id": "ring_right", "slotType": "ring"},
    ]
    data["itemTypes"].extend([
        {"id": "test_helm", "category": "equipment", "stackable": False, "stackLimit": 1, "equipmentSlotTypes": ["head"]},
        {"id": "test_coat", "category": "equipment", "stackable": False, "stackLimit": 1, "equipmentSlotTypes": ["chest"]},
        {"id": "test_ring", "category": "equipment", "stackable": False, "stackLimit": 1, "equipmentSlotTypes": ["ring"]},
    ])
    data["derivedEffects"] = [
        {"id": "set_defence", "modifiers": {"stats": {"armor": 2}, "resistances": {"cold": 5}}},
        {"id": "set_resource", "modifiers": {"resources": {"resolve": 10}, "abilities": ["steady"]}},
        {"id": "set_passive", "modifiers": {"passives": ["guarded"], "conditionalEffects": ["low_health_guard"]}},
    ]
    data["equipmentSetPieces"] = [
        {"id": "helm_piece", "itemTypeIds": ["test_helm"], "equipmentSlotTypes": ["head"]},
        {"id": "coat_piece", "itemTypeIds": ["test_coat"]},
        {"id": "ring_piece", "itemTypeIds": ["test_ring"], "equipmentSlotTypes": ["ring"]},
    ]
    thresholds = [
        {"id": "two_piece", "pieceCount": 2, "effectIds": ["set_defence"], "tierPolicy": policy},
        {"id": "three_piece", "pieceCount": 3, "effectIds": ["set_resource"], "tierPolicy": policy},
    ]
    if policy == "replacement":
        thresholds[0]["tierPolicy"] = "cumulative"
        thresholds[1]["replacesThresholdIds"] = ["two_piece"]
    data["equipmentSets"] = [{"id": "test_set", "pieceIds": ["helm_piece", "coat_piece", "ring_piece"],
                               "allowDuplicatePieces": allow_duplicates, "thresholds": thresholds}]
    return data


def set_inventory():
    state = empty_inventory(1)
    state["equipment"] = {"weapon_slot": None, "head_slot": None, "chest_slot": None,
                            "ring_left": None, "ring_right": None}
    return state


class InventoryContractTests(unittest.TestCase):
    def test_valid_contract_supports_six_backpacks_and_180_maximum_slots(self):
        data = catalog()
        data["backpackTypes"][0]["capacity"] = 30
        state = empty_inventory(6)
        for backpack in state["activeBackpacks"]:
            backpack["unlockedSlots"] = 30
            backpack["slots"] = [None] * 30
        inventory.validate_inventory(data, state)
        self.assertEqual(180, sum(len(value["slots"]) for value in state["activeBackpacks"]))

    def test_unlock_tier_limits_active_backpacks_and_slots(self):
        state = empty_inventory(2)
        state["backpackUnlockTierId"] = "novice_carrying"
        with self.assertRaisesRegex(inventory.InventoryError, "unlock tier"):
            inventory.validate_inventory(catalog(), state)
        state = empty_inventory(1)
        state["backpackUnlockTierId"] = "novice_carrying"
        with self.assertRaisesRegex(inventory.InventoryError, "unlock tier"):
            inventory.validate_inventory(catalog(), state)

    def test_invalid_capacity_duplicate_ids_stack_limits_and_quantities_are_rejected(self):
        data = catalog()
        data["backpackTypes"][0]["capacity"] = 31
        with self.assertRaises(inventory.InventoryError):
            inventory.validate_catalog(data)
        data = catalog()
        data["itemTypes"].append(copy.deepcopy(data["itemTypes"][0]))
        with self.assertRaisesRegex(inventory.InventoryError, "duplicate ID"):
            inventory.validate_catalog(data)
        data = catalog()
        data["itemTypes"][0]["stackLimit"] = 1
        with self.assertRaisesRegex(inventory.InventoryError, "agree"):
            inventory.validate_catalog(data)
        state = empty_inventory()
        state["outerSlots"][0] = stack("bad_stack", "healing_draught", 11)
        with self.assertRaisesRegex(inventory.InventoryError, "exceeds stack limit"):
            inventory.validate_inventory(catalog(), state)

    def test_incompatible_slot_types_and_nested_backpacks_are_rejected(self):
        state = empty_inventory()
        state["equipment"]["weapon_slot"] = stack("wrong_item", "healing_draught")
        with self.assertRaisesRegex(inventory.InventoryError, "incompatible equipment"):
            inventory.validate_inventory(catalog(), state)
        state = empty_inventory()
        state["activeBackpacks"][0]["slots"][0] = stack("nested_pack", "travel_pack")
        with self.assertRaisesRegex(inventory.InventoryError, "activeBackpacks"):
            inventory.validate_inventory(catalog(), state)

    def test_pickup_tops_stacks_then_uses_first_empty_in_exact_search_order(self):
        state = empty_inventory()
        state["outerSlots"][0] = stack("outer_one", "healing_draught", 9)
        state["outerSlots"][1] = stack("outer_two", "healing_draught", 8)
        state["activeBackpacks"][0]["slots"][0] = stack("bag_one", "healing_draught", 7)
        result = inventory.pickup(catalog(), state, stack("incoming_stack", "healing_draught", 9))
        self.assertEqual([10, 10], [result.inventory["outerSlots"][0]["quantity"], result.inventory["outerSlots"][1]["quantity"]])
        self.assertEqual(10, result.inventory["activeBackpacks"][0]["slots"][0]["quantity"])
        self.assertEqual(3, result.inventory["outerSlots"][2]["quantity"])
        self.assertEqual((9, 0), (result.accepted_quantity, result.excess_quantity))
        self.assertEqual(7, state["activeBackpacks"][0]["slots"][0]["quantity"], "operation must not mutate source")

    def test_non_stackable_order_and_safe_overflow(self):
        state = empty_inventory(0)
        for index in range(5):
            state["outerSlots"][index] = stack(f"blade_{index}", "field_blade")
        first = inventory.pickup(catalog(), state, stack("last_blade", "field_blade"))
        self.assertEqual("last_blade", first.inventory["outerSlots"][5]["instanceId"])
        overflow = inventory.pickup(catalog(), first.inventory, stack("excess_blade", "field_blade"))
        self.assertEqual((0, 1), (overflow.accepted_quantity, overflow.excess_quantity))
        self.assertNotIn("excess_blade", str(overflow.inventory))

    def test_backpack_category_eligibility_is_respected(self):
        state = empty_inventory(0)
        state["outerSlots"] = [stack(f"blade_{index}", "field_blade") for index in range(6)]
        state["activeBackpacks"] = [{"instanceId": "medical_pack", "backpackTypeId": "medicine_case", "unlockedSlots": 2, "slots": [None, None]}]
        result = inventory.pickup(catalog(), state, stack("another_blade", "field_blade"))
        self.assertEqual(1, result.excess_quantity)

    def test_only_actively_equipped_gear_grants_bonuses(self):
        state = empty_inventory()
        state["outerSlots"][0] = stack("stored_blade", "field_blade")
        self.assertEqual((), inventory.equipment_bonus_item_ids(catalog(), state))
        state["outerSlots"][0] = None
        state["equipment"]["weapon_slot"] = stack("equipped_blade", "field_blade")
        self.assertEqual(("equipped_blade",), inventory.equipment_bonus_item_ids(catalog(), state))

    def test_recovery_preserves_canonical_order_and_returns_all_excess(self):
        state = empty_inventory(0)
        state["outerSlots"] = [stack(f"blade_{index}", "field_blade") for index in range(8)]
        recovered = inventory.recover_over_capacity(catalog(), state)
        self.assertEqual([f"blade_{index}" for index in range(6)], [value["instanceId"] for value in recovered.inventory["outerSlots"]])
        self.assertEqual(["blade_6", "blade_7"], [value["instanceId"] for value in recovered.overflow])

    def test_seventh_backpack_and_contents_are_recoverable_overflow(self):
        state = empty_inventory(7)
        state["activeBackpacks"][6]["slots"][0] = stack("seventh_item", "field_blade")
        recovered = inventory.recover_over_capacity(catalog(), state)
        self.assertEqual(6, len(recovered.inventory["activeBackpacks"]))
        self.assertIn("pack_7", [value["instanceId"] for value in recovered.overflow])
        self.assertIn("seventh_item", str(recovered.inventory) + str(recovered.overflow))

    def test_set_resolution_zero_partial_full_and_storage_exclusion(self):
        data, state = set_catalog(), set_inventory()
        state["outerSlots"][0] = stack("stored_helm", "test_helm")
        state["activeBackpacks"][0]["slots"][0] = stack("bagged_coat", "test_coat")
        self.assertEqual((), inventory.resolve_equipment_bonuses(data, state).set_bonuses)
        state["outerSlots"][0] = state["activeBackpacks"][0]["slots"][0] = None
        state["equipment"]["head_slot"] = stack("equipped_helm", "test_helm")
        state["equipment"]["chest_slot"] = stack("equipped_coat", "test_coat")
        partial = inventory.resolve_equipment_bonuses(data, state)
        self.assertEqual(("two_piece",), tuple(x.threshold_id for x in partial.set_bonuses))
        state["equipment"]["ring_left"] = stack("equipped_ring", "test_ring")
        full = inventory.resolve_equipment_bonuses(data, state)
        self.assertEqual(("two_piece", "three_piece"), tuple(x.threshold_id for x in full.set_bonuses))
        self.assertEqual(("set_defence", "set_resource"), full.effect_ids)

    def test_distinct_default_duplicate_opt_in_and_ordinary_bonus_preservation(self):
        state = set_inventory()
        state["equipment"]["ring_left"] = stack("first_ring", "test_ring")
        state["equipment"]["ring_right"] = stack("second_ring", "test_ring")
        default = inventory.resolve_equipment_bonuses(set_catalog(), state)
        self.assertEqual((), default.set_bonuses)
        allowed = inventory.resolve_equipment_bonuses(set_catalog(allow_duplicates=True), state)
        self.assertEqual(("two_piece",), tuple(x.threshold_id for x in allowed.set_bonuses))
        self.assertEqual(("first_ring", "second_ring"), allowed.item_instance_ids)

    def test_replacement_and_exclusive_tiers_select_normalized_effects(self):
        state = set_inventory()
        state["equipment"]["head_slot"] = stack("equipped_helm", "test_helm")
        state["equipment"]["chest_slot"] = stack("equipped_coat", "test_coat")
        state["equipment"]["ring_left"] = stack("equipped_ring", "test_ring")
        replaced = inventory.resolve_equipment_bonuses(set_catalog("replacement"), state)
        self.assertEqual(("three_piece",), tuple(x.threshold_id for x in replaced.set_bonuses))
        exclusive = inventory.resolve_equipment_bonuses(set_catalog("exclusive"), state)
        self.assertEqual(("three_piece",), tuple(x.threshold_id for x in exclusive.set_bonuses))

    def test_multiple_and_overlapping_sets_resolve_independently(self):
        data, state = set_catalog(), set_inventory()
        data["equipmentSets"].append({"id": "second_set", "pieceIds": ["helm_piece", "coat_piece"],
            "thresholds": [{"id": "second_partial", "pieceCount": 2, "effectIds": ["set_passive"]}]})
        state["equipment"]["head_slot"] = stack("equipped_helm", "test_helm")
        state["equipment"]["chest_slot"] = stack("equipped_coat", "test_coat")
        result = inventory.resolve_equipment_bonuses(data, state)
        self.assertEqual((("second_set", "second_partial"), ("test_set", "two_piece")),
                         tuple((x.set_id, x.threshold_id) for x in result.set_bonuses))

    def test_recompute_after_swap_transfer_and_reconstruction_is_deterministic(self):
        data, state = set_catalog(), set_inventory()
        state["equipment"]["head_slot"] = stack("equipped_helm", "test_helm")
        state["equipment"]["chest_slot"] = stack("equipped_coat", "test_coat")
        before = inventory.resolve_equipment_bonuses(data, state)
        restored = copy.deepcopy(state)  # save/load or physical-object reconstruction
        self.assertEqual(before, inventory.resolve_equipment_bonuses(data, restored))
        restored["outerSlots"][0] = restored["equipment"]["chest_slot"]
        restored["equipment"]["chest_slot"] = None
        self.assertEqual((), inventory.resolve_equipment_bonuses(data, restored).set_bonuses)
        self.assertNotIn("set_bonuses", str(restored).lower(), "derived totals must never enter persisted state")

    def test_over_capacity_recovery_preserves_equipped_set_authority(self):
        data, state = set_catalog(), set_inventory()
        state["equipment"]["head_slot"] = stack("equipped_helm", "test_helm")
        state["equipment"]["chest_slot"] = stack("equipped_coat", "test_coat")
        state["outerSlots"].extend(stack(f"overflow_item_{index}", "field_blade") for index in range(12))
        recovered = inventory.recover_over_capacity(data, state)
        self.assertEqual(("two_piece",), tuple(
            x.threshold_id for x in inventory.resolve_equipment_bonuses(data, recovered.inventory).set_bonuses))
        self.assertEqual(3, len(recovered.overflow))

    def test_failed_state_validation_does_not_mutate_catalog_or_inventory(self):
        data, state = set_catalog(), set_inventory()
        original_data, original_state = copy.deepcopy(data), copy.deepcopy(state)
        state["equipment"]["head_slot"] = stack("wrong_slot", "test_coat")
        invalid_state = copy.deepcopy(state)
        with self.assertRaisesRegex(inventory.InventoryError, "incompatible equipment"):
            inventory.resolve_equipment_bonuses(data, invalid_state)
        self.assertEqual(original_data, data)
        self.assertEqual(invalid_state, state)
        self.assertEqual(original_state["equipment"]["head_slot"], None)

    def test_malformed_set_catalogs_fail_atomically_with_stable_ids(self):
        mutations = []
        mutations.append(lambda d: d["equipmentSets"][0]["thresholds"].append(
            {"id": "duplicate_count", "pieceCount": 2, "effectIds": ["set_passive"]}))
        mutations.append(lambda d: d["equipmentSets"][0]["thresholds"][0].update(effectIds=["missing_effect"]))
        mutations.append(lambda d: d["equipmentSets"][0].update(pieceIds=["helm_piece", "helm_piece"]))
        mutations.append(lambda d: d["equipmentSetPieces"][0].update(itemTypeIds=["healing_draught"]))
        for mutate in mutations:
            data = set_catalog(); mutate(data)
            with self.assertRaises(inventory.InventoryError):
                inventory.validate_catalog(data)
        data = set_catalog("replacement")
        data["equipmentSets"][0]["thresholds"][0].update(tierPolicy="replacement", replacesThresholdIds=["three_piece"])
        with self.assertRaisesRegex(inventory.InventoryError, "replacement|cyclic"):
            inventory.validate_catalog(data)


if __name__ == "__main__":
    unittest.main()
