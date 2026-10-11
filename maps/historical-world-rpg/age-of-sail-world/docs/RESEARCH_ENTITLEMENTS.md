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

The production `UnboundResearchEffects` adapter retains these references and
reports `unbound`. It never alters food capacity or any native statistic.
`/technology` and `/institutions` show each identity, whether it is earned, and
its binding status. A recording adapter can report a tested binding; this does
not establish a production gameplay consumer. All 220 authored references have
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
