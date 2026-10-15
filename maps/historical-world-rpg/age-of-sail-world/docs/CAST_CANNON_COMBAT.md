# Cast Cannon ordnance contract

Issue #522 delegates routine research-effect design to the agent. This scenario
contract interprets the existing Cast Cannon description, “dependable heavy
bronze and iron ordnance,” as improved effective damage from an already armed
heavy shipboard battery. The historical basis is the scenario's
`industrial_survey` chronology and its `evidence_shipboard_ordnance` reference,
John F. Guilmartin, *Gunpowder and Galleys* (1974), in
`scenario/naval/vessel-progression.json`. Those references motivate metallurgy
and shipboard ordnance as distinct capabilities; the magnitude below is gameplay
tuning, not a measured historical percentage.

The typed entitlement `(modifier, progression_cast_cannon)` supplies **+500
basis points of outgoing damage rating** under source
`research:modifier:progression_cast_cannon`. It applies only to the current
controller's active, living `sailing_naval` forces whose authoritative roster
profile qualifies for `naval_gunfire` and carries `naval_guns` or
`heavy_broadside`. The existing predicate also requires a warship, a valid ship
record, coastal/ocean sailing movement, the `broadside` ability and a matching
native siege attack. Representation handles, rawcodes alone, technology-gated
item ownership and an attack label alone cannot establish eligibility.

This initial binding deliberately covers heavy shipboard cannon batteries.
Field/siege artillery, rockets (including rocket formations with legacy cannon
metadata), small arms, boarding, rams, swivels, light-only batteries, transports,
unknown/missing profiles and incompatible categories receive no contribution.
Native non-attack/spell events and mismatched attack types receive no offensive
bonus. Abstract combat uses the same validated profile and calculation after
current strength, activity, location and hostility checks.

A base-100 hit becomes exactly 105 against an unchanged zero-rating control.
The research rating adds to independent tradition and equipment/refit damage
ratings before the single damage calculation:

`damage = base * max(0, 10000 + damage_rating_bp) / (10000 + max(0, resistance_rating_bp + discipline_rating_bp))`

All ratings and damage remain exact rationals until the existing native output
boundary. Duplicate entitlements from different completed nodes contribute once;
reconstruction replaces controller entitlement membership. Combat receipts
prevent duplicate delivery from scaling the hit again. Named independent sources
cannot duplicate the reserved research source. Captured forces immediately use
the new controller's research, and category/profile changes recheck eligibility.

Research retains `water_powered_machinery` as its prerequisite, base cost 110,
preferred year 1470 and the existing ahead-of-time formula (1056 in 1450 before
other modifiers). It grants no guns, equipment, free refits, conversion, abilities,
tradition experience or changes to recruitment requirements. Existing armed
profiles stand for their authored weapons; a vessel refit or an inventory tool
cannot silently rewrite that profile. Refit and tradition effects keep their
own sources and progression.

Combat definition catalogue v3 adds the reusable `weapon_attack` recipient with
an explicit attack and weapon whitelist. Definition v1 migrates through v2;
v2 retains its defensive consumers when read as v3. These are definition
migrations only. RPG schema 6, military schema 9, campaign envelopes 1–9 and
headless research schema 1 gain no fields: research completions and force profile
IDs already suffice. Legacy forces without a saved weapon identity remain
ineligible until an authoritative roster assignment exists. Load reconstruction
and failed-load rollback derive the contribution from restored completions and
current force authority without replaying charges or grants.

`/technology` reports the binding and whether research is earned. Military
inspection additionally checks the force's equipment profile. This closes only
the exact Cast Cannon entitlement binding after production combat execution;
other research consumers, native launch evidence and broader release blockers
remain independently accountable.
