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

## Player-facing item power, rarity, and identity

Player-use equipment and consumables are a separate content layer from bulk economic
cargo. A settlement may expose both a commodity market for trade and one or more
player-use merchants; one catalogue must not stand in for the other.

The release-facing equipment model keeps several dimensions separate:

- **Item level / power level** is the quick comparison number. The long-campaign target
  supports roughly level 1–300 equipment so item progression can remain readable beside
  level-300 heroes. Item level describes the item's overall stat/effect budget; it is
  not a rule that the larger number is always better for every build.
- **Rarity / quality** communicates craftsmanship, scarcity, affix/effect complexity,
  and ceiling. The scenario may use an ordered ladder such as Common, Fine, Superior,
  Rare, Epic, Legendary, and Relic/Artifact; exact labels remain data-driven.
- **Identity / provenance** is independent of rarity: generic, regional/cultural,
  polity-specific, profession/specialist, quest reward, equipment-set piece, unique
  historical item, legendary/relic, or other authored identities may coexist with
  any appropriate power level.
- **Enhancement / refinement** may provide bounded per-instance improvement where
  historically and mechanically appropriate, but cannot bypass era, technology, or
  equipment-category requirements.

Comparison UI should expose at minimum item level, rarity, enhancement, major stats,
abilities/passives/conditional effects, set membership and current set thresholds,
requirements, and green/red deltas against the currently equipped item. Specialized
effects must remain visible so a lower-level item can rationally outperform a higher-
level generic item for a particular build.

Historical and otherwise unique items are persistent singular identities unless the
scenario explicitly says otherwise. They may support bounded restoration/reforging or
other long-campaign improvement so an important item does not automatically become
vendor trash merely because the calendar advanced, but old gear must not be freely
upgraded into technology that does not yet exist.

The current generic inventory contract predates these release-scale fields. Phase 8
content work must extend the scenario/item schema rather than encoding rarity, item
level, provenance, or enhancement as ad-hoc display text.

## Player-use merchants and stores

Bulk goods stores/markets serve production, consumption, warehousing, cargo, price,
and trade-route simulation. Player-use merchants instead sell or service equipment,
consumables, tools, books/maps, mounts, artifacts, and ship-related supplies.

Useful merchant archetypes include general merchants, armourers/weaponsmiths,
gunsmiths, tailors/outfitters, apothecaries, booksellers/cartographers, horse/stable
dealers, specialist military suppliers, relic/artifact merchants, ship chandlers, and
dockyards. Their inventories are derived from settlement, region/culture, controlling
polity, campaign year, technology/institutions, local production, trade connectivity,
wealth, events/quests, and merchant type rather than using one global shop list.

Release-scale content targets roughly 300–500 ordinary player-usable equipment,
consumable, and tool types, 100+ unique/historical/legendary items, and about 50–80
authored equipment sets. These are planning ranges, not hard quotas; historical fit,
build diversity, and meaningful choice matter more than raw count.

## Equipment sets and threshold bonuses

- Equipment may belong to a scenario-defined set through stable set IDs; the shared inventory engine must not hardcode Age of Sail set names.
- Set bonuses are based only on qualifying pieces currently present in equipment slots. Matching pieces in outer inventory, backpacks, cargo, warehouses, or other storage do not count.
- Sets may define multiple piece-count thresholds rather than requiring the complete set. For example, a four-piece set may grant a small 2/4 bonus, a stronger 3/4 bonus, and a major 4/4 bonus.
- Thresholds and effects are data-driven per set. By default, reached threshold effects may coexist cumulatively (for example 4/4 can retain its 2/4 and 3/4 effects while adding the 4/4 effect); a set may explicitly define replacement/exclusive tiers where appropriate.
- Count distinct qualifying equipped set pieces by default. Equipping duplicate copies of the same named/set-piece identity must not multiply the piece count unless that set explicitly allows duplicates.
- Partial-set bonuses must be useful enough to support mixed equipment builds; completing a set is an additional reward, not the only point at which the set does anything.
- Set effects may grant stats, resistances, resource changes, ability/passive unlocks, conditional effects, or other character/equipment modifiers through the same derived-bonus layer as ordinary equipped-item bonuses.
- Set bonuses are derived from authoritative equipped-item state and should be recomputed on equip/unequip, load/migration, character reconstruction, and physical-map transition rather than persisted as an independent mutable bonus total.

The generic catalog expresses this with `derivedEffects`, `equipmentSetPieces`, and
`equipmentSets`. A piece maps one stable identity to one or more eligible item types
and may further restrict compatible slot types. Threshold policy defaults to
`cumulative`; an all-`exclusive` set selects only its highest reached tier, while a
`replacement` threshold explicitly names lower thresholds whose effects it replaces.
`resolve_equipment_bonuses` is the normalized runtime-adapter boundary: it returns
ordinary equipped instance IDs plus stable set/effect references and is safe to call
after every state transition or object reconstruction. Its result is never saved.

The live Wurst party inventory identifies an assignment by `(characterId, slotId)`.
Each assignment reserves one owned copy; replacement or removal releases that
reservation without changing owned quantities. Unique items can have only one
wearer. Comparisons, distinct equipped-piece counts, and cumulative set thresholds
use that character's loadout. `-inventory [HERO]` shows the selected wearer's
comparisons and set results (default: first recruited character); `-unequip HERO SLOT`
removes an assignment. Inactive wearers keep their authoritative equipment.

`WarcraftRpgProjections` applies item and set power only to the named wearer's live
representation. Reconciliation subtracts its previous contribution from that same
representation, preserving unrelated modifier layers. Replacement representations
start with a fresh contribution ledger. The ledger and set totals are derived and
never saved.

## Live equipment research eligibility

The generator retains every `technologyIds` and `institutionIds` entry in authored
order. Lists must contain unique stable research IDs, fit the 512-entry research
budget, and resolve to the matching kind in the scenario's research catalogue.
Colonial Printed Almanac requires the `movable_type_printing` institution; its
authoring script derives that classification from the research catalogue.

At `/equip HERO ITEM`, the production research resource boundary supplies the
current campaign year and controller identity (the existing single-player
identity is `player`). `PlayerInventory.available` checks every requirement
against exact controller completion IDs in `TechnologyRuntime`. Substrings,
another controller's completions, and the wrong research kind cannot qualify.
Level, date, recruitment, owned copies, unique ownership and wearer-specific
slots remain part of the same transaction. Rejection precedes any assignment or
projection write and returns the bounded English message
“Requirements are not met here.”

These are definition changes, not saved fields. Existing equipment and research
records remain authoritative on restoration, including loadouts earned under
the earlier incomplete gate. Loading or rebuilding representations does not
delete items, clear assignments or reapply new-action eligibility. Subsequent
equip commands use the current full requirements; unequipping still releases the
owned copy normally. Merchant availability and broader progression integration
remain separate incomplete portions of REQ-0076.01 and its dependencies.

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

The live Wurst RPG snapshot remains v3: its existing `e,slotId,itemId,characterId`
and `u,controllerId,researchId` records already store the necessary identities,
so equipment eligibility needs no format migration or reassignment. Supported v2
snapshots retain their existing main-character migration.
The loader validates duplicate character-slot pairs and per-item owned/equipped
copy counts across the whole candidate before changing authority. The v1 empty-RPG
migration and existing campaign envelope versions remain supported. Equipment uses
the existing 4,096 owned-copy budget, replacing the global 32-assignment limit;
the 32-hero local group can retain full loadouts. Stored items and other characters'
equipment never contribute to a wearer's set thresholds.

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
