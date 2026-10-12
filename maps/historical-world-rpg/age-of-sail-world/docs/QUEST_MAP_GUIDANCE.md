# Quest map guidance

The journal lists `/showonmap QUEST` and `/track QUEST` for available exact or
regional destinations. Both open the regional map using the current incomplete
objective. Track also retains that quest for local guidance after `/map close`.
Show on Map leaves tracking unchanged. When the final objective is ready, guidance
uses the authored return destination until a separate, validated turn-in succeeds.
`/rpg-close` closes the journal; `/map close` closes the map. Each owns its own modal
pause, and closing either preserves other screens and manual pause ownership.

`QuestNavigationController` implements the exact, region-only and hidden portion
of `_shared/engine/quest_journal.py` and `CampaignMap.focus_guidance()`. Definitions
retain stable destination IDs separately from their permitted precision. An
explicitly visited settlement can upgrade broad or hidden guidance for that same
point. Unmet required clues still reject before the upgrade. General region
knowledge never identifies every settlement or hidden point within it.

Quest authorization is scoped to the focused view. It can show an otherwise
unknown region or a single exact target without altering discovery, enabling
ordinary `/map REGION` or `/map focus SETTLEMENT`, granting command rights, or
listing unrelated hidden locations. Region-only guidance carries no point. The
map uses the current text presentation; the separate frame UI in #440 is deferred.

An exact destination on both the loaded map and the party's physical map receives
a disposable local indicator at generated interaction coordinates. A remote
command map or another physical chapter of the same logical region receives no
local indicator. Markers do not move actors, issue orders, prove presence, advance
objectives or grant rewards. Stage changes, tracking changes, failure and turn-in
replace or retire obsolete markers. A Show on Map selection temporarily supplies
local guidance while its map is open; closing returns to the tracked quest.

Tracking continues to use the existing RPG journal save record. Focus and marker
handles are derived, transient state; no save version or migration is needed.
Candidate reconstruction leaves the active map and marker untouched until commit.
Committed load closes transient map ownership and derives the marker from restored
tracking and progress. Rejected loads preserve the prior marker, focus, tracking
and pause ownership. Physical transitions use the same saved authority and never
replay objective events or rewards during reconstruction.

Downstream obligations remain explicit: production quest clue acquisition, bounded
search-area rendering, discovered-transition breadcrumbs, non-settlement earned
point knowledge, the custom frame journal/map and native Warcraft launch validation.
Until search-area presentation exists, approximate actions reject without acquiring
a modal token or fabricating a point, unless already earned exact knowledge applies.
The existing headless approximate contract remains intact. This scope does not
close REQ-0284, all of ROAD-0064, or the broader release gates.

`QuestNavigationTests.wurst` dispatches production registrations, quest acceptance,
tracking, map, branch, interaction, save/load and remote-command actions through
recording native boundaries. It checks actual map-focus/local-marker calls and
unchanged authority. Quest conditions advance through validated physical visits
and matching recording domain receipts; unfinished domain adapters stay blocked.
The issue report retains pinned execution, typecheck, packaged source identity,
headless parity and framework evidence. No incremental player QA is required.
