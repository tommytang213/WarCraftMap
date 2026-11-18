# Scoped command and science validation

Source: local exact commit `6b6a3dacc58fe59876bb9066b5024fc46b9f401c`,
source-tree identity `54bc0d7c4ac665d4721cb36798bc9d42c7637e292e850ee8b60c951de192c762`.
This is extracted local compiler evidence, not Docker execution, native Warcraft
acceptance, a complete passing execution gate, or release approval.

## Focused pass
The checked-in fail-closed focused replay runner completed typecheck and 48
individual tests: installed help 4, quest rewards 19, science exploration 25.
The retained report/transcripts were independently reparsed and audited. Actual
compiler identity matches the pinned jar; source identity, 175 verifier inputs,
304 dependency files and launcher/compiler hashes remained stable. Snapshots
were frozen before typecheck and checked after each suite. Bootstrap/runtime
origin is not certified by those hashes; cooperative persistent-drift detection
is not an atomic change-and-revert defense.

This covers corrected installed help pagination/topics, visit-before-reward
research ordering, and stronger science regression assertions. It does not
enable any isolated story-service pilot. Use the current
`_shared/tooling/focused_wurst_replay.py` and its documentation for a new replay,
with the exact source checkout and explicitly supplied local toolchain/bootstrap.

## Full attempt failed
The separate full production Python execution gate passed 298 of 878 discovered
tests, then stopped. Two tests in `CommandMapTransportTests` timed out at the
unchanged 20-second interpreter limit:
- `commandRemoteSaveRecoveryAndRejectedHomeProjectionRetainOrders`
- `commandPreservesIncapacitatedPartyPauseClockAndAutosave`

The other 578 discovered tests were not run after that failing batch. Incomplete
rows are not passes. The full transcript (losslessly compressed as `full-attempt/execution.log.gz`)
and fail-closed results are retained;
the wrapper reports `completed: false` and unchanged termination snapshots.
No timeout, discovery, instrumentation, or packaging gate was relaxed.

The archived wrapper records this invocation only, not a reusable tool. Its
absolute paths and literal revision are historical. It checked actual clean HEAD
and tooling checkout, used plain Python (no `-O`; optimization disabled), froze
inputs/dependencies before typecheck, and checked wrapper boundaries. Dependency
checks were not per execution shard. The production execution tool additionally
checked its own source/verifier-input conditions. `WURST_IMAGE` was explicitly
removed; the compiler report must not be read as container provenance. Full
runtime, bootstrap and launcher origin remain outside this evidence.

Native Austria → Victory → Continue, full exact-head acceptance, issues #438 and
#600, and draft/no-release gates remain open.

## Source-only report freshness

Runtime/release audits remain blocked (expected nonzero exits). Traceability and
checked-in report freshness passed. This refresh received no execution evidence
and grants no new runtime/native/release acceptance. Its receipt and command logs
are retained in `report-freshness/`; authoritative source identity was unchanged.

The gzip member is deterministic (`mtime=0`). Its decompressed bytes exactly
match `full-attempt/results.json:logSha256`; compression changes storage only.
