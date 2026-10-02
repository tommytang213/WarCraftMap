# Age of Sail Scenario Content

The release-scale settlement foundation is configured by
`settlements/release-scale-coverage.json`. `tooling/settlement_catalogue.py`
normalizes all seven 1450 regional sources through the shared contract and writes
`reports/settlement-coverage-baseline.json`. This is an inventory and target-gap
artifact, not a completed density gate. Coverage follows evidence-led importance,
not equal quotas; physical objects remain reconstructable representations of stable
records, and minor communities may be authoritative `abstract_minor` records with
an explicit compression rationale.

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

`campaign-quests.json` is the authority for the expanded regional, personal,
cross-region, campaign-spanning, and repeatable quest catalogue. It records
chains and the first campaign-spanning long chain. It owns English narrative,
objectives, branches, divergence policy, reward adapter declarations, location
precision, and explicit coverage targets. Run `python3 tooling/campaign_quests.py`;
pass `--write` to rebuild the deterministic quest and quest-location projection
in `world/world.json`. Physical traversal remains a navigation-runtime concern;
quest breadcrumbs only use transitions already known to the campaign journal.
`python3 tooling/phase8_content_coverage.py` validates the committed
region/quest-type/character/treasure coverage report; use `--write` after an
authored content change.

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

`historical-events.json` owns the currently authored 1450–1820 dated and recurring
pressure-event baseline, including English narrative/evidence, stable references,
conditions, weighted alternate outcomes, and balance values. The current catalogue is
not the final release breadth and expands under the Phase 8 density targets. Run
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

## Release-scale content authority

The regional files currently contain a validated playable baseline, not a statement
that their present row counts are the final release density. The release target in
`docs/DESIGN_LOCK.md` requires historically grounded 1450 settlement coverage at
approximately real locations and under the appropriate polity/province/control
context, with roughly 800–1,200 meaningful authored settlements globally as a planning
range. Density follows historical geography and gameplay relevance rather than equal
per-polity quotas.

The same rule applies to other content domains: existing presence/coverage is not
sufficient by itself. The reopened Phase 8 content pass expands technologies and
institutions, historical/conditional events, authored and repeatable quests,
land/naval roster variants, named historical heroes, player-use RPG inventory,
equipment sets, and individual-vessel refit/veterancy content toward the release-scale
ranges locked in `DESIGN_LOCK.md`.

Bulk commodity goods under `economy/` remain distinct from player-use RPG inventory.
A settlement may have economic stores/markets for production, cargo, pricing, and
trade while separately exposing player-use merchants such as armourers, gunsmiths,
outfitters, apothecaries, booksellers/cartographers, military suppliers, relic
merchants, ship chandlers, and dockyards. Their usable-item inventories belong to
scenario content and are resolved from local historical/economic context.

Likewise, naval archetypes under `rosters/` define reusable ship families, while
persistent owned vessels may carry individual equipment/refits, crew/veterancy,
experience, and service history. Named historical characters have initial
availability windows, but recruited characters persist as alternate-history campaign
state and use long-campaign progression rather than disappearing when that historical
window closes.

`economy/balance.json` owns the full-world long-campaign economic envelopes,
scenario modifiers, logistics tiers, source/sink policy, and soak performance
budget.  It deliberately derives settlement profiles from the historical
production, import, shortage, role, and route identities in the seven
authoritative settlement files. Run `python3 tooling/economy_balance.py`; pass
`--write` to refresh the deterministic regional and settlement balance report.

`economy/global-goods.json` is the authoritative Phase 8 commodity catalogue. It
defines stable units, runtime item identities, pricing, storage/cargo behavior,
production and consumption hooks, scarcity, regional defaults, and integration
boundaries. Settlement production/import/shortage identity remains authoritative in
the regional settlement files. Run `python3 tooling/global_goods.py`; pass `--write`
to refresh its deterministic validation and long-campaign simulation report.

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

`settlements/pacific-1450.json` is the authority for Pacific priority settlements, ports and anchorages, voyaging and trade routes, physical-map placement, capture or validated non-capturable models, settlement economies, transitions, and deterministic abstract-state projection. It references the authoritative polity and territorial IDs in `politics/pacific-1450.json`. Run `python3 tooling/pacific_content.py`; pass `--write` to rebuild canonical world and economy projections. `python3 tooling/pacific_density.py` validates the sparse-island release-density and runtime budgets and checks the deterministic reports without closing the global settlement-density roadmap item.

`politics/southeast-asia-1450.json` is the authority for Southeast Asia's 1450 polities, playable historical regions, capitals, sovereignty, preserved compressed port polities, diplomacy, and evidence. Run `python3 tooling/southeast_asia_politics.py` to validate its references and canonical world projection; pass `--write` to rebuild that projection deterministically.

`politics/pacific-1450.json` is the authority for the Pacific's 1450 island polities, chiefdoms, confederated and decentralized communities, playable island-group territories, distributed political-center exceptions, preserved compressed communities, diplomacy, and evidence. Open ocean is never territorial coverage. Run `python3 tooling/pacific_politics.py` to validate its historical, geography, navigation, hierarchy, and canonical-world references; pass `--write` to rebuild that projection deterministically.

`politics/east-asia-1450.json` and `settlements/east-asia-1450.json` are the authorities for East Asia's 1450 political baseline and the currently authored playable settlement content. The present catalogue is a validated baseline and must expand toward the release-scale historical-density target rather than remaining intentionally selective. They cover historical provinces and frontier regions, capitals and documented council/mobile courts, ports, trade corridors, transition endpoints, services, production, and abstract settlement representations. Run `python3 tooling/east_asia_politics.py` and `python3 tooling/east_asia_content.py`; pass `--write` to the content command to deterministically rebuild the canonical world and economy projections.

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

`settlements/europe-1450.json` is the authority for Europe’s currently authored capitals, ports, trade centers, forts, transition locations, local placements, services, production references, and abstract regional representation data. The current selection is a baseline, not the final release density; expansion follows historically meaningful 1450 settlement geography and map/readability constraints. Run `python3 tooling/europe_settlements.py` to validate it or add `--write` to rebuild its canonical world and economy projections.

`politics/africa-1450.json`, `geography/africa.json`, and `settlements/africa-1450.json` together provide the Africa authority for the currently authored capitals, ports, caravan centers, trade endpoints, transition locations, placement, services, and abstract representations. Current coverage is a baseline to expand according to historically meaningful 1450 density rather than a permanently focused subset. Run `python3 tooling/africa_content.py` to validate all references and topology or add `--write` to rebuild the canonical world and economy projections.

`politics/middle-east-india-1450.json` and `settlements/middle-east-india-1450.json` are the 1450 authority for the Middle East and India political baseline and release-scale settlements, ports, pilgrimage locations, caravan and ocean trade, regional entries, services, defenses, evidence, compressed communities, and deterministic abstract representations. Run `python3 tooling/middle_east_india_content.py` to validate the complete integration or add `--write` to rebuild canonical world and economy projections.

`settlements/southeast-asia-1450.json` provides the corresponding release-scale Southeast Asian riverine, mainland, straits, island-port, and anchorage network. `python3 tooling/mei_sea_density.py` validates both regional density passes and their deterministic report; this regional completion intentionally does not close the global settlement-density roadmap item.
