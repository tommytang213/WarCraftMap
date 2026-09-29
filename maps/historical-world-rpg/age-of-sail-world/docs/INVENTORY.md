# Inventory, equipment, and backpacks v1

## Authority and limits

`_shared/engine/inventory.py` is the authoritative reusable state/routing contract.
Warcraft handles are transient views and are never saved. The ordinary six unit
inventory slots remain the quick/outer inventory. Up to six separately equipped
backpack instances follow it in deterministic order; each has 1–30 unlocked slots
(180 total backpack slots). A backpack is not stored in an outer slot and no backpack
may be stored inside another backpack.

Item types provide a stable ID, generic category, per-type stack limit, and compatible
equipment slot types. Backpack types provide capacity, allowed categories, and generic
trait IDs. Scenario packs choose actual items, slots, progression tiers, and traits;
the shared engine contains no Age of Sail item names. Trade goods are stackable under
the same rules, although bulk cargo belongs in separate cargo systems.

An item grants gear bonuses only when its instance is present in `equipment`.
`equipment_bonus_item_ids` is the contract boundary for applying those bonuses. Items
in outer or backpack storage grant no equipment stats. Runtime adapters must suppress
ordinary passive bonuses while stored and reconcile from authoritative equip state.

## Equipment sets and threshold bonuses

- Equipment may belong to a scenario-defined set through stable set IDs; the shared inventory engine must not hardcode Age of Sail set names.
- Set bonuses are based only on qualifying pieces currently present in equipment slots. Matching pieces in outer inventory, backpacks, cargo, warehouses, or other storage do not count.
- Sets may define multiple piece-count thresholds rather than requiring the complete set. For example, a four-piece set may grant a small 2/4 bonus, a stronger 3/4 bonus, and a major 4/4 bonus.
- Thresholds and effects are data-driven per set. By default, reached threshold effects may coexist cumulatively (for example 4/4 can retain its 2/4 and 3/4 effects while adding the 4/4 effect); a set may explicitly define replacement/exclusive tiers where appropriate.
- Count distinct qualifying equipped set pieces by default. Equipping duplicate copies of the same named/set-piece identity must not multiply the piece count unless that set explicitly allows duplicates.
- Partial-set bonuses must be useful enough to support mixed equipment builds; completing a set is an additional reward, not the only point at which the set does anything.
- Set effects may grant stats, resistances, resource changes, ability/passive unlocks, conditional effects, or other character/equipment modifiers through the same derived-bonus layer as ordinary equipped-item bonuses.
- Set bonuses are derived from authoritative equipped-item state and should be recomputed on equip/unequip, load/migration, character reconstruction, and physical-map transition rather than persisted as an independent mutable bonus total.

## Pickup order and overflow

Routing is transactional and does not mutate its input:

1. Visit outer slots 1–6, then Backpack 1 through Backpack 6, each slot in array
   (top-left to bottom-right) order.
2. For a stackable type, top up compatible stacks to its `stackLimit`.
3. Put any remainder, or a non-stackable item, in the first eligible empty slot.
4. Return accepted and excess quantities. Excess remains the caller's world item (or
   is recreated at a safe pickup/drop point); it must never be silently removed.

Backpack category restrictions are eligibility rules, not another routing priority.

## Persistence and migration

Persist `ownerId`, `backpackUnlockTierId`, six outer slots, ordered active backpack records, and the equipment
slot map. Every item stack and backpack instance has an immutable stable `instanceId`;
types and slots use stable IDs. Quantity is authoritative. Handles, object rawcodes,
translated names, and UI page numbers are not persistence keys.

Validate after loading. `recover_over_capacity` accepts legacy/changed-capacity
storage, rebuilds current legal slots in canonical order, and returns every item or
removed backpack that cannot fit in `overflow`. The save layer must place overflow in
a durable recovery chest/mailbox before committing a migrated save and must preserve
the original save if recovery or validation fails.

## Warcraft III 3.0 compatibility findings

The project is pinned to Wurst `wc3Patch: v3.0`. The 3.0 `common.j` surface defines
`equipmentType`, `itemTag`, and `loadoutslot`, equip/unequip events, and these relevant
natives (latest 3.0 PTR notes also introduce `Blz`-prefixed forms and mark the
unprefixed forms for later removal):

- `GetEquippedItem`, `GetUnequippedItem`, `IsItemEquipped`, `IsItemInBag`
- `GetItemEquipmentType`, `GetItemTag`
- `UnitEquipItem`, `UnitUnequipItem`, `UnitUnequipItemFromSlot`
- `UnitExtendedInventorySize`, `UnitItemInBagSlot`, `UnitItemInEquipmentSlot`
- `UnitHasItemBagged`, `UnitHasItemEquipped`, `UnitHasLoadoutSlotEmpty`
- `UnitHasAnyItemEquiped` (native spelling), `UnitHasItemEquipmentOfType`, and
  `UnitCanEquipItemOfEquipmentType`

The native object abilities observed in 3.0 are `AIni` (Expanded Inventory, one
30-slot bag) and `AEqu` (Equipment Slots). Item object data exposes
`Stats - Equipment Type`; the loadout has Head, Chest, Gloves, Boots, two Ring
positions, Primary, Offhand, and Trinket. Current 3.0 behavior does not expose six
independent native expanded bags, configurable native bag capacity, or a reliable
general primitive for directing every normal item to an arbitrary bag slot. Thus the
one native bag is an optional visible page/cache. Backpacks 2–6 and paging are custom
UI/runtime projections of authoritative engine state.

Known 3.0 hazards are compatibility requirements, not engine semantics:

- Equipment slots depend on the expanded inventory framework in the current UI.
- Equipment-typed pickups route differently from ordinary items.
- A reported 3.0 bug lets an actively-usable equipment item apply its passive bonus
  while bagged and again when equipped. Do not use that object configuration; the
  adapter must reconcile bonuses from `equipment` only.
- Native bag contents on some non-hero death paths have been reported deleted.
  Authoritative state must own the records before removal/death and reconstruct views.

Sources checked:

- Blizzard 3.0 overview: https://news.blizzard.com/en-us/article/24298590/warcraft-iii-reforged-forsaken-kingdom-deep-dive-recap
- Blizzard 3.0 PTR native-list notes: https://us.forums.blizzard.com/en/warcraft3/t/new-300-ptr-build-24306/39295
- 3.0 object-editor/runtime investigation: https://www.hiveworkshop.com/threads/reforged-3-0-new-equipment-stats-and-talent-system.374193/

These findings stay behind the future WC3 compatibility module and must be rechecked when the pinned patch changes.
