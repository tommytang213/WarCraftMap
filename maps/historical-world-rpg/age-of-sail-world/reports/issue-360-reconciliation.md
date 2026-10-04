# Issue 360 late-audit reconciliation

Examined failing baseline `69563f79d9104b36ff7d5634bc82ad808fe51818`, #359
checkpoint `539089c`, implementation `65b662c` and merge `0a5626a`, and #360
repairs `ba173cc`, `46c38e5`, `aceaa94`, `239de71`, `48b2475`, `e4b13ab`.
This follow-up is an uncommitted worktree change based on
`e4b13ab2e92e62f6d2f937bf0fb8dfef07810f6b`. It preserves #359's selector
isolation, HM3W handling, matching W3I layouts and compilation budgets.
Scenario content and campaign-save schemas are unchanged. Release documentation
now uses the configured `phase9-rc1` artifact ID and distinguishes compiled-text
checks from executed journeys.

## Requirements and evidence

| Requirement | Reconciliation and regression coverage |
| --- | --- |
| 1. Validate the actual upload | `map-build.yml` already calls the RC packager, copies its ZIP, then invokes `verify_ci_release_artifact.py` before upload. The verifier reopens the extracted W3N and every W3X, matches manifest/provenance revisions to `GITHUB_SHA`, and records the copied ZIP's SHA-256/size. Final inspection now also compares every nested-map manifest row with the extracted bytes and rejects duplicate/missing archive members. `test_ci_artifact.py` binds the ordering, revision, copy and upload paths; upload/runtime tests exercise the real verifier and checksum/revision rejection. |
| 2. Independent W3I structure | Reused #359's parser and the earlier #360 v31/v33 layout correction in shared `warcraft_map_info.py`, expanding structural checks; the Forsaken Kingdom fixture keeps its authoring-specific expectations. The parser checks the complete supported layout, player records, human slot 0, strings, finite coordinates and tail. Both artifact inspection paths check dimensions against terrain, independently of source equality. Tests reject identical malformed canonical/output W3I, invalid slots/controllers and truncated/trailing metadata. |
| 3. Bootstrap structure | Retained the removal of the bootstrap early return. Closed the remaining header-only W3I check in `_inspect_physical_map()` by calling the shared parser. Bootstrap still gets archive, metadata/player, terrain, pathing, dimension and object-header checks; only regional content expectations differ. The bootstrap regression includes malformed terrain/pathing layouts, metadata tail, player count/slot/controller and objects. |
| 4. Evidence levels | Source reports explicitly say `source_text_static_heuristic`; compiled call/registration matches say `compiled_text_static_heuristic` and retain metrics in the artifact report. Neither establishes Lua execution or reachability. Replaced unconditional passing client smoke journeys with `not_run`. The RC gate re-executes `release_blocker_audit.py`: the headless soak and production save serialization/loading/migration paths. Journey map/system lists remain declared metadata; route and native-save execution explicitly remain `not_run`. Binary inspection, fixture execution, Wurst execution and real-client execution remain distinct. |
| 5. Diagnosis and handoff | Retained v31/v33 layout parsing and acceptance of a zero producer game-version tuple. Earlier real compilation showed that the old BJ assignment was removed and its handoff only called `EndGame(true)`; the existing repaired `compatLoadPhysicalMap()` uses `ChangeLevel(mapPath, true)`. Tests accept renamed/inlined destination-consuming calls and reject comments, strings and an unused BJ assignment. This establishes a code defect, not the cause of the player's crash. |
| 6. Localization and budgets | The all-map binary integration fixture runs production generation/localization/materialization for all 17 maps with synthetic Lua, then reopens W3N/ZIP payloads. It rejects localized bootstrap JSON paired with unrelated renamed global registration. Separately, the retained complete Wurst campaign build passed structural, localized-data and script-budget checks with the final compiler options. Existing terrain, settlements, diplomacy, trade, RPG, religion, piracy and saves are preserved. |

## Additional omissions exposed by the full artifact path

Retained CI logs for PR 362 runs `37205593057` and `37205594801` show the
artifact jobs stopped on uniform `pacific_open_ocean_encounter` pathing;
neither artifact job uploaded a release.
The materializer now surrounds navigable encounter water with blocked void,
using the bounded encounter already specified in `scenario/geography/pacific.json`.
No islands or persistent regional content were added. Regression coverage checks
navigable center/blocked edges and reproduces rejection of the former uniform map.

