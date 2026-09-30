# Shared Historical World Engine

Reusable systems live here. This layer must not know that the first scenario is Age of Sail.

`campaign_save.py` implements the headless, scenario-independent save envelope,
slot layout, integrity checks, and migration registry. Warcraft-native storage is
deliberately deferred to the runtime integration layer.

`cross_map_persistence.py` implements versioned, integrity-protected physical-map
transfer checkpoints, manifest validation, first-visit defaults, visited-map
reconstruction, and deterministic adapter ordering. Physical-map travel triggers
remain scenario/runtime concerns.

`world_integrity.py` provides bounded stable-ID scans and transactional recovery for
scenario-declared authoritative domains. It rebuilds only derived persistence indexes
and map-local Warcraft representations; unsafe authoritative corruption is rejected
without mutation.

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

`unit_roster.py` validates scenario roster catalogs, resolves controlled
archetype inheritance, evaluates historical and technology availability, and
deterministically projects roster-instance strength into bounded local proxies.
It contains no Age of Sail content or balance values.

`quest_event.py` owns deterministic quest lifecycles, trigger ordering and
deduplication, persistent discoveries, atomic scenario outcomes, and stable saves.

Planned modules include:

- world hierarchy: polity -> province/state -> settlement
- ownership vs control
- timeline and eras
- economy, goods, trade, taxation
- diplomacy, wars, occupations and peace settlements
- characters, loyalty, relationships and Oathbound progression
- declarative character availability, deterministic alternate locations, remote
  region projection, and reconstructible physical representations
- titles, peerage, land grants, vassalage and sovereignty
- quests and historical events
- navigation zones and safe-position recovery
- campaign save/load, rolling autosaves and migrations
- command/help framework
- UI framework
- Warcraft compatibility layer

Scenario content must plug into these systems through stable data contracts.
