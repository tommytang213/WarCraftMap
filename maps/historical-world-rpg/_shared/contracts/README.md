# Shared Data Contracts

Scenario content is stored as data and compiled into the Warcraft map. Shared engine code consumes stable IDs and generic records rather than hardcoded Age-of-Sail names.

## Stable ID rules

- IDs are ASCII lowercase snake_case.
- IDs are immutable once shipped in a campaign-save-compatible release.
- Display names may change without changing IDs.
- Never derive persistence keys from translated/display text.
- Cross-references always use stable IDs.
- Removing or replacing a shipped ID requires an explicit save migration/alias.
- Scenario IDs should be descriptive and namespaced by domain through their field/context, not by repeating the scenario name.

Examples:

- polity: `england`
- province: `kent`
- settlement: `london`
- technology: `naval_ship_of_the_line`
- character: `horatio_nelson`

## Authority

Scenario files define starting/static content. Runtime simulation state defines current ownership, control, damage, prosperity, technology adoption and other mutable values.

Warcraft object handles are never persistent IDs.

## Military contract

`strategicUnits` are authoritative simulation records. A unit is either a generic
`formation` or `ship`; an `army` contains formations and a `fleet` contains ships.
Membership is expressed only through stable IDs. Officers are deliberately minimal
identity records until the separate character contract is introduced.

`representedStrength` and its scenario-defined `strengthUnitId` describe strategic
scale without implying that every represented person or vessel is spawned. The
`runtimeInstantiation` block contains only reconstructible template, state, and
object-count metadata—never Warcraft handles. An `abstract` unit must have zero
active objects; an `active` unit must have at least one.

Morale, supply, and readiness use an inclusive 0–100 scale. Ownership and current
control remain separate. Strategic ownership has no native Warcraft food field or
equivalent cap.

## Character contract

Characters use immutable stable IDs while all player-facing names, biographies,
traits, skills, professions, quests, thresholds, and consequences come from
scenario data. Loyalty and companion relationship scores use an inclusive
`-100..100` scale. Threshold records contain scenario-selected score bands and
may identify buffs, debuffs, or content unlocks without teaching the shared
contract what those effects mean.

`oathbound` is the generic permanent high-investment loyalty state. It may be
entered from `none`, but it cannot be removed or entered a second time. Runtime
systems must call the same transition rule exposed by the validator before
changing this authoritative state.

Companion relationships are unordered character pairs. A scenario may define at
most one relationship for a given pair, regardless of which character is listed
first. Warcraft object handles are not part of character state.

## Technology and institution contract

Technologies and institutions share one directed graph, so prerequisites may cross branches and node kinds. Branch entry nodes define reachability. Historical timing uses a preferred year and finite scenario-defined ahead-of-time cost multipliers; it never supplies a hard earliest-year lock. Unlocks reference units, buildings, abilities, policies, or modifiers by stable ID. Polity research and establishment state is authoritative, while each province stores its own 0–100 adoption levels so diffusion may be uneven.

## Contract versions

- World schema version 1 introduced geography and strategic military records.
- World schema version 2 adds character definitions and mutable
  loyalty/relationship records. A version-1 scenario migrates by setting
  `schemaVersion` to `2` and adding empty arrays for `traits`, `skills`,
  `professions`, `personalQuests`, `characters`, `relationshipThresholds`, and
  `companionRelationships`; content can then be added without changing IDs.
- World schema version 3 adds technology and institution definitions, graph branches, polity research state, and province adoption state. Version 2 migrates by setting `schemaVersion` to `3` and adding empty arrays for `researchBranches`, `technologies`, `institutions`, `polityResearchStates`, and `provinceAdoptionStates`.
