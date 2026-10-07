# Issue 411 validation evidence

The canonical router now installs the recording and Warcraft boundaries through
the same trigger/action path. The six command-help obligations have individual
success, rejection, stale-registration and replay receipts from
`InstalledCommandHelpTests.wurst`. Tests use production command metadata and
compare complete campaign authority and storage write counts around help.

`validation.json` records the base Git revision and the dirty-source SHA-256 used
by the pinned compiler. No implementation commit was created. Execution inputs,
transcript hashes and the exact diagnostic W3N hash distinguish this worktree
from its base revision. Generated archives remain under `_build`, outside Git.

The pinned toolchain was read from the existing Docker image into the worktree's
ignored tool directory and executed locally with a worktree-local Java user
home. No service or global tool installation, writable container source mount,
or container ownership change was used.

The evidence includes:

- The complete pinned Wurst execution transcript and result/input digest report.
- Original and content-mutated shared-framework builds and pinned executions.
- Two executed mutants: removed chat registration and disconnected callback.
  Each preserves 3/3 passing handler tests but fails all 4 installed-help tests.
- Python gate mutations retaining synthetic passing receipts while removing
  registration/callback source anchors. These must still report unreachable
  requirements; synthetic protocol receipts are never release evidence.
- The bounded selector package list and unchanged out-of-scope blocker census.
- The full exact-artifact traceability report, scoped verification, compiled
  runtime acceptance, and repository headless-check log.

After building the campaign with the pinned compiler, reproduce the final scope
check from the Age of Sail project directory:

```sh
python3 reports/issue-411/verify-scoped-evidence.py
```

To execute the two mutations, supply an assembled compile tree with installed
stdlib dependencies, the pinned Grill executable, and a fresh output directory:

```sh
python3 reports/issue-411/run-negative-fixtures.py \
  _build/wurst-tests/compile /path/to/pinned/grill _build/help-mutants
```

The complete traceability report remains a publication blocker. Scoped help
readiness does not waive any other requirements, retail-launch or archive
compatibility gates. These checks require no player QA. See
[`COMMAND_HELP.md`](../../docs/COMMAND_HELP.md) for the read-only persistence and
listener lifecycle policy.

The repository wrapper passed all 912 scenario Python tests, then reported 14
errors in the unchanged worker validation-repair fixtures (129 automation tests
run). Those fixtures leave `planning_context` history calls unmocked and invoke
`gh issue list` against local repositories without a GitHub remote. The wrapper
therefore exits 1; this snapshot does not claim a fully passing repository
wrapper. The separate 285-test pinned Wurst run, 17-map typecheck/build, both
shared conformance campaigns, and all six exact-artifact obligations passed.
