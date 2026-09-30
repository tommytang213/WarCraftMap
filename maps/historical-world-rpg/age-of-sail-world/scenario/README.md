# Age of Sail Scenario Content

Scenario-specific content belongs here and must be replaceable by another timeline without rewriting shared engine systems.

Regional terrain sources under `terrain/` contain authoritative geography, traversal zones, declared gameplay distortions, transition anchors, and generation budgets. Generated terrain files are build outputs and must not be edited or committed.

Research content in this directory supplies scenario-specific names, dates, costs, prerequisites, and unlock IDs to the generic shared contracts.
The authoritative catalog is `progression/catalog.json`; it also owns historical
origins, adoption requirements, diffusion tuning, conditional modifiers, evidence,
and the complete 1450 polity/province seed. Run `python3 tooling/progression_catalog.py`
to validate its graph and world projection, or add `--write` to rebuild that projection.

Quest and event content likewise supplies display text, declarative condition and
outcome IDs, graph relationships, and typed world references. Executable logic
belongs in engine adapters, never in scenario data.

`campaign-quests.json` is the authority for the initial seven regional quest
chains and the first campaign-spanning long chain. It owns English narrative,
objectives, branches, divergence policy, reward adapter declarations, location
precision, and explicit coverage targets. Run `python3 tooling/campaign_quests.py`;
pass `--write` to rebuild the deterministic quest and quest-location projection
in `world/world.json`. Physical traversal remains a navigation-runtime concern;
quest breadcrumbs only use transitions already known to the campaign journal.

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

`historical-events.json` owns the selective 1450–1820 dated and recurring pressure
catalogue, including English narrative/evidence, stable references, conditions,
weighted alternate outcomes, and balance values. Run
`python3 tooling/historical_events.py`; pass `--write` to rebuild the canonical world
event and schedule projection deterministically.
- characters (`characters/global.json` is authoritative; run
  `python3 tooling/global_characters.py`, or add `--write` to rebuild the world
  projection; availability and location remain stable-ID simulation state)
- native title names and generic rank mappings
- special/national units
- quests
- treasures
- starting configurations

`economy/balance.json` owns the full-world long-campaign economic envelopes,
scenario modifiers, logistics tiers, source/sink policy, and soak performance
budget.  It deliberately derives settlement profiles from the historical
production, import, shortage, role, and route identities in the seven
authoritative settlement files.  Run `python3 tooling/economy_balance.py`; pass
`--write` to refresh the deterministic regional and settlement balance report.

The authoritative campaign calendar is `world/world.json.timeline`. Its 1450-01-01 through 1820-12-31 range and era labels are scenario content; the shared engine contains no Age of Sail year constants. Historical event definitions and schedules will be authored there in later content issues.

Physical packaging is authored in `../physical-maps.json`. Its stable physical-map
IDs, logical-region and regional-instance assignments, generated terrain inputs,
source folder maps/manifests, package paths, per-map budgets, and bootstrap marker
are scenario data. A logical region may occur in more than one physical-map entry,
but every required regional instance is assigned exactly once so authoritative
entities are never duplicated between map-local runtime payloads.

`geography/europe.json` is the editable authority for the 1450 Europe spatial slice. It defines regional instances, real-world control points, local affine transforms, paired seams, declared gameplay distortions, and complexity budgets. Run `python3 tooling/europe_geography.py` to validate it. Terrain/map inputs containing calculated local control points are deterministic derived artifacts and must not become an alternate source of truth.

`geography/africa.json` is the editable authority for Africa regional instances and spatial reference data. It records source coordinates, deterministic local transforms, natural seams, transition corridors, declared compression, and bounded complexity budgets. Run `python3 tooling/africa_geography.py` to validate it.

`politics/africa-1450.json` is the authority for Africa’s 1450 polities, playable provinces, capitals, sovereignty, tributary relationships, and deliberately neutral conflict baseline. Run `python3 tooling/validate_africa_politics.py scenario/politics/africa-1450.json` to validate it; `build_africa_politics.py` deterministically rebuilds its canonical world projection.

`geography/middle_east_india.json` is the editable authority for the Middle East and Indian spatial slice, including adjoining Central and Southeast Asian transitions. It records EPSG:4326 control points, compressed local transforms, paired natural seams, graph bindings, declared distortions, and per-instance complexity budgets. Run `python3 tooling/middle_east_india_geography.py` to validate it; generated local coordinates remain derived output.

