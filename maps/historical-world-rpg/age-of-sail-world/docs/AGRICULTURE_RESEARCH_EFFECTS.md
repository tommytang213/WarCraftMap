# Agricultural research implementation (#513)

The four approved entitlement identities retain their original prerequisites,
research costs, and historical availability. Research enables an option; it
never grants a granary or enacts a reform. These effects are unavailable in 1450.

`/agriculture SETTLEMENT` shows conditions, benefits, bills and transition costs.
`/agriculture SETTLEMENT EFFECT` commissions the building or opts into a reform.
The technology screen links to this inspection. Administrative actions can use
remote territory, but require its current lawful control, supplied local
administration and an operational staple market. Farming additionally requires
an authored grain-producing hinterland and available tools. Agricultural
societies require an authored local agricultural network. Merely importing or
selling grain does not make a settlement arable.

An individual retains personal research and its native currency. Government
research uses that government's existing treasury only after an earned office
commission, or when governing a founded polity. Citizenship or a change of
allegiance alone grants neither treasury access nor another controller's
research. AI controllers call the same research and agricultural domain APIs;
there is no player-only effect, asset grant or waived bill.

| Action | Bill and activation | Production effect |
| --- | --- | --- |
| `granary` | 10% of local normal annual tax plus 10 delivered timber units from the settlement warehouse; 90 campaign days; one durable project per settlement | +20% staple market storage capacity and 10% less actual stored grain spoilage |
| `land_tenure_reform` | 1% of local annual normal tax; 90 days; 0.5% annual administration | +5% supported crop output and +2% actual rural tax collection; 2% transition unrest for 90 days only in authored applicable territory |
| `enclosure` | Same policy bill and administration; supported arable farming and its completed technology required | +8% crop output; 5% unrest for 730 campaign days, reducing affected real output; no changes to title or manpower |
| `progression_agricultural_societies` | Same policy bill and administration; local farming network and active paid organization required | +6% earned agricultural knowledge diffusion and +2% supported farm output |

All percentages, support quantities, historical transition eligibility and
materials are tunable in `scenario/progression/agriculture.json`; primary
magnitudes come directly from `gameplay-effect-design.json`. Local definitions
are compiled from the existing regional economic production and service data,
including abstract communities. The figures compress economic activity; they
are not population estimates or an equalizing grant to every polity.

The reusable Wurst consumer lives in `_shared/wurst/Agriculture.wurst`, with
campaign treasury, military, warehouse and market integration in
`CampaignAgriculture.wurst`. A supported annual harvest consumes actual grain
seed, one tool unit, and funded labor. Grain enters the real market only within
its available storage capacity. Spoilage removes existing grain. Tax collection
transfers existing market currency to the controlling treasury and cannot
exceed available liquidity. Construction consumes delivered warehouse timber
and its FIFO acquisition provenance without awarding trading profit.

Farming supported by an active paid agricultural organization earns local
practice adoption from consumed seed. Societies add their 6% to that real earned quantity, with one integer rounding operation.
The resulting bounded local adoption feeds the existing agricultural research
cost discount; it never completes a technology. The shared cost model retains
its positive minimum. Compatible crop contributions sum once before scaling
real output; repeated entitlement events and representations do not multiply
bonuses. Policy upkeep is prepaid at activation and each following 365-day
anniversary; inability to pay suspends the benefit until the next funded period.
Research and construction payments are separate and are never replayed on load.

Trade domain schema 5 nests agricultural state schema 1: local construction
deadlines, harvest deadlines, earned adoption, controller-owned policy sources,
and administrative payment deadlines. Trade schemas 1–4 migrate to empty
projects and knowledge at the saved date, without granting assets or fresh
stock. The existing campaign load transaction validates before mutation and
rolls agricultural state, markets, warehouse cargo, treasury and the clock back
together after a late failure. Current agricultural and campaign clocks must
agree. Capture transfers infrastructure, while policy effects and technology
eligibility follow the current controller. Inactive replay processes deadlines
in the same chronological order as active daily execution.

Generated consumer metadata recognizes the four registered typed entitlements.
The packager independently checks the generated agricultural definitions and
configuration call against their authored builder, including when output hashes
are resealed. This recognition does not close release findings.

The release audit requires current-source pinned execution evidence, every
agriculture regression, independent matched controls for each contribution, and
observed production probes for research delivery, registered actions, clock
advancement, payment, harvest, storage, tax and adoption. A separate production
registration test checks the campaign's research chain and day listener. Missing,
failed or stale evidence, or disconnected callbacks, retain all four exact
findings. The controls establish individual effects before the existing combined
harvest test checks composition; no gameplay or persisted schema changes are
needed for this reconciliation.

The controller must regenerate release-blocker, runtime-acceptance and requirement
traceability audits with integrated new-main evidence after merge. Source-only
audits retain the four findings. Headless checks do not establish native client
playability. Issue #438 is unchanged.
