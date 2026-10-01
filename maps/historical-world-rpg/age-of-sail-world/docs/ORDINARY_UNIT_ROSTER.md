# Ordinary-unit and ship roster v1

`scenario/rosters/foundation.json` owns all Age of Sail names, dates, statistics,
costs, mechanics, Warcraft rawcodes, and historical evidence. The shared
`unit_roster.py` module contains only scenario-neutral validation, inheritance,
availability, roster resolution, persistence, and strategic-to-runtime
projection rules.

Every definition and reference uses a stable ID. Concrete archetypes declare a
category, movement, weapons, armor, abilities, land formations or ship hull,
strategic strength, runtime template, recruitment cost, upkeep, supply,
technology/tradition availability, and directed upgrades/replacements.
Abilities carry a validated mechanic class, covering passive and active effects,
auras, formation or weapon behavior, morale/discipline, resistance and counters,
logistics and terrain roles, boarding, and siege without engine switches for
scenario content.

Archetypes may `extends` one parent. Maps merge one level by named key; scalars
replace. Arrays are never silently combined: `inheritance.mode` must select
`replace_lists` (the default) or `append_lists`. Resolved children retain their
own ID and may supply a country ID, so shared archetypes do not erase national
identity. Cycles, missing parents, ambiguous modes, duplicate references, and
incompatible resolved definitions are rejected.

Historical start/end years define normal availability. Earlier access is only
possible from `earlyAccessYear` when every named early-access technology is
completed; normal required technologies still apply. The returned historical
modifier is data-independent and deterministic, leaving eventual scenario
balance consumers free to apply the value consistently.

Phase 8 adds `phase8-land-rosters.json`. Land definitions can declare a
validated `rosterLayer` (`common`, `regional`, `polity`, or `elite`) and one or
more ordinary battlefield `roleIds`. Shared mechanical bases cover levies,
militia, ranged and light troops, garrisons, artillery and siege trains,
engineers, marines, cavalry, and army transport/support. Regional families and
select major-power or elite formations add identity without cloning those
bases for every polity. Directed replacement chains preserve historical units
for old saves while suppressing obsolete predecessors when their replacements
are currently available.

`RosterCatalog.resolve_roster` is the common resolver for recruitment, AI
forces, settlement garrisons, and abstract military composition. Callers pass
the controller's family assignments plus the same date, technology,
institution, equipment, reform, resource, port, and polity context; no consumer
maintains a parallel roster.

`representedStrength` remains authoritative campaign state. Runtime templates
only specify strength represented per Warcraft proxy and per-unit proxy caps;
projection also accepts a global active-object cap. Inactive regions create no
objects. Snapshots contain stable IDs and scalar state only—never Warcraft
handles or derived ability modifiers. Representations and derived modifiers are
reconstructed from definitions after load, preventing duplicate persisted
effects.

Run `python3 tooling/validate_unit_roster.py`; `--output PATH` also writes a
deterministic generated-data inspection artifact.

The first country slice is
`scenario/rosters/europe-africa-middle-east-india.json`. It adds selective
European, African, Ottoman–Middle Eastern, and Indian identities while retaining
shared archetypes for ordinary formations. Its assignments, names, balance,
historical windows, requirements, and evidence are scenario-owned. Availability
can require a polity, date, technologies, institutions, equipment, reforms,
resources, and port access. Validation rejects broken gates and national units
assigned to another polity.

The second country slice is
`scenario/rosters/southeast-east-asia-pacific.json`. It adds shared and
polity-specific mainland, maritime Southeast Asian, East Asian frontier, and
Pacific island forces. Its data covers elephant and mounted forces, early and
later gunpowder formations, siege and fortress roles, riverine and amphibious
warfare, boarding vessels, island defense, and historically supported
long-distance wayfinding. Later matchlock and banner formations are date,
technology, equipment, and reform gated; they are not injected into the 1450
baseline.

