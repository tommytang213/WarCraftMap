# Current catalogue adaptation after the retained count failure

The original startup comparison completed both frozen probes and both parse-once
observers, then failed its historical exact-market assertion: 8,422 was expected,
while both integrated schema-17 arms contained 8,426. Its runner, failure receipt,
outer log, raw outputs and four compressed cache payloads per arm remain unchanged.

The separate `../catalogue-cardinality.json` proof derives the current count from
the pinned authored and generated sources, independently of those runtime counts.
The base catalogue has 8,422 distinct market pairs. Twenty conditional industry
market definitions add four absent pairs: `iron_goods` in Milan, Nuremberg,
Stockholm and Vienna. The resulting exact expectations are 8,426 markets, last
market index 8,425, and the unchanged 829 stores / last store index 828.

## Prepared changes

- `compare_completed_startup.py` reads the completed outputs. It never imports
  the Lua probe or launches a compiler, observer, native model or game. It retains
  the original comparison conditions, changes only the exact market expectation,
  verifies the saved byte payloads, and binds the source proof, failed attempt,
  original input identities, prepared artifacts and independent review. Its only
  result is the fresh `../startup-comparison/comparison-current-catalogue.json`.
- `full-scale-roundtrip-current-catalogue.lua` is a fresh case copy with exactly
  seven whole-token replacements of `8422` with `8426` and nine replacements of
  `8421` with `8425`. Every other byte is unchanged. All stores, cargo, selection,
  catalogue reversal, reconstruction and exact-capture assertions remain active.
- `verify-trade-full-scale-current-catalogue.py` copies the retained runner with
  its frozen-directory and current-source bindings, an explicit path to that
  adapted case, and its one whole-token `8422` assertion changed to `8426`.
  Native stubs, the two 2-billion-instruction phase budgets, function-identity
  checks and all other assertions are unchanged.
- `run_full_scale_current_catalogue.py` binds the case, runner, current build,
  source proof, passing derived comparison and independent review. It writes a
  fresh `../full-scale-revised-current-catalogue/` directory. No full-scale case
  has been executed during this preparation.

The four `.patch` files show literal differences from the retained comparison,
full-scale wrapper, Python runner and Lua case. `preparation-transformations.json`
records the exact substitutions and original/copied identities.
`preparation-receipt.json` binds all retained inputs and new artifacts before
independent review. The scripts require a passing `static-review.json` that binds
that preparation receipt.

## Sequential commands after review and root authorization

From this directory:

```sh
python -B compare_completed_startup.py
python -B run_full_scale_current_catalogue.py
```

The second command may run only after the first has a passing receipt. Preserve
unique outer logs and stop on any failure. Do not recompile or rerun startup for
this adaptation. Both commands recheck the clean integrated source, frozen
inputs, original evidence, prepared files, proof and review.

## Output schemas and limits

The derived comparison uses format
`pr536_current_catalogue_retained_startup_comparison_v1` and successful status
`pass_under_explicit_models`. It has `modelExecutedByThisDerivation: false`, the
original failed receipt identity, cardinality proof and review bindings, retained
per-arm result identities, startup native-call deltas, sampled instructions,
runtime/trade/request identity, callback phase receipts and four ordered exact
decompressed payload comparisons.

The full-scale wrapper receipt uses format
`pr536_continuation_current_catalogue_full_scale_binding_v1`, with successful
status `pass_full_scale_roundtrip_under_explicit_stubs`. It retains the bound
runner/case identities, literal binding/count changes, comparison/proof/review
identities, process exit status and raw execution log. `result.json` retains the
original runner schema and phase/roundtrip evidence. Native status remains
`not_run`; neither synthetic model can establish terrain rendering, actual unit
movement, native save behavior or resolution of the Continue freeze.
