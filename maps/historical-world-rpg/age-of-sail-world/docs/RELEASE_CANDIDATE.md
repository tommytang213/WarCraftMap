# Phase 9 release candidate

Release candidate: **phase9-rc1**
Required runtime: **Warcraft III 3.0, single player, Lua campaign**

Status: **automated packaged-artifact validation complete; real-client launch smoke not run.**
The release pipeline builds every physical W3X twice, packages the W3N, and inspects
the packaged campaign rather than trusting source markers. The gate verifies campaign
metadata, bootstrap/origin flow, physical-map identities, localized terrain and pathing,
settlement and spawn representations, production registrations, transitions and arrival
transforms, and save schemas 1–5. Player QA is not required to produce this candidate.

## Install and launch

1. Close Warcraft III. Extract the release ZIP without renaming or moving files inside it.
2. Copy `Campaigns/AgeOfSailWorldCampaign.w3n` to the Warcraft III `Campaigns` folder for the player account.
3. Start Warcraft III 3.0, open **Single Player → Custom Campaigns**, select **Age of Sail: The World**, and start **Begin the Campaign**. Do not launch an individual W3X from inside the campaign container.

## Save compatibility

This candidate writes campaign save schema 5. It transactionally supports schema 1, 2,
3, 4, and 5 saves through the documented migration chain. Keep a copy of an older save
until it has loaded and been saved successfully. Saves from a newer or modified build are
not supported; a rejected save is never rewritten.

## Real-client smoke status

The Warcraft III 3.0 launch smoke is explicitly **not run** for this candidate. It remains
a separate, optional final promotion signal and does not change the completed automated
implementation/artifact result.

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
