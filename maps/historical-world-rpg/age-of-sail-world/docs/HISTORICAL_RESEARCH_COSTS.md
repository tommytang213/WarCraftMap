# Historical research costs

Technology and institution `timeCost` records own the preferred year, base cost,
ahead-of-time multiplier and additional multiplier per year ahead. Generator v21
passes all four fields to the live definitions. Decimal tokens are read exactly,
including fractional base costs and multipliers; they never pass through a
binary float or an integer truncation.

The reusable `ResearchCost.wurst` implements the existing
`_shared/engine/technology_institutions.py::cost_units()` contract:

- Before the preferred year: `baseCost * (aheadMultiplier + annualMultiplier * yearsAhead)`.
- On and after the preferred year: `baseCost`.
- Decimal arithmetic has 28 significant digits with ties to even, followed by
  half-up rounding to integer millionths of a cost point.
- The native gold boundary rounds those millionths **up** to a whole point.
  Existing nonnegative adoption/support point discounts then apply, with a
  minimum charge of one. Live commands currently supply zero for both discounts.

For `pike_and_shot`, 1450 costs 864 points; 1469 costs 727.2 points (728 gold);
1470 and later cost 90. Early research remains available when prerequisites and
funds are satisfied.

Representable definitions have at most 28 significant decimal digits and a
normalized decimal exponent between -28 and 28 inclusive. The base must be at
least one millionth, the ahead multiplier at least one and the annual multiplier
nonnegative. Preferred years must fit a signed 32-bit integer; campaign years
must be valid Gregorian years 1–9999. Unsupported precision, missing fields,
invalid values and nonfinite numbers fail generation explicitly. The live
calculation also validates definitions, dates and discounts and rejects a charge
outside 1–2,147,483,647 gold before mutation. Large intermediate products use
decimal strings, so they cannot wrap Warcraft integers. Discounts cannot rescue
an unrepresentable historical charge.

Registered `/research`, `/unlock` and `/institution` commands calculate their
charge from the current authoritative campaign clock and definition at commit.
They check every prerequisite for the requesting controller, reject insufficient
funds and existing completions, and debit exactly once after a successful unlock.
Rejected actions preserve currency, completion records and projected effects.

Definitions and quotes are not persisted. RPG schema 3, campaign envelopes 1–8,
clock state and `u,controller,id` completion records retain their existing format
and migration paths. Loading restores the campaign date and completion IDs;
subsequent research uses that date and the current definitions. Existing earned
completions are neither repriced nor removed. No save version change is needed.

Automated evidence is scoped to historical costing, generated definitions and
the registered command boundary. Broader diffusion/institution integration and
native-client launch requirements retain their separate blockers. No player QA
is needed for this correction.
