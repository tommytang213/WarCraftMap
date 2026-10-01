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

When fewer than three open `[agent-ready]` issues remain, the worker uses one
budgeted Codex planning run to refill the small queue toward ten issues. Planning
reads the roadmap, design lock, architecture, agent rules, repository state, all
available issue history, and PR history. It creates implementation-sized issues
in dependency order, rechecks issue and PR titles before every creation, and
creates one `[needs-design]` question for an undocumented material decision, while
continuing to plan only work that explicitly documents its independence from that
decision. Existing ready work is skipped only when its body says `Blocked by: #N`
or `Depends on: #N` for an open design blocker. A healthy queue causes no planning invocation; an
exhausted roadmap exits cleanly. Planning and implementation remain sequential,
so worker concurrency is still one.

Open `[planned] Phase N: ...` issues reserve future roadmap work. Before queue
selection or replenishment, the worker promotes an eligible reservation in place
by changing only its prefix to `[agent-ready]`; it never recreates the issue.
Promotion requires every checkbox in the immediately preceding phase of the
authoritative `docs/ROADMAP.md` to be complete. Every `Depends on: #N` line in
the issue body is also a blocker until that referenced issue is closed. General
`[planned]` issues without a recognizable `Phase N:` title remain untouched.
All three workflow prefixes normalize to the same logical title, so planned
reservations suppress duplicate queue-refill issues. Dry-run mode reports each
promotion that would occur but does not edit GitHub.

Issue bodies should be implementation-ready and contain acceptance criteria.
If Codex identifies a missing material design decision, the worker renames the
issue to `[needs-design] ...` and comments the exact question. It does not ask
the player to perform incremental testing.

## Validation

`automation/run_checks.sh` runs world-data validation, Python tests, and the
Wurst typecheck. It uses local `grill` when present and
otherwise the repository's existing Docker-based Wurst workflow. Developers
may explicitly set `WARCRAFTMAP_WURST_CHECK=skip` only for focused Python tests;
the worker's default remains required.

## Safe removal

```sh
./automation/uninstall-user-service.sh
```

This disables and removes only the two WarCraftMap user units. It intentionally
preserves configuration, quota history, logs, and worktrees so uninstall cannot
destroy work. The script prints their exact locations for optional manual review
and removal. It does not touch DevCommand or any global toolchain.
