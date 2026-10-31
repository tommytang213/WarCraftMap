# Coastal Triangulation on funded voyages

Issue #574 delegates routine tuning to the historical balance authority. The
scenario authors an **800 basis point** reduction of actual position-finding
provision overhead. This is gameplay tuning, not a measured historical quantity.
The research catalogue remains unchanged: `pilot_books` is required, preferred
year 1480 and base research cost 104. Practical shoreline bearings and working
charts do not require the later precision-instrument research.

`scenario/naval/navigation-efficiency.json` v2 extends the existing voyage
contract with unique typed sources. Celestial Navigation retains its 1,000 bp
source and purchased astronomical observation kit. Coastal Triangulation adds
`(modifier, progression_coastal_triangulation)`, conditioned on a compatible
scenario vessel, current-controller research, completed paid chart/bearing kit,
and usable shoreline bearings/charts for the actual authored circuit day.
`coastalBearingDays` explicitly qualifies each day; false days, including open
water, earn no coastal credit. The initial Channel/adjacent North Sea circuit
follows usable coastal sight lines for all ten days. The broad navigation-zone
name alone never qualifies an arbitrary sea route or vessel.

Commission the `channel_coastal_bearing_kit` through the existing command:
`/science equip channel_coastal_bearing_kit`. The existing science payment port
charges **120 treasury currency minor units and two existing cloth stock units**
at London, with **seven campaign days** of preparation. It requires Pilot Books,
lawful local control, market access and the supported living vessel at station.
Research grants no equipment or geography. The site is commissioning-only:
`/science start` cannot create a second journey. Preparation and active science
work reserve the actor against other commissioning, science, naval work,
movement and voyages. Completed equipment is reusable and survives capture;
unfinished preparation is cancelled without refund. Capture transfers no research.

Departure still reserves the full undiscounted 50 provisions. Each elapsed day
consumes five, of which two are position-finding overhead. Coastal research alone
costs **92 per 100 overhead** over five circuits, saving eight provisions. Both
eligible sources together save 18 per 100 overhead. Ordinary food, weather supply
losses, hull damage, travel time, discovery and starting equipment are unchanged.
An unsupported activity, insufficient departure provisions, missing equipment,
unresearched or wrong controller, or unqualified day earns no coastal contribution.

Each source contributes once to the same integer ten-thousandths bucket. Only
that bucket releases whole provisions. Per-source remainders record attribution;
they never refund independently. Their sum modulo 10,000 must equal the common
remainder. Three combined eligible days earn 10,800 units: one provision released,
800 common remainder, 6,000 celestial remainder and 4,800 coastal remainder.
Repeated callbacks cannot replay a day. Interruption or destruction returns only
unused reserved provisions; earned fractions remain durable campaign state.

Military snapshots use **v23**, combining the independent v22 navigation and
council layouts. Existing `v` records preserve
celestial equipment, pending routes, elapsed days, last day, reservations and
common credit. New `x,FORCE,SOURCE,REMAINDER` records identify each source by stable
ID. The chart/bearing kit uses the existing stable-ID science `j` equipment record.
Versions 10–21 assign their existing fraction to the celestial source; earlier
versions retain their existing empty-voyage migration. Missing legacy kit records
migrate empty and never copy live equipment. Council-bearing v22 snapshots also
migrate their celestial fraction and missing coastal equipment; navigation-only
v22 snapshots retain all source fractions and initialize councils inactive.
Current saves require complete source
records with valid conservation and complete kit records. Detached parsing rejects
duplicates, unknown IDs, inconsistent reserves/fractions, overlapping reservations
and unsupported work. Campaign load rollback includes equipment, provisions,
research, treasury, commodity stocks and time. Headless voyage state advances from
v1 to v2; the enclosing optional military schema remains v2.

Research and military views show source magnitude, eligibility, kit cost and
preparation conditions. `/science inspect channel_coastal_bearing_kit` shows the
actual equipment owner and ready day. Generated consumer metadata identifies the
exact typed entitlement, qualification, rate, equipment site and runtime consumer.

`CoastalNavigationTests.wurst` uses registered research, commissioning and voyage
commands with real campaign payments and callbacks. Its isolated coastal-only
comparison proves 92 against 100 overhead, independently of Celestial Navigation.
Other tests cover composition, fractions, duplicate research, missing inputs,
open-water days, unsupported hulls, interruption, destruction, player/AI and
active/inactive parity, capture, migration and late-load rollback. Python tests
cover exact arithmetic, generation and evidence rejection.

The release verifier closes only this exact identity with complete passing pinned
execution for the integrated revision and source digest, including the isolated
comparison's actual resolution and credit-commit probes. Missing, focused, failed,
stale or tampered evidence cannot close it. Focused local results are developer
checks, not release closure evidence. The controller must run the complete pinned
suite, repository/framework validation and regenerate release-blocker,
runtime-acceptance and requirement-traceability audits after integration on main.
No incremental player QA is required.
