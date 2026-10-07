# Issue 411 validation evidence

The canonical router now installs the recording and Warcraft boundaries through
the same trigger/action path. The six command-help obligations have individual
success, rejection, stale-registration and replay receipts from
`InstalledCommandHelpTests.wurst`. Tests use production command metadata and
compare complete campaign authority and storage write counts around help.

`validation.json` records the initial implementation's base Git revision and
dirty-source SHA-256. `revalidation.json` and the `revalidation-*` receipts record
the subsequent validation repair after main was merged, including the current
revision, source digest, test-fixture digest and exact diagnostic W3N hash.
Generated archives remain under `_build`, outside Git.

Post-merge validation passed 920 scenario Python tests, 129 automation tests,
285 pinned Wurst tests, all 17 physical-map builds, and both shared-framework
conformance campaigns. All six help obligations pass against the exact campaign
archive, with 24 executed receipts. Both negative fixtures still pass their three
handler tests while failing all four installed-help tests. The 9,129 remaining
release blockers match the initial evidence by ID, class and message.

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

The initial wrapper run passed 912 scenario Python tests, then reported 14
errors in the worker validation-repair fixtures. The updated worker reads issue
and PR history through `planning_context`; the fixtures still mocked obsolete
queue-list calls and accidentally invoked GitHub against local repositories.
The repair supplies complete history rows and closure evidence at those
boundaries, and rejects unexpected GitHub requests. Local Git merges, saved
worker state, retry budgets and publication assertions remain exercised.

The post-merge run uses the existing pinned compiler with a worktree-local Java
home and temporary directory. Online dependency refresh cannot open sockets in
the sandbox, so `revalidate-offline.py` copies the existing clean standard-library
checkout and core JASS files into disposable compile trees and verifies their
bytes. Its logs record the dependency revision and digest. The production
builders still execute every test, typecheck, build and archive inspection.
No container or global tooling change is needed. From the repository root, with
the pinned Grill directory on `PATH` and Java's `user.home` set to its local home:

```sh
python3 maps/historical-world-rpg/age-of-sail-world/reports/issue-411/revalidate-offline.py \
  campaign /path/to/previous/compile /path/to/pinned/grill
python3 maps/historical-world-rpg/age-of-sail-world/reports/issue-411/revalidate-offline.py \
  conformance /path/to/previous/compile /path/to/pinned/grill
```

The cache must be outside the build directories that the builders clean.
`revalidation.json` separates the repository's Python checks from the pinned
Wurst execution, full campaign build, shared conformance and exact-artifact
scope checks. The initial failed wrapper receipt remains historical evidence;
it is superseded by the post-merge results.
