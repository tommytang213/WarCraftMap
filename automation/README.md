# Low-priority autonomous worker

This worker consumes open GitHub issues whose titles begin with `[agent-ready]`.
Titles beginning with `[needs-design]` or `[planned]` are never selected. It runs only one
process and one issue at a time, in a dedicated `agent/issue-N` branch and
worktree. Codex runs with `workspace-write`, `--approve-for-me`, a 45-minute
timeout, and no dangerous sandbox bypass.

The primary budget is token-based: 100,000,000 reported Codex tokens per UTC
day and 500,000,000 in any rolling seven-day window. Codex is invoked with
machine-readable JSON output and the worker records per-run usage. Because token
telemetry can fail or change across Codex versions, emergency caps of 10 runs
per day and 50 in a rolling seven-day window remain in force. A run is recorded
before launch, including crashes and timeouts; missing telemetry is recorded as
unknown rather than treated as a free run. Initial implementation gets at
most three initial attempts. Repository-validation repair before a PR, CI
repair after a PR, and merge-conflict repair each use separate five-attempt
budgets, so one exhausted lane cannot strand otherwise repairable work. If main
advances while a CI-failing PR is being repaired, that PR receives a fresh CI-repair budget for
the new base revision. Exhausted repair lanes become explicit `failed` states
rather than unselectable `repair` states. Pull requests merge only after
reported CI checks complete successfully. A PR that becomes unmergeable is
moved to its conflict-repair lane; the worker merges current main into its
preserved issue worktree, asks Codex to resolve only genuine conflicts while
retaining both work streams, validates, and pushes the repaired branch. The timer
may wake hourly, but exhausted workers exit before Codex.

After GitHub confirms a PR is merged, the worker removes its clean issue
worktree, then its local agent branch, and separately tries to delete the remote
agent branch. Dirty worktrees are preserved. Cleanup errors are logged and
recorded without changing the issue's successful merged state.

## Preview and installation

No installation is needed for a safe queue preview:

```sh
./automation/run_agent.sh --dry-run
```

Review `automation/warcraftmap-agent.env.example`, enable systemd user lingering once so the worker continues after SSH logout, then install the user units:

```sh
sudo loginctl enable-linger "$USER"
./automation/install-user-service.sh
systemctl --user status warcraftmap-agent.timer
```

The installer creates `~/.config/warcraftmap-agent.env` only when absent. Edit
that file to adjust the model, daily/weekly token ceilings, emergency run caps,
timeout, implementation/validation/CI/conflict retry caps, state directory, or
validation command. A generic optional
`WARCRAFTMAP_AGENT_DESIGN_NOTIFICATION_COMMAND` receives a JSON object on standard
input when a blocker is first created or an implementation issue first becomes a
blocker. The object contains `issue_number`, `title`, `url`, and `question`; the
command can forward it to ntfy or another transport without storing credentials in
the worker. Delivery is best-effort and is never retried on timer wakes. Existing v1
timestamp-only state is migrated to the token-aware v2 state format without
discarding prior invocation history. Logs, worktrees, and quota state live under
`~/.local/state/warcraftmap-agent` by default. The service is deliberately
low-priority (`Nice=19`, idle I/O scheduling, low CPU/I/O weights). It uses the
already-authenticated `gh` and `codex` CLIs and never upgrades them.

