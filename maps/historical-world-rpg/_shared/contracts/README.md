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

## Government, title, and territorial contract

Rank tiers are universal ordered identifiers from `none` through `emperor`; player-facing native and generic title names are scenario data in `titleStyles`. `titleGrants` link a title to a character or polity and record current allegiance independently. Sovereign grants have no grantor. Every non-sovereign grant names a strictly higher-ranked grantor, which permits an emperor to grant a subordinate king-tier title while rejecting equal-rank, upward, missing, and cyclic hierarchies.

`territorialHoldings` keep legal ownership, military control, civil governance, sovereignty, and autonomy in separate fields. A holding may name an overlord holding and owe scenario-defined tax and obligations. A holding with no overlord must have zero overlord tax and no overlord obligations, while every holding retains a positive ordinary upkeep rate. Territory and holder references use stable IDs; neither titles nor land depend on Warcraft object instances.

`allegiances` represent one current polity per subject without country-specific rules. `validate_allegiance_transition` accepts a change between any two existing, distinct polity IDs, allowing runtime systems to change allegiance without changing title or territory identity.

## Contract versions

### Campaign saves

Campaign saves use `campaign-save.schema.json` and `_shared/engine/campaign_save.py`.
The envelope records independent schema, build, and scenario versions plus a SHA-256
checksum of canonical UTF-8 JSON (computed with the checksum field empty).

Stable slots are `autosave_01` through `autosave_15`, positive-numbered manual
slots, `session_start`, and `major_milestone`. Only authoritative world/player JSON
state is stored; Warcraft handles are rejected. Migrations are pure sequential
`N -> N+1` functions applied to a deep copy after integrity verification. Loading
never rewrites source bytes, and persisting a migrated result is a separate action.

- Campaign save schema version 1 introduces the versioned envelope, slot model,
  authoritative state, integrity metadata, and migration registry.

### Scenario world

- World schema version 1 introduced geography and strategic military records.
- World schema version 2 adds character definitions and mutable
  loyalty/relationship records. A version-1 scenario migrates by setting
  `schemaVersion` to `2` and adding empty arrays for `traits`, `skills`,
  `professions`, `personalQuests`, `characters`, `relationshipThresholds`, and
  `companionRelationships`; content can then be added without changing IDs.
- World schema version 3 adds technology and institution definitions, graph branches, polity research state, and province adoption state. Version 2 migrates by setting `schemaVersion` to `3` and adding empty arrays for `researchBranches`, `technologies`, `institutions`, `polityResearchStates`, and `provinceAdoptionStates`.
- World schema version 4 adds scenario-defined title styles, title grants, territorial holdings, overlord taxation/obligations, and mutable allegiance records. Version 3 migrates by setting `schemaVersion` to `4` and adding empty arrays for `titleStyles`, `titleGrants`, `territorialHoldings`, and `allegiances`; scenario content can then be added without changing prior stable IDs.
