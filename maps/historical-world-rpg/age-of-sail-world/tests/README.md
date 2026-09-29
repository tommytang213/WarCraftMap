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
