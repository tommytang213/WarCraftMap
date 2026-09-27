# Shared Historical World Engine

Reusable systems live here. This layer must not know that the first scenario is Age of Sail.

`campaign_save.py` implements the headless, scenario-independent save envelope,
slot layout, integrity checks, and migration registry. Warcraft-native storage is
deliberately deferred to the runtime integration layer.

`inventory.py` implements the reusable personal inventory/equipment contract, data-driven validation, deterministic stack/pickup routing, safe overflow, and over-capacity recovery. Warcraft 3.0 inventory UI is an adapter, not state authority.

`timeline_simulation.py` provides ordered system hooks, deterministic random streams,
invariant diagnostics, and Warcraft-handle-free resumable checkpoints.

Planned modules include:

- world hierarchy: polity -> province/state -> settlement
- ownership vs control
- timeline and eras
- technology and institutions
- economy, goods, trade, taxation
- diplomacy, wars, occupations and peace settlements
- armies and fleets
- characters, loyalty, relationships and Oathbound progression
- titles, peerage, land grants, vassalage and sovereignty
- quests and historical events
- navigation zones and safe-position recovery
- campaign save/load, rolling autosaves and migrations
- command/help framework
- UI framework
- Warcraft compatibility layer

Scenario content must plug into these systems through stable data contracts.
