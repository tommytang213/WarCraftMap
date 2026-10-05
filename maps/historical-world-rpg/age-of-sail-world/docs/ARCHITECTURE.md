# Architecture v0.1

## Top-level model

The shared engine owns generic systems. The Age of Sail folder supplies scenario-specific data and terrain.

```text
historical-world-rpg/
├── _shared/
│   ├── engine/
│   └── tooling/
└── age-of-sail-world/
    ├── docs/
    ├── scenario/
    ├── map/
    ├── src/
    └── tests/
```

## Planned engine boundaries

```text
Engine
├── World
│   ├── Polity
│   ├── Province
│   ├── Settlement
│   ├── Ownership / Control
│   └── NavigationZone
├── Timeline
│   ├── Era
│   ├── HistoricalEvent
│   └── Institution
├── Technology
├── Economy
├── Trade
├── Diplomacy
├── Warfare
│   ├── Army
│   ├── Fleet
│   ├── Vessel
│   │   ├── Equipment / Refit
│   │   ├── Crew
│   │   ├── Experience / Veterancy
│   │   └── ServiceHistory
│   ├── Siege
│   └── CityCapture
├── Character
│   ├── Level / Progression
│   ├── Skills / Mastery
│   ├── Loyalty
│   ├── Relationship
│   ├── Traits
│   └── Assignment / PhysicalLocation
├── Inventory
│   ├── Equipment
│   ├── EquipmentSet
│   ├── Consumable / Tool
│   └── PlayerUseMerchant
├── Government
│   ├── Reputation
│   ├── Title
│   ├── LandGrant
│   └── Taxation
├── Quest
├── Save
├── Commands
├── UI
└── WC3Compatibility
```

## State authority rule

Simulation state is authoritative. Warcraft units/buildings/destructibles are runtime representations.

## Audio presentation boundary

`_shared/engine/audio_playback.py` owns deterministic, bounded playback
selection, loop ownership, fades, cooldowns, interruption, fallback, and
reconstruction. Audio is presentation state and is never authoritative campaign
state. Age of Sail catalogue and regional/context choices remain in
`scenario/audio/`; physical-map packaging localizes and embeds validated data.

This is particularly important for settlements: loss of an object instance must not silently erase a bank, quest service, city identity or ownership record.

## Scenario boundary

Age of Sail data will define, rather than hardcode into engine logic:

- polities and government naming
- provinces/states
- settlements and defense layouts
- goods and production
- player-use items, rarity/item-level/provenance data, equipment sets, and merchant inventories
- ship equipment/refits, vessel progression tuning, and service-history effects
- hero progression/mastery data and historical availability
- technology graphs and historical cost curves
- institutions
- special/national units
- historical characters
- titles/native naming
- historical events
- quests
- terrain/navigation topology
- models/assets

## Physical map partition

The authoritative world is larger than a single Warcraft terrain. Logical regions are therefore partitioned into one or more separate physical Warcraft map files rather than tiled inside one giant `.w3x`.

The currently source-controlled `map/AgeOfSailWorld.w3x/` remains a bootstrap/runtime-validation map until the multi-map campaign pipeline is complete. Final world packaging must support multiple physical maps under one single-player campaign experience.

A physical map is only the currently loaded presentation/runtime slice. Global campaign state remains authoritative outside that map: polity state, ownership/control, economy, technology, diplomacy, characters, armies/fleets, quests, discovery, and persistent settlement state survive map changes. Entering a map reconstructs locally relevant Warcraft objects from stable IDs and authoritative state.

A logical region may span multiple physical maps. Physical-map boundaries should follow practical geographic seams and preserve corresponding entry position/direction where practical. This lets the world exceed the per-map terrain ceiling without sacrificing the real-geography-first design.

Remote command of forces in another physical map is modeled as a command-context map load: the target map becomes the active runtime slice while the main character's authoritative physical location remains stored elsewhere. Returning to the character loads/reconstructs that physical map again.

## Performance rule

Strategic ownership and physically instantiated Warcraft objects are separate. Large fleets/armies may exist in simulation while only locally relevant entities are instantiated.

## Character roster and local hero instantiation

Recruited-character ownership is authoritative strategic state and is not the same
thing as physical Warcraft-object instantiation. The long-campaign design permits an
uncapped recruited strategic hero roster; heroes may be travelling with the player,
governing settlements, advising, commanding armies/fleets, or serving in other remote
assignments while retaining exactly one authoritative physical location.

