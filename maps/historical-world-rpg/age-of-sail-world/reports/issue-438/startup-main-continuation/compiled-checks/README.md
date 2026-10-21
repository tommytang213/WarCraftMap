# PR #536 integrated continuation: compiled verification preparation

These scripts are prepared for the main agent to execute **after the full Wurst JVM finishes**. Preparation and static review are not execution evidence. No native Warcraft result follows from these developer models, and no player release candidate is produced here.

## Source comparison

Both Europe variants use the clean integrated commit `d6697380d979f96b2f3543593c6383402ba26e5b`, source-tree SHA-256 `d08445f912a604b5fdb43beed2ec9573904075beb2e1ed6c40771df75852be37`, and current schema 17 scenario/settings. The `revised` assembly uses the exact authored production sources. The `baseline` assembly is an **integrated-source counterfactual** that reverses only:

1. The two empty-public-encoding guards in `PlayableCampaignServices.restoreOrdinaryStartup`.
2. `tradeDecimalDigit` and its call in `tradeInteger`, restoring the previous fixed-alphabet `indexOf` expression.

The baseline is not published `99524f6`, and is not the old pre-main baseline. The clean project checkout is never edited. A literal baseline reversion patch and every compiler-input digest are retained.

The preparation step checks the complete authored inventory and source-tree hash of `../seed`, the seed already generated for the current full Wurst suite. It copies that seed's generated directory and localizes only the copy using the current Europe configuration and current packaging helpers. The upstream seed receipt may still label its preparation reference as `99524f6`; reuse is accepted only because its full source-tree hash and every authored input match the clean integrated `d669` source. No historical pre-main scenario assembly is reused.

Both compiled maps retain the same current `d669` build metadata so their map inputs are identical. For the counterfactual baseline, its receipt and reversion patch describe the actual changed compiler inputs. This metadata arrangement is developer-only and is not a distributable artifact identity.

## Execution order

Run these commands from this directory, sequentially. The compile/model entry points reject active Wurst compiler JVMs; the main agent must avoid starting another compiler concurrently.

```bash
python -B compile_europe.py prepare
python -B compile_europe.py baseline
python -B compile_europe.py revised
python -B trade_integer_differential.py
python -B compare_startup.py
python -B run_full_scale.py
```

The build uses the relocated writable `../toolchain/grill` launcher, verified compiler JAR, and retained clean pinned standard library. It invokes no dependency installer. Typecheck and build require zero exit status, their success markers, verified compiler identity, and no Java/error diagnostics. Compiler and dependency inputs must stay unchanged. Existing attempts are never overwritten.

The archive is authoritative: repository inspections validate the emitted W3X; the repository MPQ reader and pinned separately reviewed `mpyq` reader must agree on ten known members (plus authored minimap if present), including script, terrain/pathing, units, and runtime identities. Extracted `war3map.lua` must equal the compiler output. `mpyq` cannot decrypt Grill's encrypted listfile, so this is a known-member comparison, not a claim of exhaustive MPQ inventory validation.

## Frozen models and binding adjustments

The exact retained probe, late native stubs, parse-once observer Lua, full-scale roundtrip Lua, and original Python observer/full-scale runners are copied under `frozen/`, with original and copied digests verified before/after model runs. The pinned shared library is stock **Lua 5.3.6**, despite the historical probe filename mentioning Lua 5.4.

`compare_startup.py` copies the old Python observer runner and changes only its four input/output bindings (`OUT`, `EVIDENCE`, `SCRIPT`, `RECEIPT`). The retained parse-once observer is used byte-for-byte in both arms. Both compiled inputs must omit the dead `MilitarySettlementRuntime_validateSnapshot` wrapper. The old asymmetric symbol-presence check cannot apply to two current parse-once arms.

The old hardcoded **15,095,868 `SubString`** and **37,931 `StringHash`** baseline counts described a different, pre-main source comparison. They are not gates for the current schema 17 baseline. Counts are measured anew, and the revised startup must reduce `SubString` calls. The runner retains frozen-probe/observer startup call-count agreement; matching runtime/trade identities and consumed request; four ordered cache writes with exact decompressed byte equality; exactly 37 callbacks through synthetic time 1.001 seconds; and no callback errors. Startup and callback budgets remain 2 billion and 200 million sampled instructions, respectively.

`trade_integer_differential.py` loads each whole, actually archived Lua script and calls its compiled `tradeInteger` directly without `config` or `main`. It checks canonical/boundary forms, all ASCII byte values in multiple positions, Unicode and malformed UTF-8, and explicit empty/multi-character slice returns. The raw-byte and UTF-8 replacement-marker models come from the retained helper-parity probe. Additional models change only native slices whose raw result is literal `X`, leaving the alphabet-search slices unchanged. These inputs check preservation of legacy empty/multi-character `indexOf` semantics; they make no assertion about Warcraft's Unicode slicing. All compiled function objects must retain their identities. The isolated-helper safety budget remains the retained 500 million sampled instructions per state. Frozen startup stubs are not changed.

`run_full_scale.py` derives the old Python full-scale runner with exactly two substitutions: its frozen-file directory and the revised production `PlayableTrade.wurst` digest. The current build receipt exposes the old input/exit/unchanged fields so its original checks remain in force. The Lua case, native models and two-billion-per-phase budgets are unchanged. It still requires 8,422 markets, 829 stores, 829 populated provenance lots, six activation timers, all five mutation/restore stages, selection and catalogue restoration, exact captured byte equality, and unchanged compiled function identities. Missing/renamed compiled functions or changed model assumptions fail for review; the runner does not silently adapt them.

## Script and expected output inventory

| Script | Expected default output |
|---|---|
| `continuation_common.py` | Shared pinned source/tool/model bindings; no execution on import |
| `compile_europe.py prepare` | `europe-seed/seed-receipt.json`, localized `generated/`, production `compile/` |
| `compile_europe.py baseline` | `baseline/build-result.json`, `baseline-reversion.patch`, `inputs-before.json`, `inputs-after.json`, `dependency-before.json`, `typecheck.log`, `build.log`, extracted known members including `war3map.lua`, and retained compile/W3X output |
| `compile_europe.py revised` | Same receipts/logs/extractions under `revised/`, without a source reversion patch |
| `trade_integer_differential.py` | `trade-integer-differential/receipt.json`, `cases.json`, `native-slice-models.json`, eight model pairs named `<slice-model>-baseline.json` / `<slice-model>-revised.json` |
| `compare_startup.py` | `startup-comparison/comparison.json`; for each arm, `frozen/result.json`, retained trade-snapshot text, copied probe/stubs, `observer/startup-and-first-callbacks.json`, copied observer Python/Lua, four `observer/cache-write-N.txt.gz` files |
| `run_full_scale.py` | `full-scale-revised/receipt.json`, `result.json`, `execution.log`, and the exact bound Python runner `verify-trade-full-scale.py` |

Each failed stage preserves its own receipt/logs and any partial outputs. A missing or failed expected output remains a failure. Previous focused/negative/full test attempts in the parent continuation directory remain untouched. `preparation-manifest.json` identifies the scripts/frozen input copies and records preparation-only status. `static-review.json` is a source review, not a model-execution result.

## Acceptance boundary

The retained models use typed synthetic units and successful in-memory game-cache writes. Synthetic orders record targets and report success; they do not execute movement. These checks cannot prove that Austria → Victory → Continue loads terrain or produces a controllable unit in Warcraft. Keep PR #536 draft/unmerged and issue #438 unresolved until the existing native acceptance and approval requirements are satisfied. Do not request an incremental player test from these scripts.
