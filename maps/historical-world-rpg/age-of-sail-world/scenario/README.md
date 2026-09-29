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

`geography/africa.json` is the editable authority for Africa regional instances and spatial reference data. It records source coordinates, deterministic local transforms, natural seams, transition corridors, declared compression, and bounded complexity budgets. Run `python3 tooling/africa_geography.py` to validate it.

`geography/middle_east_india.json` is the editable authority for the Middle East and Indian spatial slice, including adjoining Central and Southeast Asian transitions. It records EPSG:4326 control points, compressed local transforms, paired natural seams, graph bindings, declared distortions, and per-instance complexity budgets. Run `python3 tooling/middle_east_india_geography.py` to validate it; generated local coordinates remain derived output.

`settlements/europe-1450.json` is the authority for Europe’s deliberately selected capitals, ports, trade centers, forts, transition locations, local placements, services, production references, and abstract regional representation data. Run `python3 tooling/europe_settlements.py` to validate it or add `--write` to rebuild its canonical world and economy projections.

`politics/africa-1450.json`, `geography/africa.json`, and `settlements/africa-1450.json` are the focused Africa authority for selected polities, provinces, capitals, ports, caravan centers, trade endpoints, transition locations, placement, services, and abstract representations. Run `python3 tooling/africa_content.py` to validate all references and topology or add `--write` to rebuild the canonical world and economy projections.

`politics/middle-east-india-1450.json` and `settlements/middle-east-india-1450.json` are the focused 1450 authority for the Middle East and India political baseline, settlements, ports, pilgrimage locations, caravan and ocean trade, regional entries, services, defenses, and deterministic abstract representations. Run `python3 tooling/middle_east_india_content.py` to validate the complete integration or add `--write` to rebuild canonical world and economy projections.
