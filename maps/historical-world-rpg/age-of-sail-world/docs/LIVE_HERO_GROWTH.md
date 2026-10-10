# Earned hero experience and growth

The shared `HeroProgression.wurst` implements the exact integer curve in
`_shared/engine/hero_progression.py`. For level L, the cumulative floor is
`50*n*(n+1) + 25*n*(n-1)*(2*n-1)/6`, where `n = L-1`. The cost from L to L+1 is
`100*L + 25*(L-1)^2`. Every threshold through level 300 is checked against an
independent sum and the headless engine by executable Wurst vectors.

Live `RpgHero.experience` remains residual XP above the current level's floor.
`cumulativeExperience()` explicitly adds that floor. Thus 300 XP from level 1
produces level 2 with 200/225 residual XP and 25 XP remaining. Awards can cross
many levels in one transaction. At level 300, residual XP continues accumulating
and no further level or point rewards are granted. The portable live integer
contract permits cumulative XP through 2,147,483,647. Negative/zero awards,
overflowing totals or balances, and invalid progression state/cadence reject
before mutation. A quest with a zero-XP reward can still commit its other rewards.
The Python engine uses arbitrary precision; cross-language parity applies within
the live integer range.

The scenario's existing `growth` definition is emitted into
`scenario-runtime.json.heroGrowthCadence` and each generated hero definition.
Age of Sail grants one skill point per newly earned level, a mastery point at
multiples of five and a choice point at multiples of ten. The difference of
integer level/cadence quotients counts each crossed boundary once. Starting
profiles still grant zero unspent points. Loading and projection reconstruction
copy authority without awarding XP or applying a starting profile.
`/inventory HERO` reads this authority for level, residual and remaining XP,
skill/mastery/choice balances, invested ranks and personal tree.

Registered quest turn-ins retain the authored stage graph, prerequisite checks,
physical interaction validation and completion deduplication. The whole XP award
is validated before quest completion, currency or progression changes. The
selected eligible character alone receives it. Recording-adapter tests use the
actual registered commands, generated Printed Compact stages, matching objective
receipts and separate physical return/turn-in. The recording condition boundary
does not claim that the unresolved domain-condition adapters are implemented.

## Save compatibility

RPG domain **v6** appends the choice-point balance to the existing hero record.
It retains v5 quest-stage records and v4 rank maps. Campaign envelopes 1–8 and
the headless progression schema are unchanged. Candidate validation completes
before any RPG authority changes; the campaign transaction also rolls back
authority and projections after later reconstruction failure.

| RPG input | Migration |
| --- | --- |
| v1 empty domain | Existing new-campaign initialization; the first valid recruitment applies the authored profile once. |
| v2–v3 | Keep recorded level, residual XP, skill/mastery balances, perks, personal progression and ownership; absent rank maps stay empty. Existing main-character migration remains in effect. |
| v4 | Also preserve allocated skill/mastery rank maps. Existing quest migration remains in effect. |
| v5 | Also preserve selected stages, objective evidence, consumed receipts and reward history. |
| v6 | Preserve all of the above plus the explicit choice balance. |

For v2–v5, the saved residual is rebased onto the corrected cumulative floor of
the **recorded level**, without replaying rewards or lowering an earned level.
For example, an old level-3/0-XP record becomes cumulative 325 XP at level 3,
keeping its allocations and unspent balances. Valid old uncapped residuals fit
the new, larger thresholds. Missing choice balances initialize to zero; there
is no retrospective compensation. Existing starting profiles are never reapplied
to recruited characters. Invalid, noncanonical or overflowing records reject
atomically, including residuals at/above the next threshold below the cap and
cumulative totals beyond the live integer limit.

This repairs earned-growth arithmetic, registered reward delivery, inspection
and persistence under ROAD-0051, REQ-0091 and REQ-0092. Point spending and selected
entitlements are now available through [hero allocation commands](HERO_ALLOCATIONS.md).
Broader reward-source bindings, perk/ability effects, independent progression axes and
relationship integration remain outside this closure claim. Native launch and
other release blockers remain in force. Automated validation needs no player QA.
