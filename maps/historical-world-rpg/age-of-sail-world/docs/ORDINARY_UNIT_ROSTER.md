# Ordinary-unit and ship roster v1

`scenario/rosters/foundation.json` owns all Age of Sail names, dates, statistics,
costs, mechanics, Warcraft rawcodes, and historical evidence. The shared
`unit_roster.py` module contains only scenario-neutral validation, inheritance,
availability, persistence, and strategic-to-runtime projection rules. This is a
foundation catalog, not completion of any regional or country roster.

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
