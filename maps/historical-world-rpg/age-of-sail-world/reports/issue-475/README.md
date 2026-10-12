# Issue #475: simultaneous commodity balances

The shared live store now owns sparse quantities by commodity ID. All contents
use one existing capacity; buy/sell and explicit-commodity transfers preserve
other quantities and their FIFO acquisition costs. `/trade inspect [PAGE]` shows
six balances at a time with total used capacity. The registered transfer accepts
`SOURCE DESTINATION COMMODITY QUANTITY`; its older shorthand requires one known
source commodity. Existing access, current quotes, replay, currencies and generated
store definitions remain authoritative.

Trade domain v4 migrates supported single-commodity saves and retains unknown
legacy identities as separate, space-occupying uncosted cargo. Validation subtracts
lot quantities from a temporary ledger per store/commodity before live mutation.
Current saves do not initialize money for newly added, omitted stores. Legacy
additive-definition migration remains supported. The campaign envelope stays v10.
See [the wire contract](../../docs/LIVE_TRADE_SAVE.md) and
[the commands](../../docs/LIVE_TRADE_COMMANDS.md).

`test_mixed_cargo.py` computes headless states for two sale orders and verifies
22 executable registered-command snapshots. Each compares all commodity balances,
remaining costs, store currency and market stock/liquidity. Every order allocates
exactly 94 acquisition-cost units. Additional live cases cover mixed stores,
compatibility/capacity, access loss, stale/remote actions, bounded inspection,
uncosted cargo, integer remainders, malformed records, replay, supported migration,
fresh services, failed storage, physical travel/return and late restoration rollback.
The prize adapter preserves unrelated mixed destination cargo and rejects a mixed
source because its separate history contract still records one commodity.

`validate.sh` copies read-only source/dependency mounts into container-private
`/tmp`, uses the immutable pinned compiler offline as its non-root user, typechecks
all source, and executes the selected trade/pricing/persistence/access/framework
suites with the unchanged interpreter deadline. `CARGO_TARGETED=1 CARGO_PACKAGE=1`
also builds and inspects a diagnostic W3X and runs original/content-mutated
framework campaigns. Test selection changes only the private copy. No services,
packages or global tools are installed; no container writes into this worktree.

`report.py` verifies compressed transcripts, the pinned compiler, current source
hashes, same-source packaged store definitions and both framework executions
before regenerating `scoped-traceability.json`. The uncommitted source-tree hash
binds evidence to the recorded base revision. Python packaging fixtures use a
synthetic compiler and are separate orchestration checks, not Wurst execution.

Closure is limited to the mixed-cargo portion of ROAD-0046 and REQ-0060/REQ-0066.
Broader economic simulation and reputation work retain their blockers. Native
launch remains `blocked_pending_real_forsaken_kingdom_launch_smoke`; the diagnostic
package and scoped interpreter execution do not establish release readiness.
No player QA, commits or remote repository changes are part of this work.

Final verification:

- Pinned typecheck and **177/177** selected Wurst tests passed.
- **212** Python tests passed.
- Original and content-mutated framework campaigns each passed **2/2** Wurst tests and campaign packaging.
- World validation, framework boundary audit, traceability consistency and `git diff --check` passed.
- The diagnostic W3X retains all **829** source store definitions and the registered mixed-cargo implementation.

Source revision: `51862ed5525219922efb0f73119257cbd465810f`.
Source tree SHA-256: `6002478d8f18e00d981d200c0952da44bc1819349706d60780037b8ed17b569c`.
The package check was corrected to the compiler’s actual `TradeCommand_TradeCommand_execute` method and its `CommandHandler_execute` binding, then verified against the exact built archive.
