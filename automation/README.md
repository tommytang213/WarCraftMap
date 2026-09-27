# Low-priority autonomous worker

This worker consumes open GitHub issues whose titles begin with `[agent-ready]`.
Titles beginning with `[needs-design]` are never selected. It runs only one
process and one issue at a time, in a dedicated `agent/issue-N` branch and
worktree. Codex runs with `workspace-write`, `--approve-for-me`, a 45-minute
timeout, and no dangerous sandbox bypass.

The primary budget is token-based: 100,000,000 reported Codex tokens per UTC
day and 500,000,000 in any rolling seven-day window. Codex is invoked with
machine-readable JSON output and the worker records per-run usage. Because token
telemetry can fail or change across Codex versions, emergency caps of 10 runs
per day and 50 in a rolling seven-day window remain in force. A run is recorded
before launch, including crashes and timeouts; missing telemetry is recorded as
unknown rather than treated as a free run. Each issue gets at most three
attempts. CI failures are left for a later, budgeted repair attempt. Pull
requests merge only after reported CI checks complete successfully. The timer
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
timeout, attempt cap, state directory, or validation command. Existing v1
timestamp-only state is migrated to the token-aware v2 state format without
discarding prior invocation history. Logs, worktrees, and quota state live under
`~/.local/state/warcraftmap-agent` by default. The service is deliberately
low-priority (`Nice=19`, idle I/O scheduling, low CPU/I/O weights). It uses the
already-authenticated `gh` and `codex` CLIs and never upgrades them.

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
