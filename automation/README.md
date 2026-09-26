# Low-priority autonomous worker

This worker consumes open GitHub issues whose titles begin with `[agent-ready]`.
Titles beginning with `[needs-design]` are never selected. It runs only one
process and one issue at a time, in a dedicated `agent/issue-N` branch and
worktree. Codex runs with `workspace-write`, `--approve-for-me`, a 45-minute
timeout, and no dangerous sandbox bypass.

The default quota is one Codex invocation per UTC day and five in any rolling
seven-day window. An invocation is charged immediately before launch, including
timeouts and crashes. Each issue gets at most three invocations. CI failures are
left for a later, budgeted repair attempt. Pull requests merge only when their
check rollup is complete and successful and GitHub reports required checks as
successful. The timer may wake hourly, but exhausted workers exit before Codex.

## Preview and installation

No installation is needed for a safe queue preview:

```sh
./automation/run_agent.sh --dry-run
```

Review `automation/warcraftmap-agent.env.example`, then install the user units:

```sh
./automation/install-user-service.sh
systemctl --user status warcraftmap-agent.timer
```

The installer creates `~/.config/warcraftmap-agent.env` only when absent. Edit
that file to adjust model, quotas, timeout, attempt cap, state directory, or the
validation command. Logs, worktrees, and quota state live under
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
