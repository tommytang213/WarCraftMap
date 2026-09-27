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
