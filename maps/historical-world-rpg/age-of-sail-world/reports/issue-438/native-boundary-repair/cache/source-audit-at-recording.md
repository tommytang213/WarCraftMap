# Native game-cache transaction audit

## Scope and conclusion

The delivered PR536 source revision was
`a1b43969eb57de4127b005956823d6b876a86068`; the reported campaign digest was
`9ea9a0e554fe70f6c85ca99c12718bb867d83658cad36635b39bc20dfd3ea742`.
The owner reported an unresponsive Warcraft window after Continue, with no
terrain or units visible. The elapsed time is unknown. This audit does not
establish a permanent deadlock, crash, or the engine phase reached.

An independent, definite persistence defect was reproduced in the exact
archived destination Lua: `StoreString=false` followed by
`SaveGameCache=true` made the actual compiled `writeTransactional` return
`true`, even though the requested slot was absent. This is a false success
result. It does **not** establish the cause of the unresponsive window.

The local code correction now checks the native string-write result, verifies
presence and the exact in-memory payload before saving, and verifies it again
after a successful save before returning success. Failed writes take a checked
rollback path. It never saves a rollback buffer that failed to restore the
previous presence/value, and never reports successful restoration if the
rollback save or subsequent readback fails. Cache readback is an in-memory API
check; it is not proof of disk durability or later-process reopen success.

No save schema, payload format, namespace, key, handoff ordering, score-screen
setting, or archive was changed. No payload chunking or unverified size limit
was introduced. This audit and its tests run locally without a Warcraft client.

## Reproduction bound to the actual delivered Lua

Files:

- `cache-write-fault-probe.py`: stock Lua 5.3 runner with an explicit input SHA,
  a 100,000 sampled-instruction safety budget, and no production-function overrides.
- `cache-write-fault-probe.lua`: five explicit game-cache native stubs; calls
  only the compiled global bootstrap, storage constructor, transaction, and diagnostic.
- `legacy-false-success-result.json`: completed result, including input hashes.

The compiled script SHA256 is
`a4fc97bb27b36466bc62bad74605128258c6847c4f46791efe2df184c3f85a45`.
The observed result was `returned=true`, `stored=false`, an empty diagnostic,
one `StoreString`, one `SaveGameCache`, and 25,000 sampled instructions.
Neither `config()` nor `main()` was called. Runtime: stock Lua 5.3.6 library;
native Warcraft status: `not_run`.

Command used from `/workspace/scratch/243ebc79fa0a`:

```sh
python3 -B validation-536/native-boundary-audit/cache-write-fault-probe.py \
  --lua-path validation-536/startup-candidate/extracted/europe_central_east/war3map.lua \
  --expected-sha256 a4fc97bb27b36466bc62bad74605128258c6847c4f46791efe2df184c3f85a45 \
  --library validation-536/lua53-runtime/liblua5.3.6-probe.so \
  --expect legacy-false-success \
  --report validation-536/native-boundary-audit/legacy-false-success-result.json
```

The runner refuses to overwrite an existing result. A repeat must select a new
report path. Its `--expect rejected-write` mode is available for a future actual
compiled script, with that script's explicit digest. No new compiled campaign
has been built or claimed as part of this narrow fix.

## Source correction and focused regressions

Only these repository files are owned by this correction:

- `maps/historical-world-rpg/_shared/wurst/WC3Compatibility.wurst`:
  `compatStoreString` returns the native boolean.
- `maps/historical-world-rpg/_shared/wurst/CampaignSaveManager.wurst`:
  `WarcraftCampaignSaveStorage` checks both write and save boundaries, verifies
  readback, and handles rollback failures explicitly. The three native boundary
  methods are overridable so interpreter tests execute this production
  transaction through controlled native outcomes.
- `maps/historical-world-rpg/age-of-sail-world/wurst/WarcraftCampaignSaveStorageTests.wurst`:
  twelve fault-oriented tests.

The test cases cover:

1. Exact successful new/overwritten values, including a present empty string.
2. Rejected string writes for absent/existing slots, and a successful later retry.
3. A native that returns false but changes the cached value.
4. A native that returns true with truncated readback.
5. A failed commit of an existing slot, including simulated partial persistence.
6. A failed commit of an absent slot, including simulated partial persistence.
7. Rejected rollback writes.
8. Truncated rollback writes.
9. Failed rollback commits.
10. Failed rollback removal of a newly introduced slot.
11. Changed readback after a purportedly successful commit.
12. Changed readback after a purportedly successful rollback commit.

The unchanged pinned interpreter gate passed **15/15**: these twelve plus the
three existing `CampaignSaveManagerTests`. The fixed 20-second per-test limit
and the release gate were unchanged. The source/test and dependency input
hashes remained unchanged during execution. Evidence is under
`cache-focused-tests-attempt2/`: `results.json`, `execution.log`, and
`focused-context.json`. The runner is `run-cache-tests.py`.

The first preparation attempt, retained under `cache-focused-tests/`, omitted
the generated `ScenarioSettings`, `ScenarioData`, and `ConformanceData`
packages. It stopped at compilation with 0/15 tests executed. The corrected
assembly retained and hashed those three generated packages from the existing
compile fixture before replacing authored inputs. That initial failure was
not a production transaction assertion failure; its report and transcript
were not replaced.

## Handoff and residual engine-boundary findings

The actual archived selector unpauses before calling its single
`ChangeLevel(mapPath, true)`. In the actual selector Lua the unpause is at line
2452 and ChangeLevel at line 5118. There are no selector calls to `SaveGame`,
`LoadGame`, `EndGame`, or `SetNextLevel`. The code therefore provides no support
for a left-paused explanation or a speculative score-screen toggle.

The destination runs campaign initialization synchronously from `main()`.
Its two storage namespaces share the same `InitGameCache` handle. In an
ordinary fresh Austria handoff it writes the startup checkpoint, session slot,
milestone slot, and consumed request before startup completes. The independent
observer retained these payload sizes from the actual final compiled Lua:

| Mission | Key | Bytes supplied to StoreString |
| --- | --- | ---: |
| bootstrap | campaign_start_1 | 1,067,493 |
| campaign | session_start | 1,067,491 |
| campaign | major_milestone | 1,067,492 |
| bootstrap | request | 70 |
| Total | | 3,202,546 |

Each write was followed by `SaveGameCache` in that observed baseline path.
Payload records are in `startup-observer/startup-and-first-callbacks.json`.
Those strings are produced under explicit stubs, including collision-free
`StringHash`; their envelope checksums are not asserted to be retail engine
bytes. No supported native string-size limit has been established here.

The previous successful probes use an initially fresh cache. Real
`InitGameCache` can read a persistent campaign-profile cache, while successive
selections retain sequence-keyed `campaign_start_<sequence>` checkpoints.
The tested source has no checkpoint cleanup path. This leaves retained-cache
startup and repeated synchronous native save cost unmodeled by the fresh
in-memory probe. It is a developer-side discriminator, not evidence that this
owner's cache has a particular contents or size.

The peer's startup profiling also identifies millions of engine string-native
calls inside non-yielding initialization. Local Lua stub timing and a local
instruction safety cap cannot establish Warcraft's native duration or limit.
Actual native phase observation remains necessary to distinguish expensive
startup/native cache work from an engine transition failure. This audit neither
asks the player for logs nor represents its pure-Lua/interpreter checks as
native acceptance.
