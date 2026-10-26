# Trade startup investigation and compiled-Lua scale regression

This directory preserves local developer evidence for the trade snapshot change
after the owner reported a black screen in the `g54911ca` campaign following
Austria selection, Victory and Continue. **Native resolution is not established.**
The archived destination runs here in stock Lua with explicit native stubs.
No Warcraft client, DevBox or remote VM was used for these checks.

## Exact source comparison

The baseline is revision `54911cabe2a993b22f3a5d05b549df5dc3995c9c`.
The focused destination compile changed only `PlayableTrade.wurst` among its
Wurst inputs. `build-result.json` and `inputs-before-typecheck.json` retain the
compiler/input receipts. The compiler JAR is pinned to SHA-256
`1f3ae40b1018b8757867515596adfa69113ca85f390c1b353cc8b69cf8944145`.

| Input | SHA-256 |
|---|---|
| Baseline `PlayableTrade.wurst` | `d3ece1f1cacc7c56d6f41d65e41b927991c50d565f8dceb32d2c232dcef1cd5b` |
| Optimized `PlayableTrade.wurst` | `0730e299ae8fa093e317bb586f7b0992dd30e8ca86082be84637653c3865ecda` |
| Baseline destination W3X | `7a52b5ef128a1ff313271754a6aeba856bb9ae5f9917fb0dff642ff9561d3364` |
| Focused destination W3X | `2bed44087117f296ad461a9572752743911662fdbacdbb823733e7d55abcd9d7` |
| Baseline archived Lua, 16,032,718 bytes | `91bd25f29ae4bd89347bb426d3557ce8144bd77f1bbaeaad635f74ccb99e2ac7` |
| Focused archived Lua, 16,097,583 bytes | `a4fc97bb27b36466bc62bad74605128258c6847c4f46791efe2df184c3f85a45` |

The focused W3X retains baseline metadata. It is a disposable developer compile,
not a distribution artifact. Generated map binaries and compiled scripts are
not vendored here.

All four frozen startup probes used the same Python harness, typed native stubs,
fresh Austria request and 2,000,000,000 sampled instruction safety budget. Their
raw JSON is retained in deterministic gzip files. The unchanged comparison JSON
binds the source, archives, scripts and original report hashes.

| Stock runtime | Baseline result | Optimized result | Optimized sampled instructions | Optimized local wall seconds |
|---|---|---|---:|---:|
| Lua 5.4 | Budget exhausted in market validation at row 299 of 8,422 | `main()` completed under stubs | 1,099,290,000 | 17.8532 |
| Lua 5.3.6 | Budget exhausted in market validation at row 290 of 8,422 | `main()` completed under stubs | 1,110,460,000 | 17.0863 |

In each optimized run, campaign startup returned true, the Austria request became
consumed, 206 synthetic units existed and six timers were registered. No timer
callback was executed. Both runs used 8,422 markets, 829 stores, 827 settlements
and 1,553 military forces. All four startup trade captures were byte-identical:
539,822 bytes, SHA-256
`051f77b5a63830900008c4abe9b5ea9a6da9c1b5f058dd5ad2cee0664368eb8d`.

The baseline did not complete startup, so these measurements do not establish a
full-startup speedup ratio. The sampled budget is a local probe safety limit,
not a Warcraft/JASS operation limit. Local wall time is not native load time.

## Executable full-scale semantic gate

`verify-trade-full-scale.py` and `full-scale-roundtrip.lua` are separate from the
frozen observational harness. They load the actual archived script, verify its
compile receipt and retain the production function objects unchanged. Debug
hooks observe startup and its successful tail return through `finishStartup`.
The script exits nonzero on missing/failed phases, budget exhaustion, wrong
counts, failed assertions or byte inequality. Its startup and roundtrip phases
have separate 2B budgets. Call/return observation adds overhead; its startup
timings must not replace the frozen comparison above.

The semantic case requires all 8,422 actual markets and 829 actual stores. It
assigns distinct balances to every market and store, chooses a permitted
registered commodity for each store through the actual `accepts` function,
and adds one positive cargo provenance lot per store. It captures and validates
the full state, clears cargo/provenance and balances, changes the selected
market/hold, reverses both catalogues, and calls the actual compiled
`reconstruct` function. It restores catalogue order and requires exact equality
of the entire capture, 829 restored lots, restored market/hold identities and
the documented clearing of transient selection flags.

`full-scale-lua53.json` records a pass under stock Lua 5.3.6. All 829 stores held
two units and one attributed lot, covering 50 goods and 750 registered origins.
The populated saved and restored captures both contain 616,819 bytes and have
SHA-256 `1b0f150a628ab521067d21a2c9438889a5c7a343b9456007980a206f4600fa9a`.
The roundtrip used 377,130,000 sampled instructions and 6.975265 seconds of local
wall time. Its separate startup observer used 132.294138 seconds; call/return
debug-hook overhead makes that time unsuitable for performance comparison.
All 2,412 compiled global function objects remained unchanged.

