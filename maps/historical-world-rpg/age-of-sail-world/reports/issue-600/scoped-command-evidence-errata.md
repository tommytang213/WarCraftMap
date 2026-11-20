# Scoped evidence interpretation corrections

This clarification applies to the historical `scoped-command-evidence` archive
at source revision `6b6a3dacc58fe59876bb9066b5024fc46b9f401c` and the later
`git-status-boundary` source-only refresh. Archived receipts, runner bytes,
transcripts and manifests remain unchanged. It grants no additional acceptance.

## Full attempt failure-path scope

The archived full wrapper raised on the failed execution gate before its final
`unchanged()` call. Its `finally` clause still compared the frozen assembly
snapshot and scoped source identity. `unchangedAtTermination: true` proves those
two comparisons only. It does **not** prove that Git HEAD and whole-worktree
cleanliness were rechecked at termination. A workflow-only change, for example,
is outside the scoped source identity. The initial clean exact-HEAD check remains
recorded, as do the failed 298/878 result and two incomplete timeout rows.

## Regeneration versus pre-existing freshness

The traceability command used `--write --check`. The tool writes before checking,
so its successful exit demonstrates that the regenerated output matches that
invocation's generated report. It cannot establish that the checked-in report
was already fresh before regeneration. The separately recorded freshness test
checks the resulting files; it likewise does not retrospectively attest to the
pre-refresh versions. These were source-only regeneration runs, with blocked
runtime/release statuses retained and no execution evidence supplied. Future
freshness evidence should run a read-only `--check` separately, recording whether
it occurs before or after regeneration.
