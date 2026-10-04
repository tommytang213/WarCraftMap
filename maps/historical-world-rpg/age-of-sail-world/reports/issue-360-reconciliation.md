# Issue 360 late-audit reconciliation

Examined baseline `69563f79d9104b36ff7d5634bc82ad808fe51818`, #359 implementation
`65b662c`, and merge `0a5626a`. The #359 change is preserved: it isolates the selector
dependency graph, strips the optional HM3W wrapper, validates supported W3I layouts
independently, budgets compiled Lua, and checks the compiled destination-selection
effect before `EndGame`, including the inlined `bj_changeLevelMapName` assignment.
Format/editor/game-version labels are recorded but are not
treated as compatibility proof. The static source/runtime coverage report remains
named as heuristic evidence; compiled-map inspection and release-archive inspection are
separate evidence levels.

This reconciliation removes the bootstrap early return from physical-map inspection, so
metadata, terrain dimensions, pathing dimensions, object structure, localized identity,
and budgets apply to the selector too. Bootstrap-specific expectations remain minimal.
It also changes the downloadable workflow to build the release candidate twice through
the dedicated verifier, inspect the finished ZIP, and upload that exact ZIP together with
an evidence record containing its byte count, SHA-256, and the checked-out source revision.
The revision is also checked against both embedded release metadata files before upload.

Regression coverage includes identical malformed canonical/packaged W3I rejection,
bootstrap structural-bypass rejection, compiled inlined native handoff checks, bootstrap
localization independent of global registrations, and workflow ordering/digest/revision
binding. Existing generated terrain, settlement, diplomacy, trade, RPG, religion, piracy,
and save inputs were not changed.

Automated checks provide structural and headless evidence, not a successful live-client
launch. The supplied log has no exception or stack trace and no removal-control result is
claimed. No Windows dump/export was available here. Status remains
`blocked_pending_real_forsaken_kingdom_launch_smoke` for the user's live Forsaken Kingdom
3.0.0.24268 installation with Traditional Chinese UI; no substitute client or language
change is treated as proof.

Local validation on 2026-10-04: 40 CI-artifact, runtime-acceptance, and campaign-
packaging tests passed; 18 release-blocker, map-source, and release-save tests passed;
Python compilation and `git diff --check` passed. A native pinned-Wurst/Grill release
build and Windows client smoke were not available in this environment and remain for the
outer validator and separately tracked real-client evidence respectively.

PR #362 CI follow-up: run `37186061238` reached the built-map gate and demonstrated
that the pinned compiler emits W3I 31 metadata and optimized away the
`SetNextLevelBJ` helper name. Follow-up run `37191000507` showed the remaining exact
forms: W3I 31 omits the forced-camera-zoom fields introduced in v32, and the compiler
can preserve the destination effect as the `SetNextLevel` native. The repair accepts
W3I 31/33 only through their version-specific parsed layouts (including player/force
records and terrain-dimension agreement), and traces `SetNextLevel`, `SetNextLevelBJ`,
or the actual compiled `bj_changeLevelMapName` assignment rather than mistaking a
renamed or inlined helper for a lost handoff.

Runs `37193984729` and `37193987235` then exposed two final gate issues. The BJ
wrapper disappeared from the compiled selector because the optimizer can inline its
destination assignment; the source retains the pinned standard library's supported
`SetNextLevelBJ` call and the compiled-effect checks accept either representation.
Also, W3I playable dimensions are not raw terrain dimensions: the canonical map is
52 by 52 inside 64 by 64 terrain after its `(6, 6, 4, 8)` camera-bound complements.
The cross-file check now parses and validates those nonnegative complements and proves
`playable = terrain - margins`; it no longer rejects the valid canonical layout.
The corrected targeted suite passed locally. The prior pinned-Wurst failure from a
direct `SetNextLevel` call was repaired by restoring the supported wrapper; a complete
pinned-Wurst rerun remains for the outer validator.

Final worktree reconciliation (2026-10-04) also examined #359 checkpoint `539089c`
and the existing #360 implementation/repairs `ba173cc`, `46c38e5`, `aceaa94`, and
`239de71`. Existing fixes were retained. The remaining upload-boundary omission
was that `verify_release_archive()` checked campaign checksums but did not rerun
`verify_campaign_runtime()` on the extracted final ZIP payload. It now does so;
consistent checksums alone cannot bypass the nested-map checks. The upload verifier
then records the digest of that checked ZIP and requires both embedded revisions
to match CI's checked-out revision.

| Late requirement | Implementation and regression evidence |
| --- | --- |
| 1. Actual upload path | `.github/workflows/map-build.yml` runs `package_release_candidate.sh` and `verify_ci_release_artifact.py` before upload. `test_ci_artifact.py` checks ordering; `test_release_upload_verification.py` exercises extracted-payload rejection, exact digest/size, and revision mismatch rejection. |
| 2. Independent W3I validation | `runtime_acceptance.inspect_built_map()` calls `forsaken_kingdom_map.validate_w3i_structure()` and compares playable dimensions plus margins to terrain. `test_runtime_acceptance.py` rejects identical malformed source/output metadata. |
| 3. Bootstrap structure | `_shared/tooling/package_wurst_campaign._inspect_physical_map()` no longer returns early; final release runtime inspection also parses bootstrap W3I and cross-file dimensions. `test_campaign_packaging.py` covers the bypass regression. |
| 4. Evidence levels | Compiled-script results now explicitly say `compiled_text_static_heuristic`; call counts are named `callNameMatches`. Bootstrap inspection ignores comments and quoted strings, with regression coverage. These checks do not execute Lua or prove control-flow reachability. Headless save/packaging tests are separate evidence. |
| 5. Corrected diagnosis | Version-specific W3I 31/33 layout tests retain acceptance of a zero game-version tuple. Bootstrap tests accept the BJ helper, native, or inlined destination assignment and reject missing effects. Textual ordering remains a heuristic, not execution tracing. |
| 6. Localization and budgets | `verify_campaign_runtime()` inspects each actual nested map through `inspect_built_map()`; bootstrap Lua size/global-registration checks are independent of localized JSON. Existing generated-localization and deterministic campaign-packaging tests are retained. No scenario/gameplay/save schema changes were made. |

No uploaded GitHub artifact was downloaded or live-client smoke result obtained in
this pass. Historical CI observations above are retained from the earlier checked-in
report, not newly reproduced results. Docker socket access was denied and native
Grill is absent, so pinned Wurst compilation and a full real release build remain
unexecuted here. The outer repository validator must supply that evidence. The
release status remains `blocked_pending_real_forsaken_kingdom_launch_smoke`.

Validation performed for this final pass: 56 targeted unittest cases passed
(`test_runtime_acceptance`: 14; `test_campaign_packaging`: 23;
`test_ci_artifact`: 4; `test_release_upload_verification`: 2;
`test_release_save_compatibility`: 6; `test_release_blocker_audit`: 7).
`validate_world.py`, `validate_map_source.py`, `runtime_acceptance.py`, Python
compilation of changed modules, and `git diff --check` passed. Packaging tests use
the fixture compiler and are not a Wurst compilation claim. The native-save
reconstruction oracle passed; actual native execution explicitly returned
`runtime_unavailable` because `WC3_NATIVE_SAVE_RUNNER` is unset. Broad unittest
discovery was interrupted after targeted validation completed; no full-suite pass
is claimed. No new artifact digest is reported because no actual release was
built/uploaded in this environment.
