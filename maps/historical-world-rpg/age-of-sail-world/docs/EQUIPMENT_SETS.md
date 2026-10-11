# Equipment set definitions and resolution

The player-use catalogue is authoritative. Generation retains every set, piece,
threshold and effect reference. Existing `itemTypeIds` members become distinct
pieces identified by their item IDs. Thresholds without an authored `id` use
`pieces_COUNT`; explicit IDs are preserved. Neither normalization changes saves.
Definitions are ordered by set ID, piece ID and threshold piece count. Effects
retain authored order. Invalid references, duplicate identities/counts, invalid
policies, replacement cycles and definitions exceeding runtime budgets reject
generation instead of truncating data.

The shared Wurst resolver follows `_shared/engine/inventory.py` for each wearer.
Only equipped, slot-qualified pieces count. Copies and alternative items for one
piece count once unless `allowDuplicatePieces` is explicitly enabled. Cumulative
tiers retain every reached threshold; wholly exclusive sets retain the highest
reached threshold; replacement tiers remove named lower thresholds transitively.
Exclusive and other policies cannot mix. These are the existing inventory
policies, not new equipment mechanics.

`RpgProjectionPort.replaceEquipmentSet(ResolvedEquipmentSet)` receives one complete
wearer/set layer with threshold and effect IDs. Empty results remove that layer.
The production projector retains these references separately from item power and
other modifier layers. Reconciliation is repeatable, including when a wearer has
no current Warcraft representation. It cannot apply set effects to another wearer
or carry old numeric contributions onto a replacement representation.

`/inventory HERO`, `/items HERO` and `/equipment HERO` show each tier's required
piece count, effect IDs and `active`, `unmet` or `superseded` status. Active means
the threshold resolved. The catalogue's name-only effect definitions have no
gameplay bindings: `blocked_pending_gameplay_effect_bindings` remains explicit.
Set effect counts do not become health bonuses. This work does not claim working
resilience, mobility, mastery, or other named mechanics.

RPG v6 and the supported legacy migrations remain unchanged. Saves retain item
copies and wearer/slot assignments, never duplicated derived bonuses. Loading
rebuilds set layers from those assignments; a failed campaign restoration retains
the previous loadouts, representations and set layers. Item eligibility, owned
copy conservation and unique-item restrictions still run before equip mutations.

Automated coverage includes all 51 sets and 151 tiers (49 sets have middle tiers),
registered Akan equip/unequip actions, Python-to-Wurst policy vectors, alternative
piece identities and slot restrictions, separate wearers, replacement objects,
unrelated modifiers, supported saves and injected restoration failures. ROAD-0053
has scoped evidence for definition retention and resolution. Effect integration
and native-client launch remain downstream blockers; no player QA is required.