Before each worker starts, the launcher fetches the configured controller
branch (or `origin`'s default branch) and fast-forwards the controller checkout.
It does this only from the primary checkout when that checkout is clean and on
the expected branch. Dirty, detached, divergent, and isolated-worktree states
are logged and preserved; update failures do not reset files or rewrite
history. The updater exits before a fresh Python worker process starts, so code
is never hot-reloaded. Set `WARCRAFTMAP_AGENT_CONTROLLER_BRANCH` only when the
controller intentionally follows a branch other than the remote default.

Every wake reads the release-blocker, runtime-acceptance and exhaustive
requirement-traceability reports, plus complete open/closed issue and PR history.
The scenario's `tooling/planning_audit.py` regenerates all three audits in memory
on the current origin default-branch revision. It verifies available execution
and campaign artifacts through the existing audits; it never treats saved PASS
flags, closed issues or merged PRs as closure. Missing reports, failed audits,
dirty/outdated controller checkouts and stale execution evidence keep the gate
closed. The controller does not compile during planning or rewrite tracked
reports. Compiler execution and packaging remain repair/validation work.

While closure is pending, the worker selects and plans only blocker repairs,
even when unrelated ready work fills the queue. Repeated symptoms are grouped by
stable requirement/finding identity, with runtime findings shared across reports
deduplicated. Missing global runtime execution is repaired before validating
domains whose source checks pass; a package census waits for its final artifact.
Traceability interaction repairs wait for their prerequisite obligations to pass
a regenerated audit and for prerequisite repair issues and PRs to close.
Each generated issue records
`Closure blocker: <identity>` and `Closure revision: <main SHA>`. These markers,
legacy stable-ID references, linked PRs and normalized titles prevent duplicate
work across open and closed history; history retrieval grows beyond the preview
issue limit. A fresh failing audit after a merge allows a scoped follow-up on the
new revision. Before creating each issue the controller checks history and main
again. Open generated repairs continue to hold closure even if findings clear.

Closure repairs are planned in batches of at most ten, with at most four closely
related identities per issue. Only the unblocked, unrepresented frontier is sent
as candidates. No optional content fills spare slots, and `exhausted` is rejected
while closure remains pending. Genuine material decisions become `[needs-design]`
questions; independent blocker repairs continue. `Blocked by: #N` or
`Depends on: #N` holds execution until the referenced issue is closed, including
implementation dependencies. PR recovery and merging obey the same dependency
and design gates as issue selection. Audits are regenerated again on the new main
revision after each repair merges.

Once all reports are clean and generated repairs are closed, ordinary planning
resumes: when fewer than three independent `[agent-ready]` issues remain, one
budgeted Codex planning run refills toward ten using the roadmap, design lock,
architecture, agent rules and history. An exhausted roadmap then exits cleanly.
Planning and implementation remain sequential, so worker concurrency is still one.

Open `[planned] Phase N: ...` issues reserve future roadmap work. Before queue
selection or replenishment, the worker promotes an eligible reservation in place
by changing only its prefix to `[agent-ready]`; it never recreates the issue.
Promotion first requires a freshly regenerated zero-blocker closure state with
no open repair issues or PRs. This holds all planned reservations, including
release/launch issue #397, regardless of completed roadmap checkboxes. Main and
repair history are rechecked before promotion. Promotion also requires every checkbox in the immediately preceding phase of the
authoritative `docs/ROADMAP.md` to be complete. Every `Depends on: #N` line in
the issue body is also a blocker until that referenced issue is closed. General
`[planned]` issues without a recognizable `Phase N:` title remain untouched.
Audit IDs cited in a planned reservation do not claim its prerequisite repairs;
explicit `Closure blocker:` markers still hold closure if a repair is deferred.
All three workflow prefixes normalize to the same logical title, so planned
reservations suppress duplicate queue-refill issues. Dry-run mode reports each
promotion that would occur but does not edit GitHub.

Issue bodies should be implementation-ready and contain acceptance criteria.
If Codex identifies a missing material design decision, the worker renames the
issue to `[needs-design] ...` and comments the exact question. It does not ask
the player to perform incremental testing.

## Validation

`automation/run_checks.sh` runs world-data validation, Python tests, Wurst
typechecking, the complete Wurst execution suite, and map packaging. It uses
local `grill` with the pinned compiler digest when present and otherwise the
pinned Docker image with a read-only source mount and private build copy. Container
compilation runs as `wurstuser`, whose home contains the pinned compiler; root
only prepares the private copy and Python dependency. Developers
may explicitly set `WARCRAFTMAP_WURST_CHECK=skip` only for focused Python tests;
the worker's default remains required.

Execution writes per-test results, compiler identity, revision, input hashes and
the raw transcript under the scenario's `_build/wurst-tests/`. Both map and
campaign release paths require complete passing execution. The RC ZIP retains
the evidence under `Metadata/wurst-execution.{json,log}` and the upload verifier
checks it again. Interpreter success does not close the real-client launch gate.

## Safe removal

```sh
./automation/uninstall-user-service.sh
```

This disables and removes only the two WarCraftMap user units. It intentionally
preserves configuration, quota history, logs, and worktrees so uninstall cannot
destroy work. The script prints their exact locations for optional manual review
and removal. It does not touch DevCommand or any global toolchain.
