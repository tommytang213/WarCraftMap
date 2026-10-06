# Issue 392 validation

Prize commands now resolve facts from current campaign, combat, military and
cargo authorities, and confirmation repeats those checks before mutation. Tests
exercise the production command registry and campaign action adapter. The runtime
contract and unchanged save formats are described in
[the confirmation documentation](../../docs/PIRACY_CONFIRMATION.md).

Final local results:

- Pinned Wurst typecheck: passed.
- Complete pinned Wurst interpreter suite: **264/264 passed**, including piracy,
  military combat, trade, clock, startup and load transactions.
- Pinned generated Lua/map build: passed (`grill build map/AgeOfSailWorld.w3x`).
- Python checks: **133 passed**, including piracy, military runtime, trade/pricing,
  clock, save manager, supported saves, cross-map persistence, runtime acceptance,
  execution-gate failure handling, map packaging and campaign packaging.
- `git diff --check`: passed.

[validation.json](validation.json) records the compiler identity, complete-suite
result, compiled source hashes and raw-log hashes. Execution used the repository's
assembly function and the pinned image
`frotty/wurstscript@sha256:ea428badd326df6f16f5d3857f7aadc100dbaacfbdb8fbac026933ab369fbb5a`.
The image mounted this worktree read-only, copied assembled sources to private
`/tmp/prize-validation`, then ran `grill install`, `grill typecheck` and
`grill test` as the image's default user. No container wrote to this worktree.
The repository result parser matched every discovered test to its terminal
result, and all repository Wurst sources matched the executed copy.
The separate map build used the same assembled sources in container-private
`/tmp/prize-packaging`; its [transcript](map-build.log.gz) records the pinned
compiler and successful Lua/map build. This is a scenario build, not a complete
campaign release package.

The compressed [Wurst transcript](wurst-execution.log.gz) contains actual pinned
interpreter execution. The [Python transcript](python-checks.log.gz) additionally
includes intentionally simulated compiler failures from packaging/gate fixtures;
those fixture messages are not the Wurst execution evidence.

Python command, from the scenario's `tests` directory:

```sh
python3 -m unittest test_piracy test_military test_warcraft_military_runtime \
  test_playable_trade test_trade_pricing test_campaign_clock \
  test_campaign_save_manager test_wurst_execution test_packaging \
  test_campaign_packaging test_campaign_save test_release_save_compatibility \
  test_runtime_acceptance test_warcraft_country_interactions test_cross_map_persistence
```

The production command regressions include final-read commission issuer/rate
changes that leave the cash reward unchanged, and changes to captured vessel
supplies or maximum strength. Each rejection preserves all participating
authority after the external change. The readiness manifest references these
production command tests instead of the former caller-validated prize fixtures.
Persistence fixtures include a literal supported piracy v1 history and the
current required `partyLocations` field; production schema validation is intact.

Release status remains `blocked_pending_real_forsaken_kingdom_launch_smoke`.
This evidence does not claim native Warcraft launch or gameplay validation and
requires no incremental player QA. The outer worker still performs authoritative
repository validation.