The retained `negative-control.py` wrapper changes only the harness budget
configuration to 10,000. `negative-control-result.json` records the expected
process exit code 1 and a startup budget failure at the next 10,000-instruction
sample (20,000 total). The raw failure report is retained unchanged. This verifies
that a failed execution does not silently pass through the runner's exit status.

The Wurst interpreter's deadline and its semantic/collision tests are maintained
separately. This directory does not claim those tests passed. Its full-scale
gate supplements their bounded fixture; it does not emulate the native engine.

## Reproduction and integrity

First run the hash verifier:

```sh
python -B verify-evidence.py
```

`manifest.json` lists each retained original path, packaged digest, and
decompressed/original digest. The four raw startup reports and compressed logs
use gzip timestamp zero and no filename header. Original receipts and frozen
Python/Lua harness files are copied byte-for-byte. Original paths are provenance
labels and may no longer exist in another workspace.

Extract `war3map.lua` and `war3map.wpm` from the hash-identified destination
archives using the repository's MPQ reader. Verify the member digests before
executing them. `archive-and-metadata.json`, `terrain-and-unit-summary.json` and
`destination-input-facts.json` retain the map facts needed by the stub model.
The baseline and focused builds use the same retained WPM, SHA-256
`7cf3b29475751ebe1d962e17651b0c42ace030b9fa2e4523cf935adf27aee0bd`.

The frozen stubs deliberately retain their original absolute WPM input path:
`/workspace/scratch/243ebc79fa0a/validation-536/startup-audit/europe_central_east/war3map.wpm`.
In this workspace the full-scale invocation is:

```sh
python -B verify-trade-full-scale.py \
  --lua-path /workspace/scratch/243ebc79fa0a/validation-536/startup-fix/europe/war3map.lua \
  --build-receipt build-result.json \
  --library /workspace/scratch/243ebc79fa0a/validation-536/lua53-runtime/liblua5.3.6-probe.so \
  --report /tmp/full-scale-lua53.json
```

For the quick failure control, run the same arguments with `negative-control.py`
and a separate report path; **exit status 1 is the expected result**. Its report
records the actual 10,000 budget. Generic default-limit prose in that raw report
describes the normal 2B mode.

The full-scale roundtrip was run once on Lua 5.3.6. For the frozen
startup comparison, copy `probe-lua54-initialization.py` and
`late-startup-stubs.lua` to an output workspace, set
`WC3_LUA_PROBE_LIBRARY`, and run the frozen CLI with
`europe_central_east --stop startup-complete --instruction-limit 2000000000
--lua-path <extracted-lua> --report-label <label>`. Its historical CLI reports
failure in JSON but does not fail its process exit code; interpret its JSON.
Use the separate full-scale runner for an executable pass/fail gate.

On a machine where the retained absolute WPM path cannot be recreated, make a
scratch derivative changing only that path to a verified extraction, record the
new stub digest and label the run as a relocated derivative. Do not alter or
relabel the frozen evidence. The exact full-scale runner deliberately rejects a
changed frozen stub digest; a relocated runner must explicitly document its
corresponding expected-digest change.

`lua53-runtime-verification.json` records the isolated stock Lua 5.3.6 build.
The [official source archive](https://www.lua.org/ftp/lua-5.3.6.tar.gz) SHA-256 is
`fc5fd69bb8736323f026672b1b7235da613d7177e72558893a0bdcd320466d60`, matching the
[published checksum](https://www.lua.org/ftp/). No system installation was used.
The [primary mapping guide](https://www.hiveworkshop.com/threads/a-comprehensive-guide-to-mapping-in-lua.341880/)
specifies Lua 5.3 and discusses Warcraft 3.0.0, but the exact embedded Lua patch
version in client build 24268 was not established. Stock 5.3.6 is not asserted
binary-equivalent to that client.

## Native boundary

The native model is explicit and narrow. Unknown natives remain undefined and
unknown native constants stop execution. `InitBlizzard` does nothing, player
slots are set to 24, `StringHash` assigns consistent collision-free IDs, and
game-cache writes always succeed in memory. Synthetic units start with life
1,000, mana 500, hero level 1, foot movement, speed 300 and no inventory or
structure flag. Orders report success without engine movement. Pathing reads
base WPM only; preplaced units, collision, footprints and coordinate adjustment
are not modeled. Timers and triggers register but never fire.

These checks establish bounded Lua-side completion and trade serialization
behavior under that model. They do not establish engine loading, rendering,
asset acceptance, transitions, disk persistence, native Lua equivalence or
resolution of the owner's black screen. Hash-collision behavior remains a
separate Wurst test responsibility because the frozen hash stub has no collisions.
