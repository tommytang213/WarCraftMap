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
all source, and executes the complete suite with the unchanged interpreter
deadline. It then builds and inspects a diagnostic W3X and runs original/content-mutated
framework campaigns. `CARGO_TARGETED=1 CARGO_PACKAGE=1` selects the cargo-related
suites; `FOCUSED_SUITES` can override that selection with comma-separated filenames.
Test selection changes only the private copy. The wrapper records per-test wall
times in the private assembly's `_build/test-timings.json`. No services,
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

Final verification after the merged-suite repair:

- Pinned typecheck and **531/531** Wurst tests passed in one complete run with the unchanged 20-second deadline.
- **400** Python test executions passed across trade/persistence, integration/packaging and automation checks. Python compiler fixtures verify orchestration; they are separate from pinned execution.
- Original and content-mutated framework campaigns each passed **2/2** Wurst tests and campaign packaging.
- World validation, framework boundary, geography, canonical map source, traceability and whitespace checks passed.
- The diagnostic W3X retains all **829** source store definitions and the registered mixed-cargo implementation.

Source revision: `96c32d45ce851dc435cfa268340fb6aeedf93b13`.
Source tree SHA-256: `a9253abd7c2f58eeef20cad56f1feb85062dfa179394748491539bec185d17bd`.
Execution, packaged definitions and regenerated scoped traceability bind to this
same source tree. The longest measured test took
**8.689 seconds**.

The full-suite compiler saturated its 6 GiB heap. JVM counters showed 350 full
collections and 501.063 seconds of garbage collection. The validation subprocess
now reserves 8 GiB, while explicit caller heap settings still take precedence.
The compiler and its 20-second test deadline are unchanged. The heap regression
checks execution and packaging and verifies the caller environment is unchanged.
Generated RPG batches are selected
before treasure resolution, so discarded treasures do not repeat that work.
Visit commands also install their own fixture clock and clear it on close; the
focused baseline exposed their dependency on a previous test's global clock.
All existing journeys, assertions, catalogue registrations and 531 test cases
remain. No gameplay accounting, save schemas or scenario definitions changed in
this validation repair.

The retained before/after evidence and per-test timings are indexed in
[timeout-repair-validation.json](timeout-repair-validation.json). The earlier
release-audit input-hash repair remains recorded in
[repair-validation.json](repair-validation.json). Its 241 campaign/publication
blockers remain; native launch is still
`blocked_pending_real_forsaken_kingdom_launch_smoke`.
