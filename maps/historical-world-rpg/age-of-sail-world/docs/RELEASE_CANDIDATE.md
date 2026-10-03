# Phase 8 release candidate

Release candidate: **phase8-rc2**
Required runtime: **Warcraft III 3.0, single player, Lua campaign**

Status: **BLOCKED pending rebuilt-artifact human launch and regional-map smoke test.** The rc2
campaign metadata used a malformed private layout and crashed Warcraft III 3.0
when Custom Campaigns was opened. The rebuilt artifact now uses the v3 layout
and the raw-MPQ W3N container found in an independent 3.0 fixture, but must not
be promoted until the next real-game launch confirms that the campaign list and
first chapter open, and that an ordinary regional chapter loads its materialized
terrain, pathing, settlement/port representations, and player arrival anchor.

## Install and launch

1. Close Warcraft III. Extract the release ZIP without renaming or moving files inside it.
2. Copy `Campaigns/AgeOfSailWorldCampaign.w3n` to the Warcraft III `Campaigns` folder for the player account.
3. Start Warcraft III 3.0, open **Single Player → Custom Campaigns**, select **Age of Sail: The World**, and start the first chapter. Do not launch an individual `.w3x` from inside the campaign container.

## Save compatibility

This candidate writes campaign save schema 5. It supports schema 1, 2, 3, 4, and 5 saves through the documented migration chain. Keep a copy of an older save until it has loaded and been saved successfully. Saves from a newer or modified build are not supported; a rejected save is never rewritten.

## Recovery

Use an ordinary manual or autosave first. `/unstuck` recovers the selected eligible unit (or the main character); `/unstuck all` handles active units in the current region. `/god on` is an explicit last-resort protection aid. Full safe recovery order and support boundaries are in `PLAYER_RECOVERY.md` in this package.

## Known non-blocking limitations

- This is an automated release-gate candidate; no incremental player QA is required.
- Campaign containers built by different StormLib/JVM versions can differ in container metadata. The release verifier compares normalized archive structure and content hashes and permits no gameplay-content difference.
- Warcraft stock presentation assets can render differently between Classic and Reforged graphics; the supported gameplay target remains Warcraft III 3.0.
