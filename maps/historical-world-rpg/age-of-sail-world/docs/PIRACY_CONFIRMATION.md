# Piracy confirmation boundary

`/prize-preview <action> <target> <commission|-> <capture|scuttle|release>
<ransom|release>` requests a target and dispositions. `CampaignPiracyActionAuthority`
resolves the current party, encounter, target, stores and campaign day. The old
13-argument form remains accepted only when every supplied fact exactly matches
that resolution; malformed numbers, inflated quantities and arbitrary dates fail
without mutating a participating authority.

The campaign adapter requires an eligible, present field-party actor, matching
party and loaded maps, a local military target and a completed boarding/raid
encounter. Combat owns `PrizeEncounter`: actor, allegiance, target, victim, map,
vessel classification, available prisoners and explicit crime authorization.
`MilitarySettlementRuntime.prizeCombat` exposes that observation boundary. The
shared `PrizeEncounters` implementation accepts records from trusted combat
producers; commands cannot create encounters. Missing or consumed encounters
reject. Initializing a force or entering its vicinity alone supplies no boarding
entitlement. This boundary can be exercised with initialized targets, stores and
recording encounters without the separate fleet-startup work.

A matching valid commission, ordinary military hostility, or explicit encounter
crime authorization permits the act. Unlicensed authorized crimes retain the
locked piracy consequences. A supplied expired, revoked or out-of-scope commission
rejects; it never silently changes a privateering confirmation into piracy.
Military records supply current controller, physical map, coordinates, force
eligibility and capture protection. Target-kind observations must also match a
fleet or settlement record. The existing `cargo:<force>` and
`warehouse:<settlement>` trade stores supply cargo, commodity and money. Combat
supplies prisoners; no request creates captives or invents a ransom valuation.
The destination is the current trade hold, and normal capacity/commodity limits
apply. This does not change trade selection or initialize missing stores.

Every confirmation resolves these facts again and repeats commission, exhaustion,
disposition, capacity and arithmetic checks. A changed actor, allegiance,
encounter, target state, destination, commodity, quantity, money, prisoner count
or commission reward/issuer requires a refreshed preview. Time can advance when
the outcome remains identical, but expiry and cooldown always use the current
campaign day. Captured vessel condition includes current and maximum strength
and supplies. Commission terms are copied into each resolution, so the final
comparison catches a changed issuer or rate even when the cash reward is zero.
The adapter performs one final resolution before any mutation.
All rejection paths precede cargo, money, military, combat or piracy writes.
Successful commits consume the encounter and source contents, apply the chosen
vessel outcome, and record consequences once. Seized cargo is uncosted; the
victim's acquisition lots cannot earn the captain merchant route credit.

Pending requests are private, sender-bound, copied choices and comparison facts.
They are retired after confirmation, authority replacement, piracy restoration or
snapshot reconstruction. Military reconstruction retires transient encounters.
No preview or combat authorization is serialized or inferred from historical
prizes. The persisted piracy v1 contract and campaign, military and trade schemas
are unchanged: existing prize rows, commissions, cooldowns and action IDs load
verbatim, including literal legacy fixtures. No migration fabricates authorization
or reapplies historical loot to another authority. A reconstructed campaign needs
a fresh encounter and preview for a new action.

`PiracyCommandTests.wurst` dispatches production commands through the production
campaign action adapter, real stores/provenance, military state and campaign clock
with recorded actor, combat and native projection/timer boundaries. Rejection
assertions compare all campaign domains, combat contents and native projection
writes. Tests cover both legal routes and crime authorization, forged legacy
facts, remote/absent actors and targets, changed control/removal/cargo/prisoners,
commission revocation/expiry/reward changes, final-read issuer/rate changes with
identical rewards, changed vessel supplies/maximum strength, capacity and integer
overflow, exact cooldown boundaries, duplicate delivery, coastal raids,
and campaign save/load between preview and confirmation. Existing piracy policy,
legacy persistence, military, trade, clock and load-transaction suites remain
part of the pinned complete execution gate.

Release status remains `blocked_pending_real_forsaken_kingdom_launch_smoke`.
These checks require no incremental player QA and do not claim native launch
validation.
