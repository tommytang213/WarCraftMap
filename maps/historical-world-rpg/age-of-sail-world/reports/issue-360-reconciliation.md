# Issue 360 late-audit reconciliation

Examined failing baseline `69563f79d9104b36ff7d5634bc82ad808fe51818`, #359
implementation `65b662c` and merge `0a5626a`, and the existing #360 changes through
`48b2475` (`ba173cc`, `46c38e5`, `aceaa94`, `239de71`). The merged selector isolation,
HM3W handling, version-specific W3I parsing, archive checks, and budgets are retained.
No scenario content or campaign-save schema changed.

## Requirement mapping

| Late requirement | Code, regression, and artifact evidence |
| --- | --- |
| 1. Actual upload path | `.github/workflows/map-build.yml` invokes `package_release_candidate.sh`, then `verify_ci_release_artifact.py` on the copied ZIP before upload. The release verifier reopens the ZIP and runs `verify_campaign_runtime()` on the extracted W3N. The upload verifier records the exact ZIP SHA-256/size and requires both embedded revisions to equal the checked-out CI revision. `test_ci_artifact.py` and `test_release_upload_verification.py` cover ordering, extracted-payload rejection, digest/size and revision mismatch. No successful uploaded artifact from this repair has been observed. |
| 2. Independent W3I validation | `runtime_acceptance.inspect_built_map()` invokes `forsaken_kingdom_map.validate_w3i_structure()` and checks playable dimensions plus camera margins against W3E. `test_runtime_acceptance.py` rejects identically malformed canonical and packaged metadata. Source equality is not a substitute for parsing. |
| 3. Bootstrap structure | The shared packager's `_inspect_physical_map()` no longer returns early for bootstrap. The final release verifier also parses bootstrap W3I/player data and checks terrain/pathing. `test_campaign_packaging.py` covers malformed bootstrap rejection; the real compiled bootstrap passed `inspect_built_map()` locally. |
| 4. Evidence levels | Compiled checks return `compiled_text_static_heuristic`. The pinned compiler renames calls: the checker now associates source-call annotations only with actual calls to defined functions, and resolves command-registration aliases from emitted class exports. Comments and standalone diagnostic strings do not satisfy those checks. Negative regression tests cover these distinctions. This does not execute Lua or prove control-flow reachability. |
| 5. Corrected diagnosis/handoff | W3I 31/33 are parsed according to their layouts; zero game-version tuples remain allowed. Actual compilation revealed a missing destination effect, not merely a missing helper name: the handoff contained only `EndGame(true)`. `compatLoadPhysicalMap()` now uses `ChangeLevel(mapPath, true)`, which survives compilation. The gate requires the destination-consuming native, including inside renamed helpers or using an inlined destination variable; unused BJ state plus EndGame is rejected. |
| 6. Compiled localization/budgets | Final release inspection checks every nested map. Bootstrap global-registration checks recognize renamed calls independently of localized JSON. The real selector and Europe West output passed compiled budgets and structural checks. The shared materializer now resizes W3I playable dimensions and camera bounds with generated terrain, preserving margins and the remaining version-specific layout. Regression tests cover resize/reversal and malformed input. Terrain, settlement, diplomacy, trade, RPG, religion, piracy and save content are preserved. |

## PR 362 failure and repair evidence

On 2026-10-04, `gh pr checks 362` identified failed artifact runs
`37201964341` and `37201966451`; repository-validation jobs passed. Both artifact
logs ended with `bootstrap compiled Lua does not select a campaign destination`
after producing two campaigns. No release upload succeeded in those runs.

Reproducing the bootstrap with the workflow's pinned Wurst image showed that the
renamed handoff function only called `EndGame(true)`. The emitted Blizzard library
shows `SetNextLevelBJ` assigning `bj_changeLevelMapName`; its consumers invoke
`ChangeLevel`. The old adapter never called such a consumer and the compiler
removed its unused assignment. This supersedes the earlier report's assumption
that accepting an inlined BJ assignment would resolve the handoff. It establishes
a code defect, not the cause of the player's reported crash.

A real regional compile then exposed two additional omissions hidden behind the
bootstrap gate: source-name-only heuristics rejected renamed production calls,
and generated 128-by-128 terrain still had the 64-by-64 source map's W3I dimensions.
Both are repaired as described above; the regenerated regional output passes.

## Validation performed

- 69 targeted Python unittest cases passed: runtime acceptance (17), campaign
  packaging (23), CI artifact (4), upload verification (2), release-save
  compatibility (6), release-blocker audit (7), map source (5), native-save
  regression (5). Packaging fixtures are not Wurst execution evidence.
- `validate_world.py`, `validate_map_source.py`, `runtime_acceptance.py`, Python
  compilation of changed modules, and `git diff --check` passed.
- Pinned image `frotty/wurstscript@sha256:ea428badd326df6f16f5d3857f7aadc100dbaacfbdb8fbac026933ab369fbb5a`:
  Grill install, typecheck and build succeeded for the repaired bootstrap and
  Europe West map. Worktree mounts were read-only; all compiler writes occurred
  in container-private temporary copies. Temporary containers were removed.
- Independent `inspect_built_map()` passed on both resulting MPQ maps, including
  metadata, terrain/pathing, localization and compiled-script checks. Diagnostic
  W3X SHA-256 values (uncommitted worktree based on `48b2475`, not release uploads):
  bootstrap `092b0a7295649c05167a13ee749fbad00177386b239a58d250f76040d4a02792`;
  Europe West `509f6bf537492197fa240fe519cc8f4e56e197c1188959ca83bb9c8ad71669f5`.

## Limits and release status

No full all-map, two-build RC ZIP or uploaded payload was produced in this repair
pass. The outer repository validator and artifact CI must run the complete gates;
no new release digest/revision/upload agreement is claimed. Other regional maps,
full-suite discovery, native Warcraft save execution and a live-client launch were
not run here. Source annotations and registration matches remain static evidence.

The supplied player log has no exception/stack trace; the event export was empty
and no dump was supplied. No crash cause is inferred from its last line and no
removal-control result is claimed. The target remains the user's live Forsaken
Kingdom 3.0.0.24268 Windows installation with Traditional Chinese UI; no legacy/PTR
substitute or language change is treated as a fix. Release status remains
`blocked_pending_real_forsaken_kingdom_launch_smoke`, separate from implementation
completion. No repeated incremental player QA is needed for these repairs.
