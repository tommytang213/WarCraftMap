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

## Quest and event contract

`quest-event.schema.json` stores authored quests and events as declarative data.
Quests own stable-ID stages and objectives; stage transitions form a reachable,
acyclic graph. Events own stable-ID triggers and explicitly declare whether they
are repeatable. Quest/event prerequisites share an acyclic dependency graph,
while a repeatable event may explicitly emit itself with `repeat: true`.

Built-in prerequisite and outcome kinds express graph operations such as a
completed quest, an occurred event, reaching a stage, starting a quest, or
advancing along an authored transition. Generic world references are typed pairs
such as `{ "kind": "settlement", "id": "..." }` and are resolved against the
authoritative world collections rather than Warcraft object instances.

Scenarios extend behavior through `scenario_condition` prerequisites,
objective/trigger `conditionId` values, and `scenario_outcome` records. Their
IDs select handlers registered by runtime engine adapters; `entityRefs` supplies
validated inputs. Data must never contain scripts, function names, expressions,
or executable source. Adding a new shared world entity kind requires extending
both the schema enum and `ENTITY_COLLECTIONS` in the validator. Adding a new
generic behavior requires a schema/validator version change; scenario-only
behavior should remain behind registered condition/outcome IDs.

## Government, title, and territorial contract

Rank tiers are universal ordered identifiers from `none` through `emperor`; player-facing native and generic title names are scenario data in `titleStyles`. `titleGrants` link a title to a character or polity and record current allegiance independently. Sovereign grants have no grantor. Every non-sovereign grant names a strictly higher-ranked grantor, which permits an emperor to grant a subordinate king-tier title while rejecting equal-rank, upward, missing, and cyclic hierarchies.

`territorialHoldings` keep legal ownership, military control, civil governance, sovereignty, and autonomy in separate fields. A holding may name an overlord holding and owe scenario-defined tax and obligations. A holding with no overlord must have zero overlord tax and no overlord obligations, while every holding retains a positive ordinary upkeep rate. Territory and holder references use stable IDs; neither titles nor land depend on Warcraft object instances.

`military-tradition.schema.json` defines scenario-neutral stable IDs for eligible
controllers, categories, weighted combat sources, rational continuous
coefficients, milestone effects, and strategic-unit assignments. Persistent
experience is controller/category state; derived runtime layers are not saved.

`allegiances` represent one current polity per subject without country-specific rules. `validate_allegiance_transition` accepts a change between any two existing, distinct polity IDs, allowing runtime systems to change allegiance without changing title or territory identity.

## Inventory and equipment contract

`inventory.schema.json` defines generic item types, data-driven stacks, equipment slots, backpack types, progression tiers, and stable-ID owner state. The executable validator and deterministic pickup/recovery rules live in `_shared/engine/inventory.py`. Storage never grants equipment bonuses; only the dedicated equipment map does. V1 has six outer slots plus at most six backpacks of at most 30 slots each, with no nested containers. See the scenario `docs/INVENTORY.md` for native Warcraft 3.0 adapter findings and persistence behavior.

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
- World schema version 5 adds movement-class navigation-zone graphs, safe points and recovery anchors, and last-known-safe zoned positions for important active units. Version 4 migrates by setting `schemaVersion` to `5` and adding `navigationZones`, `navigationSafePoints`, and `activeUnitNavigationStates`; scenario topology and tracked active-unit state must then be populated with valid stable references.
- World schema version 6 adds declarative `quests` and `events`, including stable-ID stages, objectives, triggers, prerequisites, outcomes, and typed world references. Version 5 migrates by setting `schemaVersion` to `6` and adding empty `quests` and `events` arrays; authored content can then be added without changing existing IDs.

## Navigation and recovery contract

`navigationZones` form reciprocal graphs independently for `land`, `naval`,
`amphibious`, and `flying` movement. A connection is usable only for its named
movement class; pathability alone never establishes connectivity. Scenario safe
points distinguish ordinary verified points from recovery anchors. Decorative or
isolated zones may exist, but cannot become recovery destinations for a unit in a
different graph component.

`activeUnitNavigationStates` stores the current zone and last-known-safe zoned
coordinates for each important physically active strategic unit. These records
are authoritative data and contain no Warcraft handles. Formations use land
movement and ships use naval movement in the current strategic-unit model;
generic recovery policy also supports amphibious and flying mobile entities.
Structures and dummy/system objects are never eligible.

The headless selector returns a decision rather than moving anything. It checks
verified safety, movement compatibility, and graph reachability in this fixed
order: nearest-first nearby safe points, the stored last-safe position, connected
recovery anchors, then failure with no destination. Runtime teleportation is not
part of this contract and must re-verify a selected destination when implemented.

## Timeline contract

`timeline.schema.json` defines the reusable proleptic-Gregorian calendar, eras, stable event and schedule IDs, and bounded day/month/year recurrence. Campaign bounds are scenario data (Age of Sail supplies 1450-01-01 through 1820-12-31), not engine constants. Simultaneous occurrences sort by date, ascending explicit priority, stable schedule ID, occurrence number, then event ID. The scheduler consumes no randomness, so a caller seed cannot change this sequence. Missing priority is invalid, so authored ordering metadata is never implicit.

`timeline.py` advances over `(current, target]` pending occurrences (with initial-date occurrences processed on the first advance), so accelerated or skipped intervals emit the same sequence as incremental advancement. Persist `timelineStateVersion`, `currentDate`, and the stable `scheduleId`/`nextDate`/`occurrencesEmitted` records in authoritative world state; never persist runtime timers or handles. Future state-shape changes must increment `timelineStateVersion` and migrate stable fields before `validate_state`; incompatible or missing schedule references fail without mutating the source save. World schema version 7 adds the required timeline object; version 6 migrates by adding scenario-authored timeline data and changing `schemaVersion` to 7.
