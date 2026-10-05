# Tests

Automated and developer-side verification for the Age of Sail scenario.

Priority areas:

- data integrity
- multi-century simulation
- city capture/rebuild
- safe navigation recovery
- campaign save/load round trips
- save migrations
- technology reachability
- government/title/land transitions
- ownership vs control transitions
- economy invariants
- native Warcraft save/load regression

Player testing is a late release gate, not the routine development loop.

Execute the complete Wurst suite with the pinned toolchain from the scenario
directory:

```sh
python3 ../_shared/tooling/run_wurst_tests.py package.json
```

The same gate is required by `automation/run_checks.sh`, the Wurst workflow,
map/campaign packaging, and the RC upload verifier. See
`reports/issue-363-execution.md` for the failure classification and retained
execution evidence. Passing interpreter tests does not establish native-client
launch or gameplay success; release status remains
`blocked_pending_real_forsaken_kingdom_launch_smoke`.

The Phase 8 integrated release-blocker gate is repository controlled by
`scenario/release-blocker-gate.json`. It classifies campaign-blocking and
unclassified critical failures, runs the headless soak and production
campaign-save round-trip/migration fixtures, audits tracked reports and release
inputs, and verifies that checked-in machine/human reports are current.
Journey routes and system coverage are declared metadata; this command does
not execute physical-map transitions or native Warcraft saves:

```sh
python3 tooling/release_blocker_audit.py
```

Use `--write` only after resolving every reported campaign blocker. The command
cannot close the gate through an allowlist or severity downgrade.

Native Warcraft save/load uses `python3 tooling/run_native_save_regression.py`.
The default run executes the deterministic reconstruction oracle and reports a
clear runtime-unavailable skip. See `docs/WC3_COMPATIBILITY.md` for the pinned
3.0/Lua runner protocol and dedicated CI invocation.

Run the reusable timeline fixture command with, for example:

```sh
python3 tooling/simulate_timeline.py tests/fixtures/timeline/soak.json
```

The command accepts fixed `--seed`, `--start`, `--end`, and `--step` values,
repeatable `--checkpoint-at` values, `--resume`, `--compare-uninterrupted`, and
`--summary-out`. Output and failure diagnostics are canonical JSON.

The early Phase 5 local-battle gate is configured in
`scenario/benchmarks/local-battle.json`. Its maximum-reasonable land, naval,
and mixed profiles independently configure unit, formation, transient effect,
order, reinforcement, and represented-strength counts. The budgets are
provisional pre-content guardrails, not final target-hardware budgets. Run all
profiles headlessly with:

```sh
python3 tooling/run_local_battle_benchmark.py
```

The recording adapter uses deterministic work units as the frame/update-time
proxy. The Warcraft-facing adapter keeps unit/effect creation, order/pathing
calls, and elapsed-time measurement in `WC3Compatibility.wurst`. Benchmark
code is compile-covered but has no initializer and is not activated by the
release bootstrap.

Synthetic large-world validation runs the `small_correctness` profile in every
test pass. The documented maximum-reasonable profile contains 68,608 strategic
entities across every Phase 5 domain and runs in the dedicated stress job:

```sh
python3 tooling/run_large_world_stress.py --profile maximum_reasonable_world \
  --summary-out _build/stress/maximum-reasonable.json
```

Profiles and provisional simulation, persistence, state-size, and active-object
budgets live in `scenario/benchmarks/large-world.json`. Summaries are compact
canonical JSON; failures are capped and identify the invariant and stable ID.

Phase 7 campaign persistence stress uses the real campaign-save and cross-map
transaction managers, all rolling/recovery/manual slot types, supported schema
migrations, repeated map revisits, and normalized authority hashes. Run the
bounded CI profile with `python3 tooling/run_campaign_save_stress.py`; the
dedicated enlarged workload selects `--profile bounded_enlarged`. Finalized
save/load, serialized-size, and growth budgets are in
`scenario/benchmarks/campaign-save-stress.json`.

Final Phase 7 development and minimum-target gates live in
`scenario/benchmarks/final-budgets.json`. The manifest records workload
versions, environments, aggregation/variance policy, calibration samples, and
the retained Phase 6 archive/audio limits. Both bounded and extended CI use it:

```sh
python3 tooling/check_final_performance_budgets.py --profile development
python3 tooling/check_final_performance_budgets.py --profile minimum_target
```

The routine test suite also runs the bounded `smoke` profile from
`scenario/benchmarks/full-world-soak.json` against every configured authored
campaign source. The extended stress workflow runs the four-seed
`complete_multi_century` profile across 1450–1820. Both normal progression and
accelerated jumps execute the same logical schedule, and every run proves an
encoded checkpoint/resume path has the same normalized final state:

```sh
python3 tooling/run_full_world_soak.py --profile complete_multi_century \
  --summary-out _build/stress/full-world-multi-century.json
```

`CampaignStartupTests.wurst` executes the production selector writer, registration
order, regional consumer and campaign codec through recording cache, loader and
projection ports. It covers generated European, Asian and African origins,
including a starting settlement without a military city record; interrupted
commits/acknowledgements; invalid and consumed requests; unrelated older milestones;
and populated/legacy transfers. Physical arrival points share the map
materialization calculation, and transfers from abstract starting settlements
reconstruct without a military city object. Fixtures execute every generated
registration, then bound the authority population before exercising the lifecycle to stay within
the pinned interpreter's 20-second limit per test. No authority domain, codec step,
registration phase or lifecycle callback is replaced. Catalogue-wide and scale
checks remain separate repository gates. Packaging regressions also compare every
origin's generated coordinates with its materialized settlement and check that the
campaign chapter selects `wurst-bootstrap/Bootstrap.wurst` using the tested shared
writer.

`CampaignLoadTransactionTests.wurst` uses the production save manager, codec and
populated campaign domains with recording native boundaries. Checksummed candidates
change valid RPG/military records before an invalid religion, diplomacy, trade or
pirate-territory record. Late ordinary-polity, extension and party failures verify
complete authority and projection rollback, retained identity/command context,
no success observers, byte-identical source slots and original subsequent saves.
Reentrant saves are deferred through observer delivery. Successful retry and
repeated reconstruction verify the same projections and resources. Startup tests
also inject projection, session, milestone and acknowledgement failures while
restoring a bound checkpoint, then retry the retained selector handoff.
The equipment rollback regression executes the production Warcraft projector
through recording object identities and life writes, including later equipment
removal and reconciliation after failed loads and successful retries. Rejected loads
and aborted staged loads also restore clock day, cursor, fraction and speed, retain
the original timer, and restart it only on commit; startup failure/retry fixtures
carry a changed clock through the recoverable handoff.

`CampaignTimelineTests.wurst` executes the production clock and campaign codec with
recording listeners/timers: exact real round trips, simultaneous occurrences,
fractional ticks, large jumps, deferred saves, malformed records, inconsistent
cursors, changed generated schedules and timer reconstruction. `CampaignStartupTests`
also advances the generated production clock through all slot types and independently
constructed destination/return clocks, asserting time before party reconstruction
and timer activation. `PlayableCampaignRuntimeTests` migrates and repeatedly resaves
every supported live schema (1–6). These are interpreter lifecycle checks, not native
client launch evidence; release status remains
`blocked_pending_real_forsaken_kingdom_launch_smoke`.
