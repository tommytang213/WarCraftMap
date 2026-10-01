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
