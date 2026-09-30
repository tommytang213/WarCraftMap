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
│   ├── Siege
│   └── CityCapture
├── Character
│   ├── Loyalty
│   ├── Relationship
│   └── Traits
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