The prior attempt recorded nondeterministic MPQ layout and compressed Lua
identifiers during full two-build validation. `normalized_map()` now compares
decoded members rather than container bytes. It supports the compiler's encrypted
listfile and sector/fixed-key encryption, requires complete member enumeration,
and excludes only understood container listfile/derived attributes. Unknown
attribute layouts or unlisted files fail closed. Tests vary timestamps, order,
sector size and encryption; gameplay changes still change the normalized digest.
Exact raw-byte hashes remain authoritative for the released payload.

The checked-in `wurst_run.args` retains identifiers while preserving inlining,
local optimization, object injection and stack traces. The shared assembler
copies these options and generated provenance detects changes to them; RC
provenance also includes selector sources and shared engine/tooling inputs.
No Lua change is normalized away. Retained paired bootstrap, Europe Central/East
and ocean builds have identical raw bytes within each pair; their provenance
includes the explicit options. The recorded all-map inspection below also reads
every decoded member, but does not claim a second all-map build was compared.

## Validation and retained compiler evidence

- World and canonical source validation passed. All release pre-build gates
  passed, including both performance profiles, headless soak/save fixtures,
  report freshness, assets/recovery and five release-save migration fixtures.
- In the resumed pass, full scenario discovery passed **780 tests**
  (`python3 -m unittest discover -s tests` from the scenario directory);
  automation discovery passed **64**
  (`python3 -m unittest discover -s automation/tests` from the repository root).
  These include the structural, upload, workflow, save and runtime regressions.
  Changed Python source parses successfully; `git diff --check` passed.
- The preceding attempt's retained log records a complete Wurst typecheck/build
  and final inspection passing for all 17 maps, 230 origins and 34 transitions,
  including the stricter shared W3I
  inspector and the explicit compiler options. Selector Lua is 246,051 bytes
  (limit 512 KiB); regional Lua ranges from 6,703,921 to 6,707,703 bytes
  (limit 16 MiB). All 19 normalized campaign entries were read successfully.
  Diagnostic W3N SHA-256:
  `435a872a19b27044aa695ff083d7cd3617bd24b410cf5ea09f487b078561765b`.
  This is an uncommitted local build, not an uploaded release digest.
- Pinned compiler image:
  `frotty/wurstscript@sha256:ea428badd326df6f16f5d3857f7aadc100dbaacfbdb8fbac026933ab369fbb5a`.
  Container worktree mounts were read-only; builds and ownership changes occurred
  only in container-private copies. The retained compiled bootstrap passes
  `packagePath` to `compatLoadPhysicalMap`, which emits
  `ChangeLevel(mapPath, true)`. This is inspected compiled text, not an executed
  Warcraft transition.
- The native-save reconstruction oracle passed. Actual Warcraft save execution
  returned `runtime_unavailable` because `WC3_NATIVE_SAVE_RUNNER` is unset.

The retained `grill test` comparison log records **64/73 succeeded, 9 failed** on both this
worktree and merged #359 (`git archive 0a5626a`), using identical container-private
build paths. The segment from `Running tests` to immediately before
`Finished running tests` is identical, SHA-256
`9de37eefc8c198923ee5bfcddedae35459558aa98a3dc83cbd7466ddebbd17b2`.
Failures concern diplomacy reconstruction, trade, religion overview and RPG
assertions/null-string interpreter exceptions. These are pre-existing failures,
not passing Wurst execution evidence; this repair does not change those systems.

The resumed pass independently reopened the six retained compiled W3X files
in the three representative pairs, reran the current structural/compiled-text
checks, and compared every normalized member. All passed with matching content
within each pair. World/source validation, release pre-build gates and the
native-save oracle were also rerun. Local `grill` is absent and Docker socket
access is denied in this session; fresh Wurst compilation and the complete
two-build RC run were not repeated. The compiler results above are retained
evidence, not a claim of fresh compiler execution during the resumed pass.

## Limits and release status

No successful GitHub-uploaded payload has been observed in this follow-up.
An earlier full two-build run failed on the compiler-name nondeterminism
described above. With pinned options, the recorded all-map build/inspection and
retained representative build pairs passed; a complete all-map two-build RC ZIP
remains for artifact CI/outer validation. No new release-upload digest or final
all-map determinism success is claimed.
Local compiled checks and headless fixtures do not establish live-client
playability. Native Warcraft save execution and real-client launch remain
unavailable. Compiled-text checks cannot prove control-flow reachability.

The supplied log has no exception/stack trace; the Windows event export was
empty and no dump was supplied. No crash cause is inferred from the last log
line and no removal-control test is claimed. The target remains the user's live
Forsaken Kingdom 3.0.0.24268 Windows installation with Traditional Chinese UI.
No legacy/PTR substitute or language change is treated as a fix. Release status
remains `blocked_pending_real_forsaken_kingdom_launch_smoke`, separate from
implementation completion; no repeated incremental player QA is requested.
