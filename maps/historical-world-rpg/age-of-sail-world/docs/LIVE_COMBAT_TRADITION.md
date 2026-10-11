# Combat-earned military tradition

The installed `MilitaryCombatEvents` death callback resolves both current
representations from military authority and checks hostility using campaign
allegiance. An eligible killer contributes the defeated force's **remaining
committed strength**, weighted by the authored `enemy_kill` numerator and
denominator, with integer floor per contribution. This is the
`_shared/engine/military_tradition.py::award()` contract. Rounding to zero produces
no award. Neither damage amounts nor caller-supplied XP determine the reward.

The force's controller and category at death own the experience. `player` has
independent scenario-defined tracks; allegiance identifies diplomatic opponents
without combining player and AI experience. Eligible AI controllers use the same
path. A controller transfer changes future attribution and reapplies local
projections, while prior experience stays with its controller. Generated strategic
force categories come from `unitAssignments`; an absent assignment has no inferred
tradition category. Enemy controllers must also be eligible, matching the headless
contract. A hero kill can commit an otherwise legal military loss but has no
authored military-category assignment and earns no military tradition.

Army, fleet, garrison and defense deaths consume authoritative strength. Garrison
losses also update settlement strength and preserve the existing RPG combat
notification. Core capture has no troop-loss contribution; there is no invented
capture/objective reward. Authored assist and objective weights are retained in
generated definitions but have no live dispatcher. Friendly, peaceful, protected,
unresolved and stale outcomes earn nothing. Scripted illegal deaths recreate the
representation from unchanged authority.

Loss and experience commit before native projection calls or RPG notifications.
The inactive, zero-strength force record is the durable consumed-loss receipt.
Duplicate deliveries, obsolete handles, removal during capture/load, and repeated
reconstruction cannot consume it again. A newly rebuilt defense after a later
capture can suffer a new real loss; retirement itself earns nothing. Callback
generations remain transient and are invalidated during ownership changes, map
activation and load transactions.

Military snapshot **v8** retains controller/category XP and the existing force
loss records together. It accepts v1–v7, preserves earned tracks and seeds missing
legacy tracks from scenario starting values. V6 orders and every earlier
settlement, clock, recovery and conflict migration remain intact. V7 and v8 require the
complete authored track set and rejects malformed, duplicate, unknown or missing
tracks before replacing authority or touching projections. Current scenario
definitions reconcile derived presentation without resetting XP. The whole
campaign load checkpoint restores experience, losses and retained representations
if a later domain fails. Campaign envelopes 1–9 remain supported. The headless
tradition state is v2; its v1 migration only seeds newly supported player tracks.

Live accumulated XP and weighted awards use **canonical decimal strings**:
`0`, or a nonzero digit followed by any number of decimal digits. The shared
`ExactNatural` arithmetic adds with digit carry, multiplies by integer weights
using exact doubling, and divides with bounded integer remainders. Floor applies
to each individual contribution. No whole-value float conversion, wrapping,
saturation, fixed digit array, or gameplay ceiling participates in XP authority.
An eligible one-point death at 2,147,483,647 commits the loss and records exactly
2,147,483,648; additions beyond 2^53 remain exact too.

V8 writes that decimal value directly. V1–v7 accept only canonical nonnegative
signed-integer XP and migrate the digits exactly; legacy overflow, signs, leading
zeros, fractions, exponent notation and trailing junk are rejected. V8 accepts
arbitrarily long canonical values. All numerical track fields are validated in
detached authority before projection changes. Immutable string values keep load
checkpoints independent. Restoring a track never invokes a contribution adapter.
Management inspection displays the full XP value, including on inactive maps.

Issue #464 resolves the authored coefficients and every milestone through a
replaceable `TraditionLayer`. Generated definitions retain each attribute ID,
signed numerator, positive denominator, milestone ID, exact threshold, effect ID,
mode and replacement target. Validation uses threshold order and rejects unknown
or forward replacement references. Generation compares executable constructor
arguments with `scenario/military-traditions.json`, including later milestones;
retaining the JSON payload alone is insufficient.

`ExactRational` multiplies exact XP by each coefficient and reduces the signed
numerator/positive denominator without a whole-XP integer or real conversion.
Decimal arithmetic supports coefficients and thresholds beyond native precision.
Small denominators use bounded integer remainders as an optimization; this never
bounds the dividend or result. Fractions survive adjacent XP values, every
threshold crossing and arbitrarily large totals. Milestones cannot cap or replace
continuous progression.

`TraditionDefinition.resolve()` follows the headless
`military_tradition.py::_resolve()` order: ascending threshold (thresholds are
unique), removing only the explicitly named earlier effect for an upgrade or
replacement, then appending the new effect. Unrelated earlier effects remain.
Every reached milestone is retained for inspection, with superseded effects
marked replaced. Active effects remain in resolver order.

Each eligible represented force receives a fresh typed layer from its current
controller/category on earned XP, control transfer, activation and reconstruction.
Reconciliation removes obsolete layers for ineligible or inactive forces. Abstract
forces derive the same values on inspection and receive them when instantiated.
Transfers never move XP between controllers. Layer stores own only tradition
contributions; replacement and removal do not alter unrelated modifiers. Native
load checkpoints retain the previous store with its original representations,
restoring both on rollback and retiring both on commit.

Layers and resolved bonuses are never serialized. Military snapshot v8 and all
supported migrations remain unchanged; legacy presentation slots normalize to
zero for typed definitions. Current definitions are reconstructed from saved XP
in detached authority before projections change. Consumed-loss receipts and
campaign transaction rollback continue to protect against repeated awards.

Military inspection displays full XP, exact reduced values (for example,
`attack_basis_points: 3001/10`), and all reached milestones on inactive maps too.
The native integer bound remains confined to the legacy generic projection API.
The typed path does not coerce values to health, abilities or floating-point stats.
Native representability never limits progression authority.

**Gameplay-effect consumers remain blocked.** The four authored attributes and
four named milestone effects have resolved values/identities, but no implemented
consumer changes attack, discipline, naval damage, maneuver or doctrine behavior.
`militaryTraditionIntegrationBlockers` in generated runtime data lists each missing
consumer; inspection labels these effects pending. No placeholder health bonus or
native ability mapping is introduced. Assist and objective weights still have no
dispatcher. Balance and native launch remain open.

The scoped evidence covers exact resolution/delivery portions of ROAD-0052 and
REQ-0155–REQ-0163 alongside #450's earned XP and #458's expandable representation.
It does not close the broader gameplay benefits of REQ-0155.01, REQ-0157.01,
REQ-0158.02–03 or REQ-0159.01, nor non-kill adapters (REQ-0154.02).

`MilitaryCombatEventsTests.wurst` drives installed production callbacks and
compares generated player/AI land/naval layers with the headless Fraction oracle.
It covers adjacent XP, every threshold boundary, large totals, stacking and
replacement, control/category changes, inactive maps, replacement representations,
inspection, repeated reconciliation, legacy/current saves and late failed loads.
The ordinary Warcraft adapter retains unrelated abilities and health during typed
replacement and rollback. `ExactRationalTests.wurst` covers signed, zero and
expandable coefficients/denominators. Python checks reject omitted coefficients,
lost later milestones and invalid replacements. No player QA or native-launch
success is claimed.