Historical availability windows gate first appearance/recruitment. A successfully
recruited named hero persists beyond that window and is not removed merely because a
historical end/death date passes. Character progression is likewise persistent and
may include levels up to the scenario target of 300, core skills, profession/mastery
tracks, personal/signature progression, equipment/sets, relationships, loyalty and
Oathbound, offices/titles, command experience, quests, and other scenario-owned
tracks.

Only locally relevant recruited heroes are instantiated as Warcraft hero objects.
The initial release target is to support at least 32 simultaneously instantiated
player-side heroes in a local field group, subject to final runtime performance
validation. Raising that physical limit must not require increasing the strategic
roster cap because there is no arbitrary strategic roster cap.

Ordinary combat defeat of a recruited named hero should resolve through authoritative
wounded/incapacitated/recovery state by default rather than deleting a long-invested
character. Any permanent-death campaign rule must be explicit and scenario-controlled.

## Individual vessel authority

A fleet may contain persistent individual vessels whose authoritative state is more
specific than the shared ship archetype: stable vessel identity, installed
equipment/refits, crew/veterancy, experience, service history, damage/maintenance,
captain/admiral assignment, cargo and other persistent state. Runtime ship objects are
reconstructed from this state and must not be the sole source of vessel progression.

A ship archetype remains the reusable baseline for hull, availability and ordinary
mechanics; per-vessel state modifies that baseline within bounded compatibility and
technology rules. Inactive-region vessels remain abstract and do not require Warcraft
objects merely because they are owned or experienced.

## Persistence rule

Campaign persistence serializes authoritative simulation state, not raw references to transient Warcraft handles. Object instances are reconstructed from stable IDs/state on load where appropriate.

## Management-screen pause controller

`wurst/ManagementScreenPauseController.wurst` is the scenario-neutral runtime/UI
pause boundary. Modal management screens retain an idempotent ownership token;
the first token pauses the complete campaign and the last token restores the
pre-existing player/manual pause state. Passive UI uses the separate
`openPassiveCampaignUi` entry point and never acquires pause ownership. All
manual pause controls must use `setCampaignManuallyPaused` rather than calling
the Warcraft `PauseGame` native directly.

## Map and discovery boundary

`_shared/engine/map_discovery.py` owns scenario-neutral, authoritative location
knowledge and deterministic world/regional render models. Knowledge for regions,
settlements, landmarks, routes, boundaries, and other points of interest is
stored independently by stable ID. Approximate clues persist mutable circle or
polygon search areas and may move, shrink, split, or resolve to exact knowledge.

`scenario/maps/world-map.json` owns world layout, regional-instance assignments,
landmark geometry, and English labels. Canonical settlements, routes, and
boundaries are consumed from validated world data. The runtime map-screen
controller owns a modal pause token while either view is open; focusing changes
presentation only and cannot move units or change the physical region.
# Controller military traditions

`_shared/engine/military_tradition.py` owns controller/category experience and
derives continuous integer modifiers plus milestone effects from the separate
scenario `military-traditions.json` document. Combat systems submit validated
contribution batches instead of relying on Warcraft death events. Strategic
units retain only stable controller/category assignments; transient Warcraft
objects receive a replaceable, namespaced tradition layer from the runtime
adapter on activation or reconstruction. Campaign saves store
`militaryTraditionState`; handles and derived modifiers are reconstructed.

## Selector handoff and regional startup

The packaged selector uses `CampaignHandoff`, `CommandRouter` and the transactional
cache adapter. Its generated `ScenarioData` contains only origin records and their
physical starting coordinates. It does not import regional gameplay registration.
`OriginCatalog` is generated from the same authoritative records for the selector,
regional runtime and executable tests. Starting coordinates use the map
materializer's existing settlement placement calculation, including compressed
representations of abstract communities; military object existence is not needed
to locate the player.

Transfer reconstruction uses the loaded map's materialized player arrival point.
The last visited settlement remains history and need not have a military object
on that map. Invalid saved origins are rejected before reconstruction.

The `bootstrap` mission in `AgeOfSailCampaign.w3v` stores one versioned `request`:
`v1|sequence|pending-or-consumed|origin|map|instance|settlement`. The selector writes
that record transactionally, commits its local identity, closes the selector, then
loads the generated package path. Failed persistence leaves identity unselected.
The former four unversioned keys are read as a pending version-1 request and must
pass the same generated-record validation before use.

