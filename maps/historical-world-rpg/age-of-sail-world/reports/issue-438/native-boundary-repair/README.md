# Native boundary and startup source correction

**Scope: source correction only. No new player campaign is being published from this evidence. Native transition acceptance remains unestablished.** The owner’s latest delivered campaign failed to reach visible destination gameplay. The correction below fixes a separately reproduced cache transaction defect and reduces repeated startup string work; neither finding proves the cause of the unresponsive Warcraft window.

This source evidence pack is **complete**. The terminal full suite passed **667/667 tests** with unchanged source, compiler, dependency, and toolchain inputs. `manifest.json` records the exact retained file set and hashes; the default verifier checks both file integrity and the linked results. Completion of this pack does not establish native transition success.

## Native observation and identity

`owner-native-observation.json` is an unchanged copy of the owner observation recorded at `2026-10-20T16:52:49Z`. After `/origin choose austria` → Victory → Continue, the screenshot showed a gray or ghosted Warcraft window and Windows’ “Warcraft III is not responding” dialog, with no visible terrain or controlled unit. Duration, eventual recovery, and destination Lua initialization are unknown. This does not establish a permanent deadlock or its cause.

The report was a direct response to candidate `a1b43969eb57de4127b005956823d6b876a86068`, expected campaign SHA-256 `9ea9a0e554fe70f6c85ca99c12718bb867d83658cad36635b39bc20dfd3ea742`. Its installed hash was not recollected. No screenshot bytes or private client logs are retained here.

The repaired inputs were tested as a **dirty working tree**, with baseline revision `a1b43969eb57de4127b005956823d6b876a86068` and authoritative source content SHA-256 `2f55ec1dc084ab27c1a4fde2897728035ea49f086c8fbdd3e1d1cb3aeca22d8b`. The baseline revision is not a claim that these corrected bytes were present in the delivered candidate. Reports are excluded from source identity.

## Definite cache defect and correction

The old compatibility wrapper discarded `StoreString`’s boolean result. Its transaction then acknowledged success whenever `SaveGameCache` returned true, without checking whether the exact string had been stored. The small probe in `cache/` calls the actual archived compiled storage implementation under explicit native fault stubs: `StoreString` returns false and writes nothing, while `SaveGameCache` returns true. It does not call `config`, `main`, or campaign startup, and does not replace production functions.

| Exact compiled input | Observed transaction result | Retained evidence |
| --- | --- | --- |
| Delivered destination Lua, SHA-256 `a4fc97bb27b36466bc62bad74605128258c6847c4f46791efe2df184c3f85a45` | Returned true with no stored value and an empty diagnostic | `cache/legacy-false-success-result.json` |
| Corrected isolated destination Lua, SHA-256 `dec76da8c9ba445e315237a44a6dff415c81c07109b7f3f05dab1af806db3626` | Returned false, retained the absent slot, and supplied a failure diagnostic | `compiled/cache-write-rejection.json` |

`WC3Compatibility.wurst` now returns the native store result. `CampaignSaveManager.wurst` requires a successful store, exact presence/value before commit, a successful cache commit, and exact readback before acknowledgment. Rollback checks restoration and its commit, and does not persist a buffer already known to be wrong. A rollback failure remains an explicit failure. Readback verifies the in-memory API; it is **not a disk durability or reopen guarantee**. Namespaces, keys, serialization, and save compatibility remain unchanged; no payload chunking or assumed native string cap was introduced.

The passing focused run in `cache/passed/` executed **15/15 tests**: 12 new fault cases and three existing manager tests. Cases include false stores that still mutate, true stores with truncated data, failed commits, absent and empty slots, rollback store/flush/commit failures, changed readback, and retry. The test subclass overrides only the native adapter seam and exercises the production transaction. `cache/source-review-at-recording.json` and its accompanying audit are historical receipts from before the later isolated compile; their then-current “no new compiled campaign” wording has not been rewritten.

## Repeated startup work

`PlayableCampaignRuntime.wurst` reuses semicolon offsets and actual native hash results. It preserves first-match edits, existing last-match/domain-aware reads, the original tail-relative substring operation, exact serialized bytes, and hash collisions. Offset reuse falls back when the derived suffix or lengths differ. Ephemeral lookup identifiers are not serialized. Scope is valid textual campaign input under the stated models; arbitrary malformed byte boundaries and retail native behavior are not established.

The passing focused run in `authority/passed/` executed **20/20 tests**: five new comparisons with the previous helper/checksum behavior and 15 existing runtime tests. It covers duplicate fields, embedded delimiters, malformed keys, document changes, multibyte text, and case hash collisions. The pinned compiler, unchanged test deadline, selected discovery, raw logs, and source/dependency inputs are retained.

The first setup attempts are preserved in `cache/setup-failure/` and `authority/setup-failure/`. **Neither executed any test.** The first cache assembly omitted required generated scenario packages and failed compilation. The first authority assembly had a dependency-directory case mismatch and changed compiler input files during setup. Their unmodified failure results and logs are retained; they are not production assertion failures and are not included in passing test totals.

## Baseline observer and remaining limits

