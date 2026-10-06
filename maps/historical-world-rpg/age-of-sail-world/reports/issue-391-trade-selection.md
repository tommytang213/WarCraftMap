Issue #391 makes local market, commodity and cargo-store selection reachable
through the registered `/trade` command and `/market` alias. The command reference
is [LIVE_TRADE_COMMANDS.md](../docs/LIVE_TRADE_COMMANDS.md).

Generated store bindings resolve existing personal, settlement and vessel
authorities. A field character must physically reach the settlement; vessel cargo
also requires a living, controlled vessel alongside it. Citizenship, remote map
views and saved selections confer no access. Commands recheck discovery, control
and physical presence before invoking the existing transaction controller.
Selection and rejected transactions do not create stores, reset balances or
consume transaction numbers. Cargo transfers retain FIFO acquisition provenance.

Trade schema 2 and campaign envelopes 1–7 remain supported. Generator version 18
adds immutable store bindings; mutable ownership, location and merchant standing
continue to use their existing authorities and save formats. Loading older saves
cannot introduce the newly registered personal hold's starting currency.
Summary-only saves resolve the historical starting-settlement store (or the old
first-store fallback), preserving its capacity even when the current UI selects
a different store. Committed loads require renewed selection; rejected loads
restore the previous selection validation and management pause owner.

The production command journey uses generated definitions and recording physical
observations for two commodities, personal/warehouse/vessel stores, transfers,
and travel from Lisbon to London. It dispatches every player action through the
registry, including replay attempts after a populated save round trip. Other
regressions cover unknown, hidden, remote and unauthorized targets; incompatible
cargo; movement and control changes before commit; legacy migration; rollback;
and bounded listings with the existing modal pause lifecycle.

Final validation evidence is retained locally under the worktree's ignored
`_build/issue-391-review/` directory, including `pinned-wurst.log`,
`pinned-results.json`, `source-inputs.json` and `headless-results.json`.
Earlier evidence remains under `_build/issue-391/`. The final container run uses
`frotty/wurstscript@sha256:ea428badd326df6f16f5d3857f7aadc100dbaacfbdb8fbac026933ab369fbb5a`,
the `wurstuser` account, mounts assembled source read-only, and copies it into
container-private `/tmp`.
The compiler SHA-256 is checked against the repository pin
`1f3ae40b1018b8757867515596adfa69113ca85f390c1b353cc8b69cf8944145`.
Python packaging regressions use their documented synthetic compiler fixtures;
the separate container run executes the actual pinned Wurst compiler.

- Source-map and world-data validation passed.
- Final pinned Wurst typechecking passed; all 239 interpreter tests passed,
  including all seven trade-command regressions. The repository's execution-log
  parser matched every discovered test to a passing result, with no errors.
- `grill build map/AgeOfSailWorld.w3x` succeeded on the final source copy.
- 90 Python tests passed: physical-interaction generation, campaign saves and
  save manager, cross-map persistence, supported saves, native-save regression
  harness, Wurst execution gate, trade bindings, headless trade, map packaging
  and campaign packaging.
- All checks above include the summary-save migration regression. Assembled
  Wurst inputs were compared with the final source, and generated provenance
  was verified before validating the complete execution transcript.
- `git diff --check` passed.

Release status remains `blocked_pending_real_forsaken_kingdom_launch_smoke`.
These checks do not establish native-client launch success. No player QA,
commits, pushes, GitHub changes or host tooling changes were performed.
