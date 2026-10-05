# Issue 380: live cargo acquisition provenance

Live purchases now create FIFO lots keyed by store, commodity and original
market. Sales consume only matching acquisitions. Transfers split and move
those lots, retaining every integer cost remainder. The reusable implementation
lives in `_shared/wurst/CargoProvenance.wurst` and follows the existing headless
trade lot allocation rules. Uncosted cargo cannot borrow another store's history
or earn ordinary standing; later purchases cannot overwrite earlier origins.

The live trade domain is version 2. Campaign envelopes 1–6 remain supported.
All four legacy aggregate layouts migrate without inventing lots: untraceable
cost/quantity/last-origin history is retained separately, alongside holdings,
money, replay protection and earned progression. Current captures persist
ordered lots and the selected market/hold commodities. Validation precedes any
mutation, and the existing campaign load transaction restores populated lots
and earned standing when a late reconstruction fails. See the
[wire contract and migration policy](../docs/LIVE_TRADE_SAVE.md).

Validation completed against the uncommitted worktree based on
`a17a981ca4a713a6b8787e710d085c85cd4feff6`:

- **167/167 pinned Wurst tests passed**, including independent cost calculations,
  interleaved goods/stores/origins, uncosted and mixed cargo, transfers crossing
  lots, split sales, rounding and large integer allocation, atomic rejection,
  replay, populated serializer/codec round trips, all legacy layouts in every
  supported campaign envelope, malformed provenance, and failed-load rollback.
- **58 Python tests passed** across trade, economy, economy balance, campaign
  saves, save manager, release-save compatibility, native-save regression and
  execution-gate checks.
- **35 Python map/campaign packaging tests passed**.
- The real pinned `tooling/package_release.py` gate passed typecheck, Wurst
  execution, Lua compilation, map assembly and archive inspection. The generated
  `.w3x` existed only in disposable container storage.

[Execution results](issue-380/execution.json),
[execution transcript](issue-380/execution.log.gz),
[headless results](issue-380/headless.log.gz),
[packaging results](issue-380/packaging.log.gz),
[pinned packaging transcript](issue-380/pinned-map-packaging.log.gz), and
[validation summary](issue-380/validation.json) retain the evidence. All four
changed/new Wurst source hashes match the final executed inputs.

Container validation mounted the worktree read-only, copied sources to private
`/tmp`, and built as `wurstuser`. No ownership or permission operation targeted
the worktree. Native Warcraft gameplay was not exercised. Release status remains
**`blocked_pending_real_forsaken_kingdom_launch_smoke`**. No player QA, commit,
push or GitHub issue/PR modification was performed.
