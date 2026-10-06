# Issue 390: quantity-aware live trade pricing

Purchases and sales now settle the committed quantity against current market
authority. The shared Wurst pricing module and headless `trade.quote()` sum
marginal prices over identical stock edges in both directions, applying authored
quantity units, elasticity, spread, pressure bounds and integer rounding.
Grouping equal-price intervals bounds work for large orders. Whole-order
midpoint rounding was not additive across partitions; marginal settlement
prevents split, reversed or interleaved orders from manufacturing currency.
Different markets and subsequent economic changes can still produce profit.

For stock/target 100, base price 10, spread 80 and quantity 75, the corrected buy
cost is **1,080** and immediate resale proceeds are **905**. Independent rational
calculations and executable Wurst assertions verify both totals. Acquisition
lots record the actual charge. Inspection computes current display prices
without mutating persisted observations, and commits never trust cached prices.

Trade domain version 2 and campaign envelopes 1–6 are unchanged. Existing cargo,
recorded costs, progression and transaction history are preserved, including
pre-fix acquisitions and legacy provenance migrations. Generated definition
provenance advances to version 17. See [LIVE_TRADE_SAVE.md](../docs/LIVE_TRADE_SAVE.md).

Validation on the uncommitted worktree based on
`077e9dd7a2b3543e89a2b7c266a2ba344d596830`:

- **239/239 pinned Wurst tests passed**, with the original 20-second per-test
  limit. Coverage includes the exploit, 71 live quote vectors checked against
  headless and rational oracles, split/reversed/repeated cycles, economic-change
  profit, stale displays, rejection atomicity, replay, overflow, provenance,
  campaign load rollback and purchase/resale across every supported envelope.
- **106 Python tests passed**: 92 trade, pricing, economy, balance, campaign
  save, save manager, release compatibility, map/campaign packaging and execution
  gate tests; 14 native-save protocol and campaign-save stress tests.
- World validation, pinned typecheck, Lua compilation and map assembly passed.
  MPQ inspection verified bootstrap markers, metadata/terrain/pathing, all ten
  generated runtime resources and all sixteen custom asset imports against
  the generated inputs. Source hashes match the executed Wurst assembly.

The pinned container used a read-only worktree mount, copied inputs to private
`/tmp`, and built as `wurstuser`, using cached v3.0 dependencies and a 6 GiB Java
heap. Generated map output is confined to ignored build storage. No global
tooling, host services, ownership or permission settings were changed.

Evidence: [validation summary](issue-390/validation.json),
[pinned execution results](issue-390/pinned-wurst-results.json.gz),
[pinned compilation/test/build transcript](issue-390/pinned-wurst.log.gz),
[headless checks](issue-390/headless.log.gz), and
[save stress checks](issue-390/save-stress.log.gz).

Native Warcraft gameplay was not exercised. Release status remains
**`blocked_pending_real_forsaken_kingdom_launch_smoke`**. No player QA, commit,
push or GitHub issue/PR modification was performed.
