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

Military snapshot **v7** retains controller/category XP and the existing force
loss records together. It accepts v1–v6, preserves earned tracks and seeds missing
legacy tracks from scenario starting values. V6 orders and every earlier
settlement, clock, recovery and conflict migration remain intact. V7 requires the
complete authored track set and rejects malformed, duplicate, unknown or missing
tracks before replacing authority or touching projections. Current scenario
definitions reconcile derived presentation without resetting XP. The whole
campaign load checkpoint restores experience, losses and retained representations
if a later domain fails. Campaign envelopes 1–8 remain supported. The headless
tradition state is v2; its v1 migration only seeds newly supported player tracks.

Live XP uses the existing signed integer representation. Weighted arithmetic
avoids intermediate multiplication overflow; an unrepresentable positive result
or accumulated total rejects the combat commit coherently. This is a numeric
representation limit, not a designed progression level cap. Unbounded live totals
remain part of REQ-0158's unfinished work.

Issue #450 scopes ROAD-0052, REQ-0154 and REQ-0164 evidence to **earned experience
and persistence**. Authored attribute coefficients, qualitative milestones,
category-wide gameplay effects and non-kill contribution adapters remain open
(REQ-0154.02 and REQ-0155–REQ-0163). The previous generated placeholder HP rate is
zero: authored attack, discipline, naval damage and maneuver coefficients must
not silently become maximum-life bonuses. Their definitions remain in the
packaged scenario data for their own future adapters. No native-launch or release
candidate status is changed by these headless and diagnostic checks.

`MilitaryCombatEventsTests.wurst` exercises installed production callbacks, player
and AI land/naval tracks, integer weights, ownership changes, consumed losses,
native cleanup reentry, stale handles, save/reconstruction, legacy migration and
failed restoration. It also exercises the ordinary Warcraft military projection
with interpreter units. Python checks compare the callback vectors with the
weighted headless contract and validate generated definitions. No player QA is
required.