Regional construction only allocates services. `registerCampaignDomains` completes
generated country, trade, military, religion, piracy and RPG registrations and
attaches their authority/projection ports. Only then does `startup()` validate the
request against the generated origin tuple and the loaded `PHYSICAL_MAP_ID`, or
restore the existing transfer milestone. Founded polity bridges reconstruct before
saved country resources are applied, so registration cannot reset their treasury.
Migration defaults are captured after registration; campaign schemas 1–5 remain
supported through migration to schema 6; source saves are never rewritten on load.

A pending new request takes precedence over an unrelated milestone. After identity,
authored location and party projection succeed, startup writes a codec checkpoint
under `bootstrap/campaign_start_N`, publishes `campaign/session_start` and
`campaign/major_milestone`, then marks the request consumed. A failed publication or
acknowledgement retains the request and its sequence-bound checkpoint. Retry loads
that checkpoint rather than granting a new party or rewards again. Consumed
requests use the ordinary milestone; repeated startup on an active service is a
no-op. Both cache namespaces share one native cache handle in regional maps.

Rejected startup retains durable saves, rolls back attempted checkpoint restoration
and keeps campaign saving, simulation timers, autosaves and gameplay command activation
closed. There is no destination loader call in regional startup. Interpreter and
packaging validation do not establish native Warcraft launch success; that remains
`blocked_pending_real_forsaken_kingdom_launch_smoke`.

## Atomic campaign loads

`CampaignSaveManager` guards manual, recovery and startup checkpoint loads. Before
reconstruction, `PlayableCampaignState` validates RPG, military/settlement,
religion, piracy, diplomacy/rewards, trade and clock records. Pirate-polity reconciliation
checks territory against the candidate military snapshot and country validation
includes the candidate's founded polity, without invoking live callbacks.

Reconstruction retains a rollback checkpoint for every participating authority,
including campaign time, ordinary country registry membership and player identity. Trade owns
its checkpoint, including the selected market and cargo store. Party and military
adapters retain their previous native units until commit; rejection removes the
candidate units and restores the original handles, positions, orders and effects.
Authority rollback uses the existing domain restore boundaries and restores RPG
and religion modifier layers. The RPG projector checkpoints the equipment
contributions on retained party objects before detachment and restores that
bookkeeping after reattachment without rewriting native life. Later equipment
reconciliation or removal therefore cannot duplicate the retained bonuses. It
does not rerun pirate-polity callbacks. The authority document and command context
are published only on success.

Startup restoration keeps this transaction open through session/milestone writes
and selector acknowledgement. Publication failure rolls back live state while
retaining the sequence-bound checkpoint for retry. Load observers run only after
commit, and saves remain deferred through reconstruction and observer delivery.
The clock rolls back before date-sensitive domain effects, retaining its original
timer; successful activation restarts the timer only after commit. These checkpoints
are internal runtime state: atomic loading adds no persisted format changes, and
supported schemas 1–6 and the original source slots remain intact.

## Live campaign clock persistence

`PlayableCampaignState` and `PlayableCampaignCodec` receive the same configured
`CampaignClock` that Bootstrap installs. Campaign schema 6 requires a separate
`clock` authority field; `world=instance:...` continues to identify the regional
instance. Clock record version 2 contains the Gregorian ordinal day, next occurrence
index, fractional-day accumulator, speed and a fingerprint of the generated schedule
(including date bounds, initial date and tick rate). Binary significand/exponent
encoding preserves reals exactly; Warcraft's display-oriented R2S rounding is not
suitable for repeated save/load. Clock helper version 1 was never part of a live
campaign save format.

Decode checks the complete clock record and schedule fingerprint before mutation.
The cursor must consume every occurrence through the saved day without splitting
simultaneous occurrences or consuming future events. The pristine initial clock can
still have initial-day occurrences pending. During event delivery, reentrant clock
advancement/restoration is rejected and ordinary saves use the manager's existing
deferred-save path. A transfer cannot start until advancement is complete.

Restoration precedes RPG, military, religion, trade and party reconstruction. Regional
startup enables simulation and clock timers only after checkpoint restoration has
succeeded. Timers, listener objects and UI pause ownership are transient: manual load
restarts the attached adapter, map startup attaches a new one, and installing a
replacement clock detaches the previous timer. Repeated startup never creates a second
clock timer.

Schemas 1–5 migrate missing clocks to the scenario's configured initial day, zero
fraction, speed 1 and cursor 0, independent of the live clock at load time. Their
omitted historical time cannot be recovered. Explicit records are validated and
preserved; schema 6 rejects missing records. The generic Python save envelope also
advances to version 6 while preserving its already supported `world.clock` records;
calendar-dependent migration defaults belong to the live scenario codec.
