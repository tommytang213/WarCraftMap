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
