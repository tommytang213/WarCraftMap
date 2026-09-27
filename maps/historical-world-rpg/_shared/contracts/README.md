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
