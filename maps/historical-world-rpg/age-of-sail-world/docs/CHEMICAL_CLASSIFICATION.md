# Chemical Classification scientific work (#527)

The owner's ordinary design delegation in
[HISTORICAL_BALANCE_AND_RESEARCH_EFFECTS.md](HISTORICAL_BALANCE_AND_RESEARCH_EFFECTS.md)
authorizes this 4% calibration. The exact scenario contract is
`scenario/progression/chemical-classification.json`; the shared engine contains
no Age of Sail IDs.

Chemical Classification adds **400 basis points** of
`repeatable_observation_efficiency` to funded repeatable observations and
specimen classification at `london_scholarly_work`, only for targets in the
scenario's scientific research branch. This is scholarly bench work producing
progress toward a selected technology. It is not combat damage, commodity
production or a global research multiplier. Non-scientific targets retain only
their other eligible scientific sources.

Use `/science inspect london_scholarly_work TECHNOLOGY` for the combined eligible
rate, current target bill, equipment, daily inputs and staffing threshold.
The existing site opens in 1660 with Scientific Societies. Equipment costs 120
treasury minor units and two actual local cloth units, commissioned over seven
days. This supplies instruments, specimen cases and recording tools. A lawful
local administrator with positive capacity and at least 40 administration must
supervise the assistants. Each funded day consumes one treasury minor unit for
assistants and one local cloth stock unit for filtering, specimen wrapping and
records. Missing stock or funds suspends output without partial payment or later
catch-up. Loss of lawful control, staff qualification, institution or local
market access cancels work. Abstract facilities use these identical durable gates;
an uncommissioned or idle facility generates nothing.

Start pays the selected technology's **full existing research cost** in advance,
then each funded day commits `floor((baseWork * (10000 + rate) + remainder) / 10000)`
work and retains the remainder modulo 10000. At the authored base of 100 work,
Chemical Classification produces 104 per day against 100 in the control and
completes a 9000-work study in 87 funded days against 90. Calculus retains its
independent named 500-bp `research_generation_efficiency` source: together the
rate is 900 bp and output is 109, completing in 83 funded days. Sources add before
one rounding and cap at +10000 bp. Duplicate typed grants never multiply a source.
The binding can execute with durable Electrical Experimentation and Classification
ownership even without the Calculus consumer. Completion invokes the existing
campaign technology grant, rechecking the authored bill and prerequisites.

Electrical Experimentation remains Chemical Classification's prerequisite.
Historical prices, including the 1770 preferred year, remain unchanged. The
preferred year is a price rule, not an unlock date: legitimate early research
pays the existing ahead-of-time multiplier. Neither the scientific-target list
nor the effect adds a 1770 calendar lock.

There is **no added persistence**. Military snapshot v19 already stores equipment,
owner, target, paid bill, committed day, work and fractional remainder. Existing
v1–v18 migration paths remain unchanged. Immutable site qualification reconstructs
from scenario definitions; earned sources reconstruct from completed research.
Capture clears work and fractions, transfers only completed equipment and never
transfers research. Staged restore and campaign rollback preserve work, treasury,
stock and entitlement ownership together. Human and AI controllers share the same
production action and day-advance APIs.

Focused interpreter and Python evidence is recorded in `reports/issue-527`.
Repository validation and the three official audits must be regenerated after
integration on the new main revision; focused execution does not establish release
blocker closure or native-client gameplay acceptance.
