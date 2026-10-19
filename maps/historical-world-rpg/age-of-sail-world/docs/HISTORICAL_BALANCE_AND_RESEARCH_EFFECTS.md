# Owner-delegated historical balance & research gameplay contracts

**Status:** owner-approved **design**, **not** a live consumer, completed research effect, verified playable map, or release gate. The source-of-truth data for the 26 current decisions is `scenario/progression/gameplay-effect-design.json`. Shared engine code must interpret typed scenario definitions; do not hardcode these Age of Sail names/magnitudes.

## Core player experience

- **Fun first, history as the starting situation.** The world begins **1 January 1450**, with territory, claims, cultural/regional troops, manpower, treasury, institutions, navy, fortifications and trade geography reflecting the real relative strengths and uncertainty of that period. Use the existing seven `scenario/politics/*-1450.json` political baselines and authored military/economic/settlement data. Do not copy modern borders or extrapolate population/army numbers from settlement *count* alone; compression is not historical manpower. Record the evidence, source quality, confidence and justified simplifications for each initial comparative strength. Never manufacture false precision. Regional powers need not have equal territory, army, fleet or technology.
- **A weaker start remains winnable by strategy, not by cheating the baseline.** Give every playable independent, vassal, tributary or threatened polity at least two credible, initially accessible survival/progression routes, such as defensible terrain and attrition, trade/port specialization, diplomacy, negotiated peace and tribute, alliance-building, espionage, politics, technological specialization, commerce, quests/character career, or limited-war objectives. Major powers keep true structural advantages; unsupported 1-v-1 conquest is *not* guaranteed for the underdog.
- **Historical crises remain genuine.** Existing 1450 active wars (including Ottoman–Byzantine, Hundred Years' War and Ming–Oirat) must retain their authored pressures. No forced historical winner, free army spawned for the player, secret player-only morale bonus, invulnerable capital, scripted invincibility, or arbitrary empire debuff. A very endangered polity can lose territory if played poorly, but the *individual* player retains a meaningful campaign path, including negotiated subjection, migration/service elsewhere, resistance or later restoration where lawful game systems permit it. Losing a war must not silently hard-delete the RPG character/progression.
- **Balance from costs and options:** Scaled support costs, supply lines, distance, war exhaustion, strategic objectives, morale, geography, estates, unrest, tech availability, diplomacy and opponent intelligence. Large polities have reach and resources but meaningful multi-front upkeep and coordination costs. Small polities can be agile/defensible/wealthy for historical reasons, without an ahistorical flat bonus. Same rules for eligible player/AI governments.
- **Player agency:** Warn about costly/risky policy and military actions through readable previews. Research, reforms and local facilities should create distinct interesting choices, not 200 pop-up approvals or repetitive mandatory clicks. Automatic administrative implementation of approved low-risk options may be delegated; opt-in/controversial reform stays player-controllable. No forced grind or unreasonably rapid snowballing.
- **Long campaign:** Both tiny and large countries can grow and diverge; balancing must not introduce an arbitrary hard cap on the existing unbounded military-tradition XP. Research bonuses use small finite, attributable contributions, while continuous combat XP evolves according to its existing separate curves. Economy remains resource-conserving rather than minting money/food/troops from modifiers.

## Concrete mechanics shared by research consumers

1. Five typed unlock kinds retain their source `(controller,node,kind,contentId)`; only completed technology research enables them. A modifier activates passively *only when its recipient/condition really exists*. A building/ship requires real commissioning, time and payment. An ability is a player/AI action with duration and cost. A policy is unlocked for local enactment/administrative delegation with visible upkeep/tradeoffs; merely unlocking a policy does not force a controversial reform. This never changes authored prerequisites, research gold costs or 1450 political identities.
2. Interpret numerical values as **basis points relative to the eligible domain quantity**, with 10,000 = 100%. E.g. 500 = 5%, 800 = 8%, 2500 = 25%. The concrete metric is specified in each record. Reductions only reduce actual costs or losses; gains only affect real inputs/capacities and cannot create shipments, debts, assets, naval guns, food or recruits out of thin air. At zero qualifying activity the benefit is zero.
3. Source-aware stacking: deduplicate an unlocked `(kind,contentId)` per controller regardless of multiple sources/reloads; add compatible basis-point adjustments **once** to the appropriate rate/efficiency bucket before applying the actual authoritative transaction. Do not multiply near-identical bonuses between representations or native/abstract callbacks. Explicitly upgraded/replaced military traditions still replace their prior effects. Enforce a positive minimum fee/cost and valid existing inputs rather than applying a universal hard cap to character/military XP.
4. For passives, the relevant controller must currently own the force, unit, province, ship, port or route *and* satisfy the stated equipment, terrain, access, facility and service predicates; no globally distributed buff for owning a tech. For buildings, capture transfers durable infrastructure but does not transfer completed research; the new controller must satisfy use requirements. Policy activation and local project completion survive save/load deterministically, with clean rollback. Inactive-map calculations use the same result as the active representation. No instantaneous free granting from event history.
5. **Default balancing costs for newly defined actions:** policy enactment costs 1% of affected annual normal tax and has a 90-day transition, with 0.5% equivalent ongoing annual administration; each Granary costs existing materials plus 10% of the town's annual normal tax equivalent and 90 in-game days, max one per town; medical response costs 2% of settlement's annual normal tax equivalent plus medical supplies, lasts 90 days with 90-day cooldown; cadastral surveys cost 1% of annual province tax and take 90 days. If a required real tax/material input or authoritative state does not exist, the implementation must introduce and test a lawful domain integration, not substitute free coins, fake stock or a generic health bonus.
6. Currency, percentages, time granularity and affected domain state must be visible through the existing management/research UI. Reuse shared engine effect families across future scenarios, leaving parameters scenario-owned. A schema/design entry must remain **unbound** until live callbacks and deterministic real-state tests pass.

## Approved initial values for the 26 existing needs-design tickets

These are **calibration starting values**, not claims that a historical reform improved productivity by exactly these percentages, and not evidence of shipped gameplay. Effect interactions must honor equipment/region/country/era predicates. Each corresponds to one existing exact typed entitlement.

| Unlock node | Kind / content ID | Activation and qualifying recipient | First-pass mechanic |
| --- | --- | --- | --- |
| `abolitionist_public_sphere` | Policy `progression_abolitionist_public_sphere` | policy choice for `controlled_civic_centers` | **5%** `civic_reform_diffusion`. Only applies where reform discussion and lawful civic institutions exist; no automatic emancipation, no blanket global diplomacy modifier |
| `agrarian_improvement` | Building `granary` | build per settlement for `owned_settlement_with_food_storage` | **20%** `staple_storage_capacity`. One durable granary per settlement; pays a construction bill and takes 90 campaign days; separately lowers stored grain spoilage by 10% |
| `agrarian_improvement` | Policy `land_tenure_reform` | policy choice for `controlled_rural_provinces` | **5%** `crop_output_efficiency`. Reform administrative action, no double grant; +2% rural tax efficiency; temporary transition unrest only where historically applicable |
| `agricultural_mechanization` | Policy `enclosure` | policy choice for `controlled_rural_provinces` | **8%** `crop_output_efficiency`. Requires eligible arable land and technology; transitional unrest +5% on affected rural territory for two years; no automatic confiscation or instant manpower generation |
| `agricultural_societies` | Policy `progression_agricultural_societies` | policy choice for `controlled_farming_provinces` | **6%** `agricultural_knowledge_diffusion`. Only eligible agricultural networks, +2% farm output conditional on locally supported farming and active organizations |
| `anatomy_and_medicine` | Ability `epidemic_control` | active settlement action for `controlled_settlement_during_outbreak` | **25%** `epidemic_losses_avoided`. 90-day quarantine/medical response; reduces disease losses only; local trade throughput -10%; consumes existing medical resources and treasury; cooldown 90 days |
| `arquebus_volley_drill` | Passive modifier `progression_arquebus_volley_drill` | passive research for `land_formation_arquebus_musket_firearms` | **5%** `firearm_reload_efficiency`. No sword, bow, cavalry-charge or siege gain. Compatible with, but independent of, Ordered Volley/Platoon Fire damage and Pike and Shot defense |
| `artillery_offices` | Policy `progression_artillery_offices` | policy choice for `owned_arsenal_production` | **8%** `artillery_production_throughput`. Requires actual arsenal and arms inputs, administrative upkeep +2% of artillery procurement; never spawns free guns |
| `artillery_train` | Passive modifier `progression_artillery_train` | passive research for `supplied_field_artillery` | **8%** `artillery_supply_waste_reduction`. No benefit for isolated, unsupplied artillery; cannot manufacture ammunition from nothing |
| `auction_markets` | Passive modifier `progression_auction_markets` | passive research for `eligible_formal_auction_transactions` | **5%** `market_transaction_fee_reduction`. Existing market/auction infrastructure and real trade transaction required; no generated cash |
| `barometric_measurement` | Passive modifier `progression_barometric_measurement` | passive research for `qualified_sea_voyages` | **10%** `storm_attrition_reduction`. Only on eligible voyages using actual weather information; no immunity, perfect prediction or generic battle armor |
| `battlefleet_doctrine` | Ship/unit unlock `ship_of_the_line` | commissioning unlock for `qualified_warship_yards` | **unlock only** `unlock_recruitment`. Purchase existing ship_of_the_line roster at its historical, shipyard, tech, manpower, funds, supply, maintenance and construction-time rules. No free hulls or automatic upgrades |
| `bayonet_system` | Passive modifier `progression_bayonet_system` | passive research for `bayonet_equipped_firearm_infantry` | **8%** `anti_cavalry_melee_defense`. Requires actual socket bayonet compatible equipment; not a generic 8% damage boost for all land forces |
| `bill_of_exchange_networks` | Passive modifier `progression_bill_of_exchange_networks` | passive research for `qualified_long_distance_trade_transfers` | **6%** `secure_remittance_fee_reduction`. Reduces existing transaction/remittance costs for accessible banking networks; does not mint gold or create debt/loans |
| `blast_furnace_practice` | Passive modifier `progression_blast_furnace_practice` | passive research for `fueled_iron_smelting_facilities` | **7%** `iron_refining_yield`. Consumes actual ore, fuel, labor and equipment; no raw-iron creation or universal wealth multiplier |
| `boring_mills` | Passive modifier `progression_boring_mills` | passive research for `qualified_artillery_manufacturing_workshops` | **6%** `gun_barrel_production_throughput`. Requires foundry/machining infrastructure and materials; no bonus to existing cannon combat damage |
| `botanical_collecting` | Passive modifier `progression_botanical_collecting` | passive research for `qualified_overland_exploration_parties` | **10%** `unknown_route_attrition_reduction`. On eligible survey journeys only; does not reveal hidden map or instantly discover secrets |
| `brokerage_houses` | Passive modifier `progression_brokerage_houses` | passive research for `formal_exchange_hubs` | **7%** `market_slippage_reduction`. Requires legitimate market access and active trading volume; real counterparty and stock constraints remain |
| `cadastral_survey` | Passive modifier `progression_cadastral_survey` | survey province for `controlled_surveyed_provinces` | **5%** `land_tax_collection_efficiency`. Must complete paid local survey before benefit, no instant census of unknown territory; collected revenue still limited by taxable economic capacity |
| `calculus_methods` | Passive modifier `progression_calculus_methods` | passive research for `controlled_scholarly_research_centers` | **5%** `research_generation_efficiency`. Only active scholarly centers with research inputs; no direct firearm or artillery firepower |
| `campaign_bakeries` | Passive modifier `progression_campaign_bakeries` | passive research for `supplied_land_armies_with_grain` | **8%** `grain_supply_spoilage_reduction`. Consumes and transports real grain; reduces waste, not hunger when disconnected from logistics |
| `canal_logistics` | Passive modifier `progression_canal_logistics` | passive research for `connected_operational_canal_routes` | **10%** `canal_freight_throughput`. Only actual built and usable canal routes; not desert roads, ocean passages or generic player movement |
| `canal_tolls_finance` | Passive modifier `progression_canal_tolls_finance` | passive research for `funded_operational_canal_projects` | **6%** `canal_infrastructure_financing_cost_reduction`. Reduces financing costs for real canal works; does not hand out free capital or apply to all buildings |
| `careening_stations` | Passive modifier `progression_careening_stations` | passive research for `ships_at_operational_careening_ports` | **15%** `hull_repair_throughput`. Actual repair materials, money, access and time required; no healing at sea, no free owned docks |
| `carronade_batteries` | Passive modifier `progression_carronade_batteries` | passive research for `warships_equipped_with_carronade_guns` | **10%** `close_range_naval_gunfire_damage`. Only valid carronade mounts and close-range cannon shots; no free armament and no long-range buff; preserve gunnery doctrine and vessel refit layers |
| `carvel_hull_construction` | Passive modifier `progression_carvel_hull_construction` | passive research for `carvel_hulled_or_validly_refitted_vessels` | **8%** `voyage_hull_weather_resilience`. Only ships with historically compatible carvel construction/refit; no automatic redesign of legacy hulls or combat invulnerability |

## Preauthorized design decisions for *subsequent* authored research unlocks

The research catalogue has many more entitlements than these 26. Their missing gameplay consumers are **implementation/balance tasks**, not one new player decision per technology. Future issues must group compatible consumers into at most four exact audit identities per implementation issue, by shared engine domain (farming, governance, logistics, economy, industry, science, exploration, land combat, naval combat, shipbuilding). Use historical descriptions, existing capabilities/resources, and these ranges to select small scenario-owned defaults:

| Domain | Normal first-pass effect family and range |
| --- | --- |
| Agriculture/storage | +4–8% conditional real yield/technology diffusion; +15–25% local storage capacity; no free food |
| Trade/finance | 4–7% reduction of an existing eligible fee/slippage/financing cost; no invented profit or debt |
| Transport/logistics | 6–10% reduction in real spoilage/supply waste or improved capacity on actually connected routes |
| Manufacturing | +5–8% throughput/efficiency when correct facilities, raw materials and skilled workers exist |
| Science/exploration | +3–6% earned research efficiency in scholarly centers or 8–10% fewer eligible journey hazards |
| Military | 4–8% narrowly typed, weapon/role-gated firing/drill/defense/supply efficiency; never free troops, always respect existing continuous tradition and upgrades |
| Naval | +5–10% narrowly typed seamanship/gunfire/endurance or up to +15% port-only paid repair rate; no free ships/guns |
| Civic/policy/health | 4–6% historically contextual local reform diffusion or a costed active choice with proportional tradeoff; emergency medical response up to 25% reduction in verified disease losses |
| Recruitable unit/building/ability | Unlock legitimate existing action and eligibility rules, not automatic object creation; assets require resources, time, manpower, space and maintenance |

If existing scenario data provides an explicit numerical coefficient, that value **wins** over the generic range. If a novel system is genuinely absent (e.g., whole new slavery/disease/debt mechanic), implement a bounded, historically reasonable and optional domain rule with deterministic tests, **not** a hardcoded placeholder. Ask the player only when a choice would contradict an explicit prior design decision, involve a sensitive new moral/roleplaying opt-in that cannot be defaulted responsibly, or change approved basic gameplay architecture. Do not issue routine '[needs-design]' tickets for a normal modifier magnitude, recipient, supply cost or technology role. The user has delegated those choices.

## Historical starting-strength verification gate

Before claiming the campaign is balanced, produce a reproducible **1450 baseline and viability report** sourced from the regional political/settlement/economic/military files: every playable polity's relative holdings, revenue and liquidity, military/fleet force projection, manpower and supply, technical era, trade access, alliances/subjects, fortifications, local geography, and active wars. Use *historical references and uncertainty bands* for relative tier calibration. Do not generate arbitrary equal initial forces or compare province-count as a direct power proxy. Document plausible exceptions and compression errors.

Use deterministic simulation seeds across diverse starting conditions. Include historical stress exemplars such as a fragile polity facing an expansionist neighbor, small merchant polity, maritime state, inland minor, tributary/vassal, and large imperial polity. Demonstrate: (a) at least **two meaningful non-exploit early survival/development options** for each minor exemplar, (b) historically larger actors have a clear conventional initial advantage unless local evidence says otherwise, (c) no automatic near-term guaranteed collapse caused only by an initial selector rather than game choices and current state, and (d) plausible eventual growth from a small state without special player-only combat buffs or unavoidable historic outcomes. The rare near-doomed historical start may remain extremely hard to keep **independent**, but not impossible to continue playing as an individual.

Evaluate both 10-year opening survival and 25–50-year progression, varying player choices and the same AI rules. A scenario with 100% instant empire annexation across every reasonable opening strategy is unacceptable; a minor conquering the leading empire in one battle without a strong situational edge is equally unacceptable. Preserve costly defeat, negotiated peace, subject status and personal alternate progression rather than requiring every polity to win its first war. Record sample seeds, definitions, assertions and remaining risks.

## Implementation and audit honesty

- This file resolves a **design backlog**, not the existing release blocker. Binding a JSON record, renaming or closing a question, passing headless compilation or merging a PR is not proof of a working Warcraft III campaign.
- Each implementation must run registered real production consumers, negative capability/ownership tests, save/rollback, active/inactive map parity, Wurst/headless deterministic checks, and same-revision release/traceability/CI audits. Only the correct executed effect may clear its corresponding research-unbound audit finding.
- Do not touch the native launch crash evidence in issue #438/PR #455; Warcraft 3.0 native client gameplay remains unverified. Keep that separate and a priority before release.
- Bundling four related unlock consumers into one implementation issue is preferable to four independent unintegrated PRs. The group must remain testable and small; avoid a single 220-unlock monster PR.
- If a design value needs tuning after actual combat/economy simulation, update this versioned scenario catalogue and regenerate deterministic evidence. Avoid spawning new user decisions for ordinary tuning.

## Civic governance production consumers (#512)

`scenario/progression/civic-governance.json` supplies the local conditions, bills,
calendar durations and economic calibration for the three civic consumers. The
compiler reads their exact typed unlocks and basis points from the approved
`gameplay-effect-design.json`; it does not change research prerequisites or costs.
Shared `CivicGovernance` and `CivicCampaignRuntime` run the same rules for any
controller, independently of physical map or Warcraft object survival.

Use `/civic inspect DISTRICT`, where DISTRICT is a controlled settlement ID, for
expenses, conditions, deadlines and outcomes. `/civic policy`, `/civic repeal`,
`/civic survey` and `/civic response` take that same ID. A serving administrator
and legal control authorize local administration. A mere occupation, regional map
selection, nationality or technology discovery does not authorize it.

* The civic policy requires a civic center and locally available discussion.
  After the paid 90-day transition it accelerates the district's bounded civic
  institution diffusion meter by 500 bp. Annual administration is paid in advance;
  failure to fund renewal suspends the policy. No emancipation or diplomacy is
  inferred from institutional discussion or progress.
* Each settlement is a local tax district of its authored province. A paid survey
  takes 90 days and improves only that district's collection efficiency by 500 bp.
  Surveying the entire province costs 1% of its districts' combined normal annual
  tax. Completed local land records survive capture; their benefit requires the
  new controller's own entitlement. The annual levy transfers existing market
  liquidity into the government treasury, capped by the assessed taxable capacity.
  The default 90% collection rate becomes 94.5%, with one final integer rounding.
* Medical response consumes government treasury and existing local cloth stock
  for dressings. It reduces actual exposed manpower disease losses by 2500 bp
  for 90 days, followed by 90 days of cooldown. A persisted district-wide daily
  shipment budget drops from 1,000 to 900 stock units during response, shared by
  purchases and sales across all commodities. Splitting transactions, changing
  cargo stores or reloading cannot reset that budget. The initial bounded disease
  exposure is the authored 1778 Hawaii contact outbreak; other locations require
  additional authored outbreaks. Unavailable medical commodities and blocked
  supply access reject activation without partial payment.

Gains and avoided losses round down; positive currency bills round up. Daily
losses describe the interval ending at each committed day, so a 90-day response
covers exactly 90 future daily loss intervals. Tax is collected once per 365-day
accounting year. These are campaign accounting units, not historical demographic
estimates. Capacity factors retain the existing economy's capital, port and market
asymmetries; this does not claim to prove relative historical national strength.

Military/settlement snapshot schema **11** includes local civic projects, policy
choice, response/cooldown, diffusion, outcome counters and shipment usage. Versions
1–10 migrate with inactive projects and no invented past revenue or supplies. The
first live day anchors legacy accounting. Campaign transaction rollback restores
this ledger together with treasuries, commodities and research. Capture cancels
policy choices, unfinished surveys and medical authority, retains completed land
records and local cooldowns, and grants no research or assets.

The three exact research-unbound release findings remain in the release audit
until fresh integrated current-main execution, runtime and traceability evidence
removes them. Focused interpreter execution is development evidence; it does not
establish native client playability or resolve the unrelated #438 crash.

## Land drill and artillery production consumers (#515)

`scenario/progression/land-army.json` owns the four land research bindings,
kit predicates, arsenal eligibility and action calibration. The compiler checks
these exact typed identities against the approved design and resolves equipment,
weapons, historical dates and required technologies from the inherited roster.
The shared `LandArmyEffects` and `LandArmyRuntime` consumers use current control;
research never commissions a force or adds equipment to an existing roster.

`/land inspect ARSENAL` shows bills, conditions, deadlines and work. An arsenal is
an authored arms-producing settlement, with a local tax district, lawful government
control, a serving administrator and an accessible local market. `/land policy`
and `/land repeal` require that settlement ID. Enactment costs 1% of normal annual
local tax and takes 90 days; annual administration costs 0.5%, paid in advance.
Failure to fund renewal suspends the office. This is an explicit local choice.

`/land commission ARSENAL` pays the existing field-artillery roster price and
withdraws 30 actual local arms, 30 manpower and 30 supply. One local order can be
pending. Completion takes 90 workshop days. An active office adds 800 bp to daily
work on an order that also paid its 2% procurement administration bill. At the
initial values, a funded order completes after 84 days. Activating an office later
does not retroactively accelerate an order that did not pay the surcharge. No
research, policy or load callback grants a free battery. Blockaded, occupied or
unadministered workshops cannot operate. Capture cancels the old policy and work;
spent resources are not refunded or transferred as completed artillery.

`/land supply ARSENAL FORCE` transfers a fixed 100-unit shipment from actual arms
stock to owned, living field artillery that already has supply. The local route
must be on the same physical map within 768 map units, with an accessible source.
Normal handling wastes 25 units. Artillery Train avoids floor(25 × 800 / 10000)
= 2 units of waste, so the force receives 77 instead of 75 supply. The full shipment
is withdrawn either way. A disconnected, hostile, dead, unequipped or empty-supply
force cannot use this delivery action or obtain a train bonus.

Arquebus drill contributes 500 bp to firing frequency, independently of volley
damage and tradition defense: interval = floor(base milliseconds × 10000 / 10500),
with a positive minimum. The scenario owns the base primary-weapon interval for
eligible runtime templates (initial foot company: 1350 ms). Native cooldown and
abstract firing use the same calculation. Native/abstract duplicate deliveries
share a hit receipt; the next-shot deadline survives reconstruction and save/load.
Socket Bayonet System adds 800 bp to the defense bucket only for actual compatible
socket-bayonet infantry receiving a verified cavalry melee hit. A musket weapon
name alone does not establish bayonet equipment. Swords, bows, siege, spells and
unqualified kit receive no drill/defense substitution. All four effects and actions
use the same legal rules for player and AI controllers.

Military/settlement snapshot schema **13** adds the local arsenal policy, prepaid
upkeep, order work, paid surcharge, serial identity, accounting day and firearm
reload deadline, using distinct `h` firearm, `l` arsenal and `j` science records.
Schema 12 science state remains authoritative during migration. Schemas 1–12
migrate with inactive artillery projects and no invented past charges or deliveries. The first live day anchors legacy accounting.
All fields participate in detached validation and the existing campaign rollback.
Balance quantities remain scenario-owned; gains round down and positive bills
round up once at the transaction boundary.

The four exact research-unbound findings from #515 remain release blockers until
fresh current-main production execution, runtime and traceability audits remove
them. Focused tests establish development behavior, not native client playability;
the unrelated #438 crash remains blocked.
## Science, weather and exploration production consumers (#514)

`scenario/progression/science-exploration.json` configures the shared
`ScienceExploration` ledger and `ScienceCampaignRuntime` resource adapter. Exact
entitlement identities and 1000/1000/500 basis-point rates come from the approved
design catalogue. These are future options; no research, equipment, forces or
supplies are added to the 1450 start.

Use `/science inspect SITE` to see conditions, expenses, progress and outcomes.
`/science inspect` lists the authored sites. `/science equip SITE` commissions
local instruments/collecting equipment for 120 treasury minor units and two
existing cloth stock units, taking seven campaign days. This bill covers the
commissioned tools and their cases; research never supplies them. All sites
require lawful local administration, market access and an earned supporting
technology/institution. Journey actors must also have the authored roster type,
control, physical map and station position. Player and AI use the same action API.

* `channel_weather_survey` uses the existing Channel station-return sea circuit,
  compatible patrol vessel and oceanic seamanship, from 1640. Actual weather is
  a scenario-owned deterministic five-day observation cycle with two exposed
  days. Each exposed day risks ten supply units; a provisioned, equipped voyage
  with barometric research avoids 1000 bp of those actual losses. Ordinary
  provisions, navigation credit and combat statistics remain separate.
* `isles_botanical_survey` is an explicitly authored unknown overland survey
  circuit, available from 1600 with caravan surveys and the compatible local
  formation. Each survey day risks two supply units. Earned botanical collecting
  avoids 1000 bp of that hazard. Neither circuit reveals map knowledge, bypasses
  travel boundaries or discovers secrets. Each takes ten funded survey days,
  consumes two ordinary supply units, one treasury unit and one cloth stock unit
  per day, and pays one additional treasury unit at departure. The actor's local
  representation retires during the circuit and returns to its station afterward.
* `london_scholarly_work` requires London's durable civic/market facilities and
  the scientific societies institution, from 1660. `/science start SITE TECHNOLOGY`
  validates the target's unchanged prerequisites and pays its full current
  authored research gold cost from government treasury. Each funded day consumes
  one additional treasury minor unit and one actual cloth stock unit for research
  materials and produces 100 scholarly work units. The target requires 9000 work;
  earned calculus adds 500 bp to generation, finishing in 86 funded days instead
  of 90. Completion uses the existing research unlock consumer, rechecking the
  authored cost and prerequisites. There is no firearm/artillery effect, generic
  treasury yield or transferable invented research currency.

Insufficient daily materials, money or provisions produce no work or avoided
loss and make no partial payment. Missing days are never replayed for free after
resupply. Compatible sources add once per typed identity in their metric bucket;
fractions carry between funded days, with integer gains rounded down. Repeating
commands, reconstruction or save/load cannot duplicate output. `/science stop SITE`
cancels work without refund. Capture cancels unfinished work/commissioning;
completed equipment survives while the new controller needs its own research,
administration, supplies and actor access. Critical state is independent of
Warcraft object survival and follows the same day replay on inactive maps.

Military/settlement snapshot schema **12** introduced (and schema **13** retains)
equipment commissioning, controller, target, paid research bill, committed day,
work, fractional credit and
actual hazard outcome counters. Versions 1–11 migrate with inactive science work
and no invented assets or past output. Parsing stages a separate ledger, rejects
missing/duplicate/invalid records and future committed days, and campaign load
rollback restores science together with treasury, stock and research authority.

The three exact issue #514 research-unbound release findings remain pending the
controller's fresh integrated current-main execution/runtime/traceability audit.
Focused development tests do not establish native client playability or resolve
the unrelated #438 crash.