`geography/southeast_asia.json` is the editable authority for the Southeast Asia spatial slice and its Indian, East Asian, and Pacific transitions. It records EPSG:4326 control points, logical mainland and maritime instances, navigable-water topology, paired seams, bounded distortions, density metadata, and per-instance complexity budgets without selecting physical-map packages. Run `python3 tooling/southeast_asia_geography.py` to validate it; calculated local coordinates remain deterministic derived output.

`geography/pacific.json` is the editable authority for Pacific island, archipelago, reef, passage, anchorage, route-endpoint, and transition geography. It records EPSG:4326 control points, dateline-aware compressed transforms, paired seams, physical-map assignments, explicit direct-route and optional encounter-map policy, navigable topology, bounded distortions, and density/complexity budgets. Run `python3 tooling/pacific_geography.py` to validate it; calculated local coordinates remain deterministic derived output.

`settlements/pacific-1450.json` is the authority for Pacific priority settlements, ports and anchorages, voyaging and trade routes, physical-map placement, capture or validated non-capturable models, settlement economies, transitions, and deterministic abstract-state projection. It references the authoritative polity and territorial IDs in `politics/pacific-1450.json`. Run `python3 tooling/pacific_content.py`; pass `--write` to rebuild canonical world and economy projections.

`politics/southeast-asia-1450.json` is the authority for Southeast Asia's 1450 polities, playable historical regions, capitals, sovereignty, preserved compressed port polities, diplomacy, and evidence. Run `python3 tooling/southeast_asia_politics.py` to validate its references and canonical world projection; pass `--write` to rebuild that projection deterministically.

`politics/pacific-1450.json` is the authority for the Pacific's 1450 island polities, chiefdoms, confederated and decentralized communities, playable island-group territories, distributed political-center exceptions, preserved compressed communities, diplomacy, and evidence. Open ocean is never territorial coverage. Run `python3 tooling/pacific_politics.py` to validate its historical, geography, navigation, hierarchy, and canonical-world references; pass `--write` to rebuild that projection deterministically.

`politics/east-asia-1450.json` and `settlements/east-asia-1450.json` are the authorities for East Asia's 1450 political baseline and selective playable settlement content. They cover historical provinces and frontier regions, capitals and documented council/mobile courts, ports, trade corridors, transition endpoints, services, production, and abstract settlement representations. Run `python3 tooling/east_asia_politics.py` and `python3 tooling/east_asia_content.py`; pass `--write` to the content command to deterministically rebuild the canonical world and economy projections.

`rosters/foundation.json` is the scenario authority for the ordinary-unit and
ship roster format and representative cross-category fixtures. It deliberately
does not complete any country roster. Run `python3 tooling/validate_unit_roster.py`
to validate references, inheritance, availability, mechanics, and runtime data.
Country slices under `rosters/` add scenario-owned regional assignments and
historical evidence. `southeast-east-asia-pacific.json` owns the second slice,
including mainland, maritime, frontier, island-defense, and voyaging identities;
the combined validator checks it together with the foundation and other slices.
`europe-africa-middle-east-india.json` owns the first selective country slice,
including its regional history, assignments, statistics, requirements, and
evidence. The first slice alone does not complete the overall roster roadmap.

`settlements/europe-1450.json` is the authority for Europe’s deliberately selected capitals, ports, trade centers, forts, transition locations, local placements, services, production references, and abstract regional representation data. Run `python3 tooling/europe_settlements.py` to validate it or add `--write` to rebuild its canonical world and economy projections.

`politics/africa-1450.json`, `geography/africa.json`, and `settlements/africa-1450.json` together provide the focused Africa authority for selected capitals, ports, caravan centers, trade endpoints, transition locations, placement, services, and abstract representations. Run `python3 tooling/africa_content.py` to validate all references and topology or add `--write` to rebuild the canonical world and economy projections.

`politics/middle-east-india-1450.json` and `settlements/middle-east-india-1450.json` are the focused 1450 authority for the Middle East and India political baseline, settlements, ports, pilgrimage locations, caravan and ocean trade, regional entries, services, defenses, and deterministic abstract representations. Run `python3 tooling/middle_east_india_content.py` to validate the complete integration or add `--write` to rebuild canonical world and economy projections.
