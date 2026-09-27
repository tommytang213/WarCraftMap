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


if __name__ == "__main__":
    unittest.main()
