# Live recovery (issue #414)

`registerCampaignDomains` installs `CampaignUnstuckRecovery` for the loaded
physical map. Ordinary party deployment/projection and military creation bind
namespaced stable IDs. Retirement removes entries, replacement updates one
entry, and ownership, movement type, assignment and live-handle checks run before
each command and on the one-second bootstrap sampler. Loads suspend recovery;
commit and rollback discard observations and bind the current representations.
The registry is capped at 4,128 entries (4,096 forces plus 32 active party members).
Buildings, local defenses, system objects, nonlocal/abstract forces, dead handles
and nonplayer owners cannot become recovery targets. Empty selection uses the
saved main character; an ineligible selection never substitutes that character.

The generator derives four movement rasters and explicit component-centre
anchors from each physical map's materialized terrain and playable bounds.
`RecoveryNavigation` reuses `PartyNavigation`'s row decoder. Its zone identity
includes the physical map, movement class and connected component. Decorative
water and void terrain supply no components. Fixture navigation records in
`world.json` remain contract examples; they never enroll live recovery entities
or supply physical coordinates. Packaging compares all four rasters and anchors
with the actual WPM, alongside existing boundary and party evidence.

`UnstuckRecovery` searches a 512-unit neighbourhood on a 32-unit lattice around
each target, then checks its last-safe record, then generated connected anchors.
The Warcraft adapter checks footprint topology, native movement pathing and live
unit collision. Recovery places the unit at the exact verified point so Warcraft
position nudging cannot cross components. A blocked or unknown component fails
without movement. Sampling can retain the previously proven component while a
unit occupies a blocked cell; it cannot infer connectivity from a nearby point.

Party coordinates and last-safe positions remain in `PartyLocation` v1. Recovery
updates that existing authority; save/load and boundary travel retain their
existing flows. A transfer reconstructs hints in destination coordinates and
never interprets a source-map hint on a different map.

Nested RPG schema v3 adds a single `p,mainCharacterId` record. V2 migrates to the
first recruited field member in catalogue order; v1 retains normal new-campaign
initialization. Nested military schema v5 combines settlement policy with optional
`n,forceId,mapId,movementClass,component,safeX,safeY` records. V1–v3 have no invented
safe hints: local native representations establish them through validation.
Both historical v4 layouts migrate: the recovery branch's 23-field settlements
receive policy and missing authority from definitions, while main's 26-field
settlements retain complete-authority validation. Existing hints survive either
migration; mixed settlement layouts reject. New snapshots always use v5.
Unknown, duplicate and malformed hint records are rejected before mutation.
Map/class/topology/native pathing are revalidated on import and use. Campaign
envelopes 1–8 and party location schema v1 remain supported without a new domain.

Military projection now reads `unitTypeId`, avoiding Wurst's intrinsic `typeId`
property. For old snapshots containing a class ID instead of a rawcode, a known
stable force ID recovers its unit code from the registered definition. Unknown
historical rawcodes are not guessed.

`LiveRecoveryTests.wurst` starts with generated production registration and
ordinary Warcraft party/military adapters, using interpreter unit handles and
recording native selection, movement fields and pathing. It covers selection,
four movement classes, disconnected land/water, candidate ordering, blocked
failure, ownership/stale handles, bounded replacement, malformed/legacy hints,
save/load and map travel. No recovery entity is manually seeded. Requirement
receipts cover REQ-0191.01–REQ-0202.01. Python checks independently compare every
generated physical map's recovery evidence with materialized WPM. These checks do
not claim native-client gameplay validation or require player QA.
