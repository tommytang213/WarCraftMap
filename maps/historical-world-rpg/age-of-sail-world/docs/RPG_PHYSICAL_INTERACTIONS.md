# RPG physical interactions

`/interact LOCATION` and `/turnin QUEST HERO` treat their arguments as requested
targets. `WarcraftRpgRuntime` resolves a recruited, non-incapacitated field hero
through `InteractionActors`, then resolves the target through the shared
`PhysicalInteractionContext`. Warcraft observations require a living, visible,
unloaded unit owned by the command sender. Native movement types are translated
in `WC3Compatibility`.

`CampaignInteractionMaps` requires a stable campaign, an established player
identity, and agreement between the loaded physical map and the party's physical
map. Command-region selection, hero administrative assignments, discovered maps,
and tracked quest markers do not supply physical presence. Both mutation entry
points resolve the context again immediately before committing; no authorization
or actor coordinate is cached or saved.

The generated location catalogue is shared as immutable definition data. Each
runtime retains its own actor and campaign-map boundaries; reconstruction does
not copy or reuse a prior presence check.

`physical_interactions.py` generates settlement points with the same placement
function used by the map materializer and origin startup. Settlement-linked quest
locations are aliases of those points. All settlements, including abstract minor
communities, have stable interaction records independent of building handles.
Point interactions require a compatible actor within 256 Warcraft world units
(two terrain cells). Region clues require presence inside that region's generated
layout on the loaded physical chapter.

Treasure candidates use their authored instance, position and accessibility, the
physical-map manifest, and deterministic compatible terrain placement. Authored
navigation definitions constrain movement where present; descriptive zone IDs
without navigation definitions cannot override the materialized terrain.
Candidate points avoid settlement and other candidate cells. The existing
resolved candidate ID and clue/completion requirements remain authoritative.
An unknown, incompatible, unresolved, exhausted or insufficiently understood
treasure target grants nothing; failed inventory grants do not consume treasure.

Turn-in requires the named reward recipient at the authored turn-in destination.
An interaction that automatically turns in a quest rewards its validated local
actor. Trusted combat/settlement notifications can progress objectives but cannot
collect treasure or turn in quests. Rejected local requests do not refill unrelated
quest offers or change any persistent state.

Location records and runtime observations are derived definitions/projections.
Campaign and RPG save schemas are unchanged. After reconstruction, each command
checks the new live representation and physical context again.

`RpgInteractionTests.wurst` exercises registry dispatch with recording actor, map
and output boundaries, production map authority, generated targets, complete campaign
snapshot rejection checks, and production codec reconstruction.
Coordinate changes, disappearing actors and physical-map changes between initial
resolution and commit are rejected with the same complete authority snapshot.
`test_rpg_interactions.py` compares generated locations with materialized maps and
checks candidate placement and invalid definitions. The startup suite verifies
that production registration installs the map boundary before campaign activation.

Release status remains `blocked_pending_real_forsaken_kingdom_launch_smoke`.
