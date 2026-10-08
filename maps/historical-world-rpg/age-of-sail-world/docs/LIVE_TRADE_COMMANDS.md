# Local market and cargo commands

| Action | Command |
| --- | --- |
| List eligible nearby markets | `/trade markets [PAGE]` |
| Inspect discovered local commodities and quotes | `/trade commodities MARKET [PAGE]` |
| Select a market and commodity | `/trade select MARKET COMMODITY` |
| List eligible stores at the selected market | `/trade stores [PAGE]` |
| Select a cargo store | `/trade store STORE` |
| Buy or sell using the selected store | `/trade buy QUANTITY`, `/trade sell QUANTITY` |
| Transfer cargo between two eligible stores | `/trade move SOURCE DESTINATION QUANTITY` |
| Inspect the current local selection | `/trade inspect` or `/trade open` |
| Close market management | `/trade close` |

`/market` is an alias for `/trade`. Lists show six eligible entries per page.
Unknown, undiscovered, inaccessible and malformed requests receive bounded
English feedback without exposing hidden identifiers. Use the exact commodity
and store IDs shown in the lists. Quantities must be positive whole numbers.

For example, at Lisbon use `/trade commodities lisbon`,
`/trade select lisbon grain`, `/trade stores`, `/trade store player_ship_hold`,
and `/trade buy 2`. Close management before travelling. At the next settlement,
list and select that settlement's market and commodity before selling. Each
store retains its own currency; cargo transfer moves quantities and acquisition
lots, without transferring currency or replenishing any balance.

Markets require a recruited, capable field character physically within the
existing 256-world-unit interaction range of the generated settlement point.
Commands act for the single-player campaign owner in slot 0; another Warcraft
player cannot use these stores by controlling a character representation.
The loaded chapter and party map must agree, and startup, staged loads and map
transitions must have finished. Market commodity discovery, blockade,
hostile-occupation flags and active war with the settlement's current controller
are checked against their existing authorities. Saved settlement coordinates,
building handles, map tracking and remote command views do not grant presence.

Store bindings are generated definitions:

- The existing `player_ship_hold` is the player's portable personal store. Its
  stable ID and existing capacity are retained; the name does not imply ownership
  of a generated vessel.
- `warehouse:SETTLEMENT` is local to that settlement. Access requires either
  player ownership and control or the authored warehouse service plus the
  existing merchant warehouse-access unlock (100 standing). Origin citizenship
  and current allegiance do not grant warehouse ownership.
- `cargo:VESSEL` requires an active, living vessel under the existing `player`
  controller, on the same physical map, with a live owned representation alongside
  the settlement. A saved spawn coordinate or a movement order is insufficient.
  National vessels remain ineligible solely on the basis of citizenship.

No remote trade authority is implemented. Selection and each transaction resolve
presence and eligibility again immediately before committing. Changed settlement
control invalidates the selected market; lost store control or physical access
rejects a transaction. After load, market and store IDs remain selected as views,
but the player must select them again before transacting. Selection creates no
store, resets no resource and awards no progression. The existing transaction
controller owns atomic buy/sell/transfer, FIFO provenance and replay history.
Rejected commands leave the economic state and next transaction number unchanged.

Listing and inspect/open actions share the existing market management session.
Repeated opens retain one pause owner. Select/store/buy/sell/move actions do not
open management. `/trade close` releases only that market owner, preserving other
management sessions and manual pause. Failed or aborted loads retain the session
and previous selection validation; committed reconstruction closes the session.

Trade schema 2 and campaign envelopes 1–8 remain supported. Access bindings and
interaction points are regenerated definitions (generator version 18), not saved
permissions or new mutable location records. Current military ownership/control,
RPG physical observations and merchant standing remain the authorities, with
their existing save contracts. Older generated trade saves omitted the personal
store: reconstruction initializes that absent store with zero cargo and currency,
then applies any saved personal record or legacy hold summary. Existing warehouse
and vessel balances, selected IDs, lots and transaction history are retained;
repeated migration cannot introduce starting money. See [the trade save contract](LIVE_TRADE_SAVE.md).
The oldest summary-only saves use their historical starting-settlement store,
with the previous first-store fallback, so registering the smaller personal hold
does not redirect their balances or reduce cargo capacity.

`TradeCommandTests.wurst` dispatches the production registration using generated
markets, stores and physical locations with recording native boundaries. It
covers two commodities, three kinds of store, transfers, a two-settlement journey,
populated codec reconstruction, replay, discovery, ownership, movement, control
changes during commit, invalid cargo, migration, rollback and bounded listings.
The journey never calls `selectMarket()` or `moveCargo()` directly and never assigns
`runtime.hold`. `test_trade_selection.py` validates all generated store bindings
against their scenario and campaign definitions. The existing modal, interaction,
trade, command-router, persistence and packaging suites remain required.

Release status remains `blocked_pending_real_forsaken_kingdom_launch_smoke`.
No incremental player QA is required.
