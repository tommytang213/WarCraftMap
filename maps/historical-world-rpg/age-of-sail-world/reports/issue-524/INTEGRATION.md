# Issue 524 merge integration verification

This verification supersedes the earlier focused result for the current merged
worktree. The six actual merge conflicts were resolved and staged, preserving
both banking and main's army-food logistics implementation. No commit, push,
GitHub mutation, global tooling change or player QA was performed.

The independently authored v17 banking and logistics layouts migrate to military
snapshot v18. Existing policies, completed works and freight counters survive;
absent domains initialize inactive/empty. V18 requires every configured record,
and partial older ledgers still reject. The release-save manifest, current-format
test inputs and runtime source-readiness contract now agree on v18.

Validation for the source identity in `integration-validation.json`:

- Pinned Wurst typecheck and **35/35 interpreter cases passed**: six banking,
  seven logistics, ten finance, seven legacy combat migrations, research costs
  and framework cases. The raw transcript and compiler-input hashes are retained
  in `integration-wurst.log.gz` and `integration-inputs.json.gz`.
- **204 distinct Python cases passed** across core economy/research/save/execution
  (83), packaging/framework (21), finance (7), settlement integration (5), and
  release/runtime/traceability audits (88). The first audit run passed 83/88;
  correcting the stale source-readiness v17 token fixed all five affected cases,
  which passed in the retained recheck. Both audit transcripts are retained.
- Generated data verification, framework boundary and traceability report
  freshness passed. Economy checks include multi-century invariants and campaign
  save/checkpoint stress. Synthetic compiler outputs in Python packaging tests
  validate orchestration and do not count as actual Wurst execution.
- Official release-blocker, runtime-acceptance and requirement-traceability reports
  were regenerated with matching current source identities. Source-static
  readiness passes. Publication remains gated on the controller's complete-suite
  and packaged-campaign evidence; this focused result cannot close blockers.

Reproduce assembly with `python3 reports/issue-524/prepare-integration.py
PATH_TO_CACHED_WURST_STDLIB` from the scenario directory. This uses the normal
source generator/assembler and masks only unselected test annotations in the
throwaway copy. Run pinned `grill typecheck` and `grill test` there. Validation
mounted that assembly read-only at `/source`, used UID/GID 1001 with networking
disabled, and copied it into container-private `/tmp/banking-integration` before
all writes. No container changed worktree ownership or permissions. Cached
standard-library source was used only as a compiler dependency; no predecessor
execution artifacts were reused.

The controller must perform authoritative repository validation and regenerate
closure audits again on the new main revision after merge.
