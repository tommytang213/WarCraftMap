# Issue #397 launch-path repair

The repair is based on main `b2e55a173518b875cfba2715e1f48b1881b4692e`, after
the merges for #392, #393, #398, #399, #400 and #401. It preserves those gameplay
and acceptance changes. Source and scenario data remain authoritative; packed
campaigns are diagnostic build products under `_build/`.

The unchanged Actions #704 fixtures reproduce these concrete defects:

| Contract | Observed defect | Repair and regression |
| --- | --- | --- |
| Startup | All 17 compiled map entry points omit `InitBlizzard()` because their authored `main` is empty. | Initialize Blizzard state in both consumers' source maps before Wurst package initialization. Inspect the archived Lua, including when a valid intermediate script would conceal the bad payload. Reject comments, strings, local/nested entry points, conditional calls, early returns, shadowed/member calls and wrong initialization order. |
| Placement records | All 16 regional maps omit the item-table field. Their bytes decode as a reference to table 0 despite empty W3I item tables. | Write the complete v8/11 layout with item-table sentinel -1 and no randomization. Independently parse all record fields; reject the exact historical Europe West member. |
| Shadows | Nine resized maps retain the bootstrap's 65,536-byte shadow resource. | Generate the shadow raster from terrain dimensions and verify its packaged length. Replacing it with the old bootstrap raster fails acceptance. |

Fixture hashes lock the historical Lua and unit records. The campaign audit also
checks W3F v3 chapter/visibility data, all configured MPQ members, manifest map
identities, paths and checksums, nested Lua metadata, player/start data and the
direct `ChangeLevel` handoff. The independent 3.0.0.24268 W3I fixture uses v39;
the authored v33 and compiled v31 layouts are parsed according to their own
versions. No version number alone establishes client compatibility.

`validation.json` retains the initial audit and build evidence. The subsequent
`revalidation.json` records validation after hardening the archived-Lua guard.
Both distinguish source checks, Wurst interpreter execution, archive inspection
and Lua syntax checks from retail Warcraft execution.

These reproducible defects justify the repair, but do not identify the native
instruction that faulted in Blizzard report
`102B765A-6BDF-44E4-BEFC-2E1C09280753`. No exception address, call stack or retail
client execution is available here. Crash causality remains unconfirmed.
Repository validation readiness does not close that native acceptance criterion.

Release remains `blocked_pending_real_forsaken_kingdom_launch_smoke`. Exhaustive
traceability blockers also prevent player ZIP publication. Do not request another
player smoke until integration/traceability/framework closure and a materially
new, verified candidate; then the exact candidate must pass **Begin the Campaign**,
origin selection and destination handoff on Forsaken Kingdom 3.0.0.24268. No
intermediate player testing was requested.
