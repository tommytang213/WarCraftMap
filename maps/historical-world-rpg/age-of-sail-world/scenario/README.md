# Age of Sail Scenario Content

Scenario-specific content belongs here and must be replaceable by another timeline without rewriting shared engine systems.

Regional terrain sources under `terrain/` contain authoritative geography, traversal zones, declared gameplay distortions, transition anchors, and generation budgets. Generated terrain files are build outputs and must not be edited or committed.

Research content in this directory supplies scenario-specific names, dates, costs, prerequisites, and unlock IDs to the generic shared contracts.

Quest and event content likewise supplies display text, declarative condition and
outcome IDs, graph relationships, and typed world references. Executable logic
belongs in engine adapters, never in scenario data.

Planned data domains:

- polities
- provinces/states
- settlements
- defense layouts
- sea/navigation regions
- goods
- technologies
- institutions
- historical events
- characters
- native title names and generic rank mappings
- special/national units
- quests
- treasures
- starting configurations

The authoritative campaign calendar is `world/world.json.timeline`. Its 1450-01-01 through 1820-12-31 range and era labels are scenario content; the shared engine contains no Age of Sail year constants. Historical event definitions and schedules will be authored there in later content issues.

`geography/europe.json` is the editable authority for the 1450 Europe spatial slice. It defines regional instances, real-world control points, local affine transforms, paired seams, declared gameplay distortions, and complexity budgets. Run `python3 tooling/europe_geography.py` to validate it. Terrain/map inputs containing calculated local control points are deterministic derived artifacts and must not become an alternate source of truth.

`settlements/europe-1450.json` is the authority for Europe’s deliberately selected capitals, ports, trade centers, forts, transition locations, local placements, services, production references, and abstract regional representation data. Run `python3 tooling/europe_settlements.py` to validate it or add `--write` to rebuild its canonical world and economy projections.
