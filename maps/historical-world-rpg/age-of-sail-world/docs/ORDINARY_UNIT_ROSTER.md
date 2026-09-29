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