`observer/baseline-incomplete/` preserves the first observer, whose startup completed but whose first recovery callback stopped because the explicit model lacked `BlzGetUnitCollisionSize`. `observer/baseline-extended/` adds a synthetic collision radius of 32 and modeled visible/nonflying units. Those defaults are not object-data measurements. Its 37 queued callbacks complete through 1.001 simulated seconds after `main` returns, with registration order breaking ties.

Both observers delegate to the actual archived destination code but use wrappers for measurements. They are not production-function-identity gates. Their native model uses collision-free synthetic hash values, successful in-memory cache operations, and no engine latency. The first three modeled save strings are 1,067,493, 1,067,491, and 1,067,492 bytes; the request is 70 bytes, totaling **3,202,546 bytes over four stores and four commits**. These are model-derived envelopes, not retail checksum bytes. Save payload bodies are omitted; their sizes and hashes remain in the raw reports.

## Corrected compiled destination

`compiled/build-result.json` binds the isolated Europe typecheck, build, independent member inspection, exact compiler-output/archive-Lua equality, unchanged input snapshots, and the three changed production source files. It is a developer artifact retaining baseline map metadata, not a distributable map or full campaign. The compiler and clean pinned dependency inputs are recorded; the complete OCI image was not run.

`compiled/comparison.json` links the terminal compiled receipts and scripts. The frozen startup probe reaches registered/started state under its original explicit model. The unchanged extended observer Lua completes all 37 callbacks through 1.001 simulated seconds. All four encoded cache payload hashes and lengths match the baseline observer byte for byte; payload bodies are not retained in this pack.

| Startup native-call observations under the same model | Baseline | Corrected |
| --- | ---: | ---: |
| `SubString` | 20,484,826 | 15,095,868 |
| `StringHash` | 3,240,256 | 37,931 |
| `StringLength` | 2,160,883 | 2,160,917 |
| `StoreString` / `SaveGameCache` | 4 / 4 | 4 / 4 |
| `GetStoredString` / `HaveStoredString` | 4 / 9 | 12 / 17 |

These are instrumented model observations, not retail engine measurements. The extra reads implement the cache acknowledgment check. The frozen probe samples 1,110,460,000 versus 1,074,550,000 instructions; the observer has its own additional measurement cost. Neither count is a Warcraft operation limit. No wall-time speedup ratio is claimed, because the later run shared its host with the interpreter suite and neither timing is native load time.

The direct compiled differential in `compiled/parity/` compares actual old/new `replaceCampaignField` output across 188 cases and 1,144 sequential edits **per slice model**, checking every resulting cached index. It compares actual checksum results under eight slice/hash model combinations, including zero, minimum signed integer, and colliding hash results. One combination also checks a full 1,067,473-byte captured body. The two slice models are raw byte slices and an explicit invalid-slice replacement marker. Malformed and partial UTF-8 cases are evidence about those two models only. The private removal function is inlined; existing Wurst lifecycle tests cover its callers. Production helper functions are not replaced in this differential.

Residual startup work—particularly roughly 15.1 million substring calls—and native uncertainty do not justify another player campaign. Cache latency and capacity, real persistence, native string behavior, map transitions, rendering, asset loading, and operating-system scheduling remain outside these models.

## Source checks and retained evidence

`source-checks/` retains the source-only report refresh and developer check summaries. Freshness maintenance preserves **30 runtime failures, 238 release blockers, and 7,004 traceability publication blockers**. The summaries record 17 launch diagnostics tests and the previously failing report-freshness regression passing. The launch test raw transcript was observed in tool output and was not copied; the receipt explicitly discloses this limitation. None of these checks is native or release acceptance.

`full-suite/` retains the **667/667** terminal result, complete discovery, original transcript, runner, and before/after input manifests. The run took 1,382.447 seconds. No test annotations, per-test deadlines, or execution gates were changed in the repository. The original gate’s receipt parser is retained byte for byte in `common/wurst_execution.py` and is reused by the standalone verifier; it checks the complete test partition and raw results rather than accepting a saved pass flag. The 5,494,379-byte transcript is retained as deterministic gzip and verified after decompression.

Exactly three generated textual test inputs are retained to reproduce the seed assembly. Their compressed and original digests are in the manifest, and their original hashes must match both compiler-input snapshots and `run-receipt.json`.

| Retained generated input | Original bytes | Gzip bytes |
| --- | ---: | ---: |
| `ScenarioData.wurst` | 3,829,175 | 382,880 |
| `ScenarioSettings.wurst` | 75,954 | 11,109 |
| `ConformanceData.wurst` | 712 | 285 |

Compile trees, map/campaign binaries, Lua runtime binaries, and compressed save payloads are intentionally omitted. Original absolute paths in receipts identify their recording locations; retained bytes are resolved through this pack’s manifest. Reproduction scripts preserve their original workspace paths and assembly requirements. The standalone verifier needs only the retained pack, and does not run a map, compiler, VM, or native client.

From this directory:

```sh
python3 -B verify-evidence.py
```

The default check verifies the exact file set, stored and decompressed digests, source bindings, test results, and native-status limits. It rejects missing terminal receipts. A pass means retained evidence is internally consistent; it does not turn an explicit native model into native gameplay proof.
