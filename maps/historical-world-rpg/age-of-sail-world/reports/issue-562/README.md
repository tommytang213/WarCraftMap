# Battlefleet Doctrine audit recognition (#562)

The naval generator now emits one exact commissioning consumer:
`battlefleet_doctrine` → `unit:ship_of_the_line` →
`ship_of_the_line_generic`. Bills, crew, provisions, research requirements and
historical availability derive from the resolved roster and scenario recipe.
The other naval effects remain independently blocked.

The release audit invokes a scenario-neutral commissioning execution verifier.
It uses the existing `integration_evidence.verify_execution_coverage` path and
requires the complete passing pinned suite, exact revision and source digest,
current instrumented production inputs, and raw transcript probes in the isolated
registered comparison. Payment, campaign work, durable completion, snapshot and
restore must all execute. Metadata, successful research, a focused run, a merged
PR or another naval test cannot close this finding.

The comparison earns only doctrine against an otherwise identical control. It
checks the entire construction bill, no vessel from research or purchase alone,
the day before completion, one completed roster vessel, repeat delivery,
reconstruction and existing funded maintenance. Additional production tests cover
missing doctrine/supporting research/era/dock/board/funds/materials/crew/provisions,
rejection atomicity, capture cancellation, active/inactive player/AI parity and
late campaign-load rollback of paid work, research and resources. Production
completion was extracted into a private method solely to probe the existing
completion boundary. No save format, migration, starting asset, balance or native
startup/handoff behavior changes.

`focused-validation.json` and compressed logs record developer-side validation.
The real pinned interpreter typechecks the full generated production assembly and
executes all 14 naval tests. Only unrelated test annotations are removed in the
disposable assembly; production remains intact and probes use the repository
instrumenter. Docker mounts that assembly read-only, runs as the image's default
non-root user, and copies it into container-private `/tmp` before building.
Synthetic transcripts in `test_naval_binding_evidence.py` are protocol regressions,
never release execution evidence.

Reproduce focused Python checks from the scenario directory with
`python3 -m unittest discover -s tests -p PATTERN` for
`test_naval_binding_evidence.py`, `test_naval_services.py`,
`test_integration_evidence.py`, `test_research_generation.py`,
`test_release_blocker_audit.py`, `test_runtime_acceptance.py` and
`test_requirement_traceability.py`. The framework boundary command is
`python3 ../_shared/tooling/audit_framework_boundary.py`.

The checked-in release/runtime/traceability reports are refreshed **source-only**
snapshots and retain this finding and all unrelated blockers. This isolated
worktree starts at `142ccf224ceeaeb75a0bf5656f84b2e7ac9519ad`; it neither merges
predecessor #561 nor reuses predecessor artifacts. The controller owns complete
repository validation after integration preflight. On the new integrated main,
run the complete pinned suite and consume its fresh results/transcript through
the #560 evidence delivery path. Regenerate all three audits using that same
revision and source digest:

```sh
python3 tooling/runtime_acceptance.py --write --execution-dir "$EXECUTION_DIR" --source-revision "$REVISION"
python3 tooling/release_blocker_audit.py --write --execution-dir "$EXECUTION_DIR" --source-revision "$REVISION"
python3 tooling/requirement_traceability_audit.py --write --execution "$EXECUTION_DIR/results.json" --transcript "$EXECUTION_DIR/execution.log" --source-revision "$REVISION"
```

Include the exact built campaign/artifact through the existing audit options when
checking artifact readiness. Close #562 only when its exact release finding
disappears through this verifier. Release/launch promotion, including #397 work,
continues to require freshly regenerated zero-blocker closure and closed repair
issues. No player QA or native-playability claim is part of this change.
