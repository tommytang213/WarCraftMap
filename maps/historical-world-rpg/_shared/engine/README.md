# Shared Historical World Engine

Reusable systems live here. This layer must not know that the first scenario is Age of Sail.

`campaign_save.py` implements the headless, scenario-independent save envelope,
slot layout, integrity checks, and migration registry. Warcraft-native storage is
deliberately deferred to the runtime integration layer.

`inventory.py` implements the reusable personal inventory/equipment contract, data-driven validation, deterministic stack/pickup routing, safe overflow, and over-capacity recovery. Warcraft 3.0 inventory UI is an adapter, not state authority.

`timeline_simulation.py` provides ordered system hooks, deterministic random streams,
invariant diagnostics, and Warcraft-handle-free resumable checkpoints.

`timeline.py` provides deterministic calendar progression, era queries, scheduled/recurring event emission, stable persistence state, and a finite research-cost time query.

`technology_institutions.py` provides fixed-point polity research, graph-prerequisite
enforcement, finite ahead-of-time costs, typed stable-ID unlock events, independent
province adoption, and campaign-save snapshots.

`military.py` owns authoritative strategic units, armies, fleets, movement,
operational state, and stable-ID persistence. Warcraft objects are transient,
locally relevant representations created only through a compatibility adapter.

`quest_event.py` owns deterministic quest lifecycles, trigger ordering and
deduplication, persistent discoveries, atomic scenario outcomes, and stable saves.

Planned modules include:

- world hierarchy: polity -> province/state -> settlement
- ownership vs control
- timeline and eras
- economy, goods, trade, taxation
- diplomacy, wars, occupations and peace settlements
- characters, loyalty, relationships and Oathbound progression
- titles, peerage, land grants, vassalage and sovereignty
- quests and historical events
- navigation zones and safe-position recovery
- campaign save/load, rolling autosaves and migrations
- command/help framework
- UI framework
- Warcraft compatibility layer

Scenario content must plug into these systems through stable data contracts.
