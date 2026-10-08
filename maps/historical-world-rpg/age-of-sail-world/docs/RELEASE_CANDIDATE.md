# Phase 9 release candidate

Release candidate: **phase9-rc1 (launch-crash remediation; not promoted)**
Required runtime: **Warcraft III 3.0, single player, Lua campaign**

Status: **blocked_pending_automated_integration_and_real_forsaken_kingdom_launch_smoke**
Player-test publication requires same-revision production-path execution and
verification of the exact built campaign and every nested map. The checked-in
source-only runtime and release-blocker reports intentionally fail while that
evidence is absent. A passing general test suite, static registrations, or declared
journey coverage cannot promote a candidate.

Publication also requires zero blockers in the exhaustive
[requirement traceability report](../reports/traceability/requirements.md).
That gate currently reports unresolved requirement mappings and missing
production/artifact evidence. See [the traceability contract](REQUIREMENT_TRACEABILITY.md)
for final-W3N catalogue census, byte composition and execution requirements.

The release pipeline builds every physical W3X twice and inspects the packaged W3N.
Automated checks cover binary structure, physical-map identities, localized terrain
and pathing, settlement and spawn representations, destination data and arrival
transforms, and save schemas 1–8. Compiled script checks identify handoff calls and
registrations but do not execute them or prove control-flow reachability. Player QA
is not required to produce this candidate.

## Install and launch

1. Close Warcraft III. Extract the release ZIP without renaming or moving files inside it.
2. Copy `Campaigns/AgeOfSailWorldCampaign.w3n` to the Warcraft III `Campaigns` folder for the player account.
3. Start Warcraft III 3.0, open **Single Player → Custom Campaigns**, select **Age of Sail: The World**, and start **Begin the Campaign**. Do not launch an individual W3X from inside the campaign container.

## Save compatibility

This candidate writes campaign save schema 8. It transactionally supports schema 1, 2,
3, 4, 5, 6, 7, and 8 saves through the documented migration chain. Keep a copy of an older save
until it has loaded and been saved successfully. Saves from a newer or modified build are
not supported; a rejected save is never rewritten.

Schema 8 preserves the autosave next slot and remaining unpaused delay through
manual saves, autosaves, recovery checkpoints and map transfers. Schemas 1–7
without this metadata start at slot 1 with the configured full interval. Previously
discarded rotation and elapsed time cannot be recovered. Failed saves and rejected
loads preserve the active scheduler.

Schema 7 preserves each locally represented party member's physical map and current
coordinates in manual saves, autosaves and recovery checkpoints. A transfer arrival
is consumed once; later saves restore subsequent movement. Schemas 1–6 omitted these
coordinates. Their deterministic fallback is the saved boundary arrival, selected
origin, or recorded local settlement. Movement discarded by those saves cannot be
recovered. Blocked current locations require verified connected recovery; invalid
locations reject the load without replacing the active campaign or stored save.

Schema 6 preserves the live campaign date, fractional day, speed and scheduled-event
cursor through manual saves, autosaves, recovery checkpoints and map travel. Schemas
1–5 omitted this clock state. Their deterministic migration starts at the scenario's
configured initial date with zero fractional progress, speed 1 and all initial
scheduled occurrences pending. Discarded historical time cannot be recovered from
those saves. Migration never infers time from play duration or the current map.

## Real-client smoke status

Phase 9 RC1 crashed live Forsaken Kingdom 3.0.0.24268 before origin selection. The
replacement bootstrap is selector-only and is guarded by compiled-artifact budgets and
transition checks, but release remains blocked until that exact client passes Begin the
Campaign, origin selection, and destination handoff smoke coverage.

Issue #397 audits the actual Actions #704 payload from `5a324d7`, whose launch
crash report is `102B765A-6BDF-44E4-BEFC-2E1C09280753`. Its compiled selector
omits `InitBlizzard()` because the source main is empty. Regional placements
also encode item-table ID 0 despite having no W3I item tables, and resized maps
retain the bootstrap-sized shadow raster. The repair restores Blizzard
initialization, writes complete non-random placement records with item-table
sentinel -1, and regenerates shadows at the materialized terrain size. Final
archive inspection checks these contracts and campaign member identities.

These are reproducible packaging/startup defects, not a demonstrated native
exception diagnosis. No exception address or call stack accompanies the report
ID, and no retail client is available in the build environment. The exact cause
of the reported immediate crash therefore remains unconfirmed. A green build
does not close #397's crash-causality or real-client acceptance criteria.
Do not request another player smoke until a materially new artifact passes
integration, exhaustive requirement traceability and framework conformance.

## Historical diagnostic

The superseded `phase8-rc2` artifact used a malformed private campaign-metadata layout
and crashed Warcraft III 3.0 when Custom Campaigns was opened. That failure is retained
here as release history; rc2 is not the current candidate. Phase 9 uses the corrected v3
campaign layout and raw-MPQ W3N container validated by the packaging pipeline.

## Recovery and known limitations

Use an ordinary manual or autosave first. `/unstuck` recovers the selected eligible unit
(or the main character); `/unstuck all` handles active units in the current region.
`/god on` is an explicit last-resort protection aid. Full recovery order and support
boundaries are in `PLAYER_RECOVERY.md`.

- Campaign containers built by different StormLib/JVM versions can differ in container metadata. The verifier compares normalized content and permits no gameplay-content difference.
- Warcraft stock presentation assets can render differently between Classic and Reforged graphics; the supported gameplay target remains Warcraft III 3.0.
