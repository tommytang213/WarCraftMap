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
