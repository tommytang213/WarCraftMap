# Live trade provenance and save contract

`PlayableTradeRuntime` writes trade domain version 3 (`v3:`). The campaign
envelope is version 8, supporting envelopes 1–8. This follows the existing
independently versioned diplomacy and military domains. The headless JSON trade
contract already contains attributable lots and remains unchanged.

Player selection, physical access and cargo-transfer commands are documented in
[LIVE_TRADE_COMMANDS.md](LIVE_TRADE_COMMANDS.md). Generated access bindings reuse
the saved military and merchant authorities; saved selections never confer access.
Older saves that omit the now-registered personal hold receive a zero balance for
that missing store before any saved record or legacy summary is applied.
Summary-only generated saves retain the historical starting-settlement store
(or the first generated store when no local store exists), including its capacity.
Their destination does not depend on the current UI selection or the newly
registered personal hold.

`_shared/wurst/CargoProvenance.wurst` uses the FIFO rules from
`_shared/engine/trade.py`. Each acquisition records its stable store ID,
commodity ID, quantity, integer cost and original market ID. Sales consume only
matching lots. Transfers append the consumed portions after acquisitions already
in the destination. Partial allocation floors `cost * taken / quantity` and
leaves the entire remainder on the source lot. Zero allocated cost still retains
legitimate provenance. Empty lots are removed. Uncosted balances remain uncosted.

A sale containing uncosted quantities earns no ordinary merchant standing.
For fully costed profitable sales, the existing standing calculation uses only
the profit attributable to origins other than the selling market. A new purchase
cannot change earlier lots' origins. Existing standing, realized profit and
completed-route progression persist. Transaction and lot capacity are checked
before mutation; replay history is never evicted to accept another transaction.

After the `v2:` or `v3:` prefix, fields 0–19 retain the former colon-delimited layout.
Fields 8–10 now hold **unattributed legacy** cost, quantity and last origin;
they are archival history and never participate in sales or transfers. Fields
20–22 contain the selected market's commodity, selected hold's commodity and
ordered lots. A lot is `storeId,goodId,quantity,cost,originMarketId`; lots are
separated by `~`. Store IDs retain the existing colon-to-semicolon encoding.

The production validator checks all records before mutation, including lot
amounts, known stores and origin/commodity pairs, matching saved store
commodities, total attributed quantities no greater than saved holdings, and
agreement between the selected hold summary and its store record. Reconstruction
and rollback use the same serialization; campaign load still commits through
the existing staged transaction boundary.

Unversioned legacy documents with 16, 17, 19 or 20 fields are supported. Their
single aggregate cost/quantity/last-origin tuple cannot identify the actual
stores, commodities or earlier origins, even when the currently selected hold
happens to match the total. Migration retains that tuple as unattributed history
and creates no acquisition lots. Cargo, money, recorded commodities, market
state, processed transaction IDs, next transaction number and earned progression
are retained. The summary-only formats never saved the hold's commodity; their
cargo quantity remains present with an unknown commodity rather than guessing
an identity from the selected market. New purchases receive normal provenance.
Resaving writes v3 and migration is idempotent. Source saves are not rewritten.

Quantity-aware pricing does not change this wire format. The live domain stays
independently versioned; the campaign envelope remains version 8. Base prices, target stocks,
quantity units, elasticity, spread and price bounds are generated definitions;
generator provenance is version 18, including the trade access bindings. Current
stock and persisted live modifiers determine every commit quote. Cached displayed
prices never authorize a debit or payout, including after restoration. Opening a
market computes fresh display prices without changing persisted observations or
other authority.
Existing acquisitions retain
their actual recorded cost, even when the old pricing bug undercharged them;
holdings, earned profit/standing, route history and replay IDs are not rewritten.

`_shared/wurst/TradePricing.wurst` and `_shared/engine/trade.py::quote()` sum
marginal prices over the stock interval traversed by an order. Each indivisible
quantity unit uses its midpoint rounded toward the upper stock endpoint, on
both buys and sells. Scarcity, condition modifiers, pressure bounds, base-price
half-up rounding and spread are applied at each edge. Only the summed amount is
converted from quantity units to minor currency: buys round up, sells round
down; a sale below one minor unit is rejected. Equal-price intervals are grouped
so work is bounded by the 2,751 scarcity bands rather than the quantity.

This refines the former whole-order midpoint approximation: rounding or clamping
one midpoint is not additive and can reward different partitions of the same
stock movement. With marginal prices, every closed stock path traverses each
edge equally in both directions, and its buy price is at least its sell price.
Currency settlement rounding can only increase buy costs or reduce proceeds.
No batching, reverse ordering or repeated cycle can create currency while the
market's other authority is unchanged. Different markets and subsequent
economic changes may still produce legitimate profit.

For stock/target 100, base price 10 and spread 80, buying 75 costs 1,080 and
returning them pays 905. The five base-10 edges and ten each at base 11 through
17 independently give those totals after spread. New lots record 1,080 as the
actual acquisition cost. Existing pre-fix lots retain their historical cost.

`PlayableTradeTests.wurst` covers independent cost expectations, interleaved
stores/goods/origins, partial transfers and sales, integer remainders, uncosted
cargo, replay and rejection, malformed records, populated codec round trips,
and all four legacy layouts in every supported campaign envelope.
`TradePricingTests.wurst` adds the reported round trip, split/reversed/interleaved
orders, unchanged-world repeated cycles, stale authority, atomic rejection,
integer limits, economic-change profits, a literal pre-fix v2 save and purchase/
resale through all seven supported campaign envelopes.
`TradePricingVectorsTests.wurst` executes 71 live quote cases;
`test_trade_pricing.py` checks their literal expected
amounts against the headless contract and an independent rational per-edge
oracle, plus deterministic randomized partitions. Packaging tests verify that
every generated market receives the authored pricing definitions.
`CampaignLoadTransactionTests.wurst` also injects failure after applying changed
trade state and verifies populated lots, earned standing, other campaign domains,
projections and source slots roll back together.

Release status remains `blocked_pending_real_forsaken_kingdom_launch_smoke`.

Trade v3 adds the market discovery bit as column 14 of each market record while
retaining additive catalogue registration. V2 and the unversioned layouts still
migrate. Before applying those older records, reconstruction resets
registered definitions to their initial balances/profiles, then applies the saved
state. This initializes newly included abstract settlements deterministically,
including after loading the same legacy save over a changed campaign. Existing
saved balances, capacity, commodities, provenance and progression override these
defaults. Missing personal stores retain the existing zero-balance migration.
Generated bindings and local actor checks remain the only access authority.
