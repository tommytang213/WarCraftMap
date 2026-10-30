# Typed research entitlements

Research completion earns every authored `(nodeId, kind, contentId)` reference
for the requesting controller. The five kinds are `unit`, `building`, `ability`,
`policy`, and `modifier`. Content IDs are declarations in the research catalogue;
they are not Warcraft rawcodes or magnitudes. There is no common content registry
for these five domains, and no numeric effect can be inferred from a name.

Generator v27 preserves node order, all prerequisite edges, exact historical
cost coefficients, and authored unlock order. It checks stable IDs, duplicate
nodes/typed references, prerequisite references/cycles and live capacities
(512 nodes, 512 prerequisites and 64 unlocks per node). Invalid inputs fail before
output generation. Generated expected unlock counts also make dropped live
records invalid. Empty authored unlock lists remain valid and earn no content.

The registered research action still checks current cost, every prerequisite,
controller ownership, funds and duplicate completion. Definitions are validated
before completion mutation or charging. Successful research passes a complete
`ResearchEntitlements` object through `TechnologyEffectPort`. The recipient owns
that object and its copied entries; regenerated definitions remain independent.
Entries follow definition order and authored order within each node. Historical
headless events retain their existing `(kind, contentId)` sort order; the derived
entitlement view preserves authored order without rewriting saved history.

Delivery is an idempotent replacement of one controller's research layer, not an
incremental bonus or grant. It must preserve other controllers and unrelated
modifiers. Different nodes unlocking the same typed content retain both sources;
`has(kind, contentId)` provides union membership without multiplying a grant.
Kinds remain distinct even when they share a content ID. The boundary is a
non-fallible projection operation; one-time grants are outside its contract.

The fallback `UnboundResearchEffects` adapter retains these references and
reports `unbound`. Campaign registration wraps the existing adapter with
`CombatResearchEffects`, which binds only scenario-declared combat recipients.
The navigation adapter independently binds the scenario-owned voyage contract.
Other typed references and existing consumers survive that wrapper. Neither
adapter alters food capacity, health, equipment or native abilities.
`/technology` and `/institutions` show each identity, whether it is earned, and
its binding status. A recording adapter can report a tested binding; this does
not establish a production gameplay consumer. Of 220 authored references, 218 still have
individual release-blocking consumer findings, including all three unlocks from
`mass_army_logistics`. Generated runtime metadata retains the same blocker list.

RPG schema 6, campaign envelope schemas 1–9, and headless research schema 1 are
unchanged. Only completion records (`u,controller,node` in live saves) are durable;
no entitlement, binding flag or bonus layer is saved. Existing completions remain
valid without retroactively enforcing repaired prerequisites. Reconciliation
rebuilds all saved controllers and clears obsolete controller layers, including
on transaction rollback. It does not replay research actions, debit resources,
rewrite event history or reissue grants. Malformed candidate saves are rejected
before authority/projection changes; downstream reconstruction failures use the
campaign's existing checkpoint and rollback boundary.

Issue #463 supplies definition retention and entitlement delivery for ROAD-0045.01.
Gameplay consumers, broader technology/institution integration, and native-client
launch evidence remain separate release blockers. No player QA is required.

Issue #474 binds `(modifier, army_discipline)` through combat catalogue v2:
`research:modifier:army_discipline` contributes exactly **+500 basis points** to
forces explicitly assigned `land_formation` and currently controlled by the
research owner. This is an approved gameplay tuning value, not a historical
measurement. An identical entitlement from another completed node retains its
provenance but contributes no second copy. Partial research contributes nothing.

Defensive discipline adds the controller's exact continuous
`discipline_basis_points` and compatible, source-identified ratings before
`damage_received = base_damage * 10000 / (10000 + max(0, discipline_rating_bp))`.
The existing offensive and naval-resistance consumers remain separate. This
recipient rule requires a force record, not a firearm profile: legal melee,
weapon and spell combat can encounter discipline. Peaceful, protected,
environmental/unresolved and stale events cannot activate it. Naval or unknown
categories and characters without a qualifying force record receive no layer.

The damage boundary derives the layer from current authority, so there is no
cached per-unit bonus to accumulate or preserve across replacement. Research
reconstruction, force transfer/category reassignment, recruitment, inactive-map
simulation, map activation, successful load and rollback use the same binding.
No campaign/research/military save schema changes are necessary. Existing
completion records reconstruct the new effect without replaying research,
charging funds, rewriting history or changing XP. Combat catalogue v1 migrates
to v2 with its original weapon consumers and no new research bindings.

Technology/institution and military inspection display the source, +500 basis
points, recipient category, binding and active status. The release audit removes
only `RESEARCH-UNBOUND-PIKE-AND-SHOT-MODIFIER-ARMY-DISCIPLINE`; other research
consumers, maneuver, missing weapon identities and the #438 native-launch issue
remain open. Pinned interpreter tests do not establish native Warcraft launch.

Issue #523 binds `(modifier, progression_celestial_navigation)` to the
scenario-owned [Celestial Navigation voyage contract](CELESTIAL_NAVIGATION.md).
A purchased observation kit and current controller research reduce the
position-finding provision allowance by 10% during the explicitly eligible
station-return circuit. Full provisions are reserved before departure; campaign
time, legality, equipment, geography and other progression layers remain
independent. Military v10 saves the necessary voyage inputs, with pure legacy
migration and the existing campaign rollback boundary. Only this research
consumer finding is removed; weather/exploration consumers and native launch
remain separate blockers.

Issue #522 binds `(modifier, progression_cast_cannon)` to qualified heavy
shipboard gunfire through combat catalogue v3. See
[the Cast Cannon contract](CAST_CANNON_COMBAT.md) for its exact rating, weapon
whitelist, activation, stacking and save compatibility rules.

Issue #574 binds `(modifier, progression_coastal_triangulation)` to qualified
paid coastal position finding in the existing voyage authority. Its 800 bp source
requires a separately commissioned chart/bearing kit and explicitly usable coastal
circuit days. See [Coastal Triangulation](COASTAL_TRIANGULATION.md). Release closure
requires complete passing current-revision pinned evidence, including an isolated
registered coastal-only comparison; generated binding metadata alone cannot close
the release finding.
