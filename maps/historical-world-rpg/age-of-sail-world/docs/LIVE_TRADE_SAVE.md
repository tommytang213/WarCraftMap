# Live trade provenance and save contract

`PlayableTradeRuntime` writes trade domain version 2 (`v2:`). The campaign
envelope is version 7, supporting envelopes 1–7. This follows the existing
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

After the `v2:` prefix, fields 0–19 retain the former colon-delimited layout.
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
Resaving writes v2 and migration is idempotent. Source saves are not rewritten.

`PlayableTradeTests.wurst` covers independent cost expectations, interleaved
stores/goods/origins, partial transfers and sales, integer remainders, uncosted
cargo, replay and rejection, malformed records, populated codec round trips,
and all four legacy layouts in every supported campaign envelope.
`CampaignLoadTransactionTests.wurst` also injects failure after applying changed
trade state and verifies populated lots, earned standing, other campaign domains,
projections and source slots roll back together.

Release status remains `blocked_pending_real_forsaken_kingdom_launch_smoke`.
