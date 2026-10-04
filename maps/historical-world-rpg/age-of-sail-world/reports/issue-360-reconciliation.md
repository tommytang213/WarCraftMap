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

Local validation on 2026-10-04: 39 CI-artifact, runtime-acceptance, and campaign-
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
