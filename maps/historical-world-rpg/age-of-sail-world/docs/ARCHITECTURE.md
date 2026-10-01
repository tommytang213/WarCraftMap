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
