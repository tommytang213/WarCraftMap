# Item definitions, comparisons and equipment delivery

Generator v28 emits every authored major-stat ID/value, effect ID and complete
conditional-effect descriptor into executable Wurst definitions. The 468-item
player-use catalogue retains item level, rarity ID/name/rank, provenance,
singular identity, category, slot metadata, requirements, improvement bounds and
set membership. Scenario JSON remains authoritative. Definitions that exceed
the runtime's 64 stats/effects/conditions per item fail generation; they are never
truncated. Major stats use signed integers within ±1,073,741,823, which also keeps
any comparison delta within the signed runtime integer range.

`PlayerInventory.compare()` follows `player_items.py::compare()` for individual
candidate values and deltas over the union of candidate/equipped stat IDs. An
absent stat is zero; replacing an item therefore shows lost stats as negative
deltas. `/inventory [HERO]` and its `/items` and `/equipment` aliases inspect that
wearer's equipped slot, showing item level, rarity, provenance, set membership,
requirements and colored per-stat deltas. Effects and conditional descriptions
remain visible with an explicit unavailable status. Existing set-tier inspection
and resolution are preserved.

`RpgProjectionPort.replaceEquipment(EquipmentItemLayer)` receives the stable
wearer ID, equipped slot and complete typed item definition. The projector owns
the layer and borrows the catalogue definition. A replacement or null-definition
removal affects only that wearer/slot. Reconciliation marks current layers and
retires unseen slots after visiting all assignments, including inactive heroes.
A content fingerprint includes every definition field and conditional descriptor;
unchanged deliveries reuse their layer, and changed definitions replace it. This
keeps authored metadata in the optimized executable as well as the source.
Definitions and layers do not require a Warcraft unit. Other wearers, slots, set
layers and unrelated native modifiers remain separate.

Item stats and effects have no gameplay consumer yet. Their status is
`blocked_pending_item_gameplay_bindings`; conditional activation is also unbound.
There is no universal conversion to maximum life: Afghan Pulwar retains
`meleePower=40` and `mountedPower=12` and grants no 52-life bonus. This work does
not select formulas for combat, command, economy, navigation or condition
evaluation. Those consumers remain downstream work, as do merchant-context
availability integrations. Existing equip eligibility checks for character,
date, every technology and every institution remain enforced.

No durable contract changed. RPG v7 continues to save owned copies and
`(wearer, slot, item ID)` assignments, never item stats, effects, computed deltas
or projected life. Supported v1–v6 migration reconstructs definitions by ID
without rechecking equip eligibility, minting replacement items or compensating
for the removed fallback. Campaign envelope migrations remain unchanged. Party
load transactions retain the prior item/set layers until commit; a rejected or
aborted load restores them alongside the prior authority and representations.

Validation covers all emitted definitions, negative controls for dropped stats,
effects and conditions, headless comparison vectors, registered production
commands, inactive/replaced representations, unrelated modifiers, unique/copy
conservation, all supported RPG loadouts and late campaign-load failure. The
pinned Wurst suite and compiled-definition inspection are developer-side checks.
They do not establish native Warcraft launch acceptance. The release blocker
`blocked_pending_real_forsaken_kingdom_launch_smoke` remains separate; no incremental
player QA is requested.