The third country slice is `scenario/rosters/americas-caribbean.json`. It covers
Indigenous woodland, Arctic, Pueblo, Mesoamerican, Caribbean, Andean, Amazonian,
and southern-cone military identities. Firearms, horses, and imported cannon
are equipment-, reform-, resource-, technology-, and date-gated rather than
1450 defaults. `global-roster-families.json` supplies explicit shared-family
fallback coverage outside directly assigned rosters, and validation rejects an
orphaned polity. With all three slices integrated, the initial country-content
roster pass is complete.

Phase 8 adds `scenario/rosters/naval-expansion.json` while reusing the bounded
naval runtime templates. It broadens the catalogue across merchant, transport,
patrol, raiding, boarding, riverine, oared, cruising, line-of-battle, junk,
dhow, canoe and proa families. `scenario/naval/phase8.json` owns regional,
polity and era coverage; explicit exceptions; representative AI/abstract fleet
fixtures; defense, trade, transport, tradition, visual, audio and packaging
bindings; and object/import budgets. Regenerate its deterministic report with
`python3 tooling/validate_naval_roster.py --output
scenario/naval/reports/coverage.json`.

## Persistent individual vessels, refits, and veterancy

A ship archetype/hull defines the baseline vessel family; an owned ship is a
persistent individual campaign entity. Two vessels built from the same archetype
may diverge over time through installed equipment/refits, crew quality, experience,
captain/admiral effects, damage/maintenance state, and recorded service history.

Per-vessel refit/equipment categories should cover historically/plausibly appropriate
choices such as:

- armament and ammunition;
- hull reinforcement/protection and later hull treatments;
- rigging, sails, maneuvering, and storm handling;
- navigation, charts, surveying, and chronometry;
- cargo capacity, provisions, repair stores, and other logistics;
- crew quality, marines, boarding specialists, and gunnery organization;
- magazine/fire protection and safety;
- flagship/command facilities and other role-specific fittings.

Availability is data-driven from hull compatibility, campaign date, technologies and
institutions, polity/region, dockyard capability, resources, money, and other
authoritative state. Refitting an individual vessel must not mutate every ship of the
same archetype.

Ships accumulate persistent experience from meaningful service rather than receiving
only discrete veteran flags. Continuous veterancy bonuses must be large enough to be
noticeable in normal play while remaining bounded by hull and technology. As an
initial balance target, early meaningful experience should produce a visible
few-percent improvement; established veteran ships commonly reach roughly 10–20%
effective improvement in relevant areas; exceptionally long-lived elite/legendary
vessels may reach roughly 25–40% combined improvement across selected relevant
stats/effects. Those figures describe combined role-relevant improvement, not a flat
multiplier to every statistic.

Experience growth is role/history-sensitive. Gunnery-heavy service may improve
reload, accuracy, broadside discipline, or magazine handling; exploration/trade
service may improve navigation, storm handling, range, supply efficiency, or
maneuvering. Diminishing returns or another bounded curve prevents an obsolete hull
from defeating a vastly superior later design solely because it survived for a long
time.

Milestones such as Experienced, Veteran, Elite, Famous, and Legendary add distinctive
traits, passives, or specialization choices on top of continuous scaling. Persistent
history may record battles, defeated ships, voyages, storms survived, distance
sailed, ports visited, discoveries, commanders served under, and other notable
service. These records are authoritative campaign state and may feed names, traits,
quests, reputation, or presentation.

The existing Phase 8 naval catalogue is therefore a breadth baseline, not the final
refit catalogue. Its small weapon/equipment surface must expand during the reopened
release-content pass; ship archetype count alone does not satisfy individual-vessel
progression.

The complementary Phase 8 land roster broadens those families across all seven political
regions and the 1450, 1550, 1650, 1750, and 1820 deterministic fixtures. The
machine-readable coverage audit is in
`scenario/rosters/reports/phase8-land-coverage.json`.
