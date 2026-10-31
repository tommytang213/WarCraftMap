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

For the two policy/medicine findings, #548 adds fail-closed binding recognition:
current-source full pinned execution must observe registered research/actions,
campaign-clock replay, actual payments and local outcome consumers in matched
controls. Negative, replay and late-load rollback cases must also pass. A serving
local administrator must have the district jurisdiction and positive capacity;
foreign or unavailable offices authorize neither civic action nor local benefits.
No persisted fields or migration formats change. Focused results cannot close
these findings; the integrated-main audits must consume complete fresh evidence.

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

Issue #550 adds exact generated consumer metadata and current-source,
full-suite execution recognition for Arquebus Volley Drill, Artillery Offices
and Artillery Train. Each requires its matched production comparison and actual
reload, paid work or stock delivery probes. Missing, stale, failed or incomplete
evidence keeps each finding blocked. Issue #563 extends this contract to the exact
`bayonet_system` → `modifier progression_bayonet_system` →
`anti_cavalry_melee_defense` identity at 800 bp. Its isolated registered-research
comparison requires actual compatible socket equipment, legal roster dates and
prerequisites, hostility and cavalry melee. With no other ratings, incoming 108
resolves to 100; the unresearched control remains 108. Installed callbacks must
also emit the weapon-authentication, equipment and final damage-resolution probes.
Swords, bows, firearm shots, spells, siege, unknown equipment and unsupported native
metadata contribute no bayonet defense. Independent tradition and equipment ratings
remain additive before one final calculation. Reconstruction, transfer, current
save/load, legacy unknown-kit migration and late-load rollback execute in the same
required complete pinned suite. Office work accrues the last prepaid interval before a failed
renewal; subsequent intervals receive no office bonus.

No persisted field or schema changes are required. The integrated current
military v20 codec retains the earlier arsenal and firing records, and the
migration and late-load rollback tests execute that codec. After integration,
fresh current-main production execution, runtime and traceability audits must
remove the four land findings through verified comparisons. The #560 current-main
evidence transport and planner regenerate all three audits against the exact
revision and authored-source digest; missing, focused, stale or altered evidence
retains the findings. Release/launch promotion still requires fresh zero-blocker
closure and closed repair issues. Focused tests establish development behavior, not native client playability;
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

Calculus recognition requires the isolated registered-research comparison in
`ScienceExplorationTests`: both arms share Barometric Measurement (a Calculus
prerequisite), Scholastic Natural Philosophy, the same London facility and
Printed Observation Tables target. Only the treatment earns Calculus; Chemical
Classification is absent. Both pay the 108-unit target bill, 120 treasury and two
cloth for equipment, then one treasury and one cloth per funded day. The first
funded day commits 105 versus 100 work; completion takes 86 versus 90 funded days.
The independent Chemical source adds only for eligible observation targets.
`calculus_scholarship` requires comparison-local research, command, facility,
research-bill, daily-payment, committed-work and completion probes, plus all
Calculus lifecycle tests in complete passing pinned execution for the audited
revision and source digest. Focused or sibling-only evidence cannot bind Calculus.
See [issue 568](../reports/issue-568/README.md) for validation and integration.

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

## Trade exchange, remittance and canal finance consumers (issue #517)

`scenario/progression/trade-finance.json` supplies the shared `TradeFinance` and
`FinanceCampaignRuntime` adapters. The active map and inactive regions use the
same campaign ledgers and integer calculations. Player and AI controllers use
these same action methods. Research delivery rebuilds one named entitlement
layer; duplicate provenance does not multiply an effect. Activity starts no
earlier than the technology's authored preferred year (1580 auction, 1475 bills,
1710 brokerage, 1750 canal finance); early research retains its existing premium
and prerequisites but cannot confer an out-of-era finance benefit.

* A formal exchange requires an existing market, warehouse and authored urban
  trade role, lawful current control, administration and access. The existing
  commodity spread is now explicitly accounted as 50% transaction commission and
  50% liquidity/execution slippage. Auction research reduces only the commission
  component by 500 bp; brokerage reduces only execution slippage by 700 bp.
  Both components are portions of the existing spread, not extra charges.
  Actual marginal stock prices and scarcity remain unchanged. Savings round
  down independently against actual settled costs; each nonzero component keeps
  a positive minimum charge. Tiny orders can have zero saving. Buying and selling
  still validate stock, counterparty funds, compatible cargo, capacity, physical
  presence and transaction replay. No same-market merchant standing is awarded.
* `/finance remit SOURCE DESTINATION AMOUNT` transfers existing warehouse
  currency between controlled, administered banks in different provinces of the
  authored European correspondent network (London, Bruges, Venice and Genoa).
  Both endpoints require real banking/warehouse services, accessible markets and
  earned double-entry bookkeeping. The service bill is 200 bp of the principal,
  rounded up with a minimum of one minor currency unit; earned bills research
  reduces that bill by 600 bp, rounding the saving down. A transfer of 10,000
  costs 200 without research or 188 with it. The principal arrives in the other
  existing store and the fee is consumed. This is a currency transfer through
  banks, not commodity shipping, a loan or a new credit balance. Transfers use
  the existing persisted transaction history and never award trade standing.
* `/finance canal yangzhou_canal_quay` funds one durable refurbishment of the
  existing Grand Canal quay at the authored Yangzhou canal node. From 1750 it
  requires river transport bureaus, lawful local administration and market
  access, ten available local workers, 20 existing timber stock units, 1,000
  principal and 100 financing currency units from government treasury. Canal
  finance reduces only the financing bill to 94; principal and materials remain
  unchanged. Each of 90 funded workdays also requires the real local workforce
  and pays two treasury units in wages. Worker availability is a daily service
  capacity; workers are not consumed as casualties. Missing wages or workers
  suspend work without retroactive free days. Completion adds 200 cargo units to
  that existing local warehouse once, as a derived canal capacity contribution.
  Repeated starts, grants or refreshes cannot add a second quay. Capture cancels
  unfinished work without refund. Completed physical infrastructure survives
  transfer; research and its fee reduction do not transfer.

`/finance inspect [PROJECT]` explains conditions, bills, labor, materials, time
and expected output. `/technology` identifies each exact metric and its activity
availability; `/trade inspect` previews current one-stock-unit settlements with
eligible research. Existing discovery, ownership, supply, route and cargo checks
continue to govern the underlying actions. There are no new ships or equipment,
policy enactments, general construction discounts or treasury income passives.

Military/settlement snapshot schema **15** adds canonical canal project records
(owner, committed day, paid work and completion). Versions 1–14 without canal
records migrate to unstarted projects with no invented capital or capacity. Staging rejects missing,
duplicate, unknown, inconsistent, wrong-controller and future-day records before
mutating authority. The existing campaign transaction rolls back project state,
research, treasury, bank stores and stock together. Warehouse capacity is rebuilt
from completed works after load and before cargo use, avoiding duplicate layers.

The four exact research-unbound findings stay blocking without verified full
same-revision execution. The release audit now checks current source identity,
pinned compiler evidence, production probes and all required trade-finance
consumer tests before recognizing these four bindings. Focused development logs
are not that full release evidence. Native campaign launch issue #438 remains
separately owned; repository validation and integrated audit regeneration belong
to the controller.

## Naval construction and fleet services production consumers (#516)

`scenario/naval/services.json` supplies paid service recipes, compatible hull
profiles and facility calibration. `naval_services_catalog.py` reads the four
exact typed entitlements and 1500/1000/800-bp values from the approved design,
and construction price, upkeep, crew, provisions, weapon profile and recruitment
window from the resolved existing `ship_of_the_line_generic` roster. No national
starting strength, research prerequisite, research cost or historical roster is
rebalanced by these consumers.

`/naval inspect PORT` lists conditions, calendar availability, currency/material
bills, durations and results. `/naval dock PORT` commissions a dock for 200
currency, 20 timber and 10 iron, taking 90 days. `/naval board PORT` is a separate
100-currency, 90-day naval-board choice. Both require lawful administration,
labor, supporting dockyard technology and accessible markets. Port/banking/
warehouse services and nearby real naval pathing determine eligible yards;
current authored markets qualify London and Ragusa. They start without new docks
or boards. A government can administer its own port on an inactive physical map.
The same action API serves player and AI controllers.

* `/naval build PORT` commissions one existing roster hull after earned
  Battlefleet Doctrine, Public Credit, the local board and dock, and historical
  eligibility. The roster's early-access window starts in 1630 and ends in 1820.
  The bill is 1540 currency, 700 real manpower, 78 ship-provision stock units and
  settlement supply, 40 timber and 20 iron; paid ordnance is included in this
  construction recipe. At least one local worker must remain. Construction takes
  180 campaign days. Completion creates a durable fleet record and only then
  projects it locally. Existing ships never change archetype or receive free gear.
* Fleet maintenance uses the roster's 98 currency per 30 days, carried exactly
  across daily installments, plus one provision per day. Unpaid fleets cannot
  deliver attacks or receive carronade/carvel bonuses, and remain vulnerable
  to enemy attacks. `/naval supply PORT SHIP` transfers 78 actual local provision
  stock/supply units for 156 currency after one day; no supply or money is minted.
* `/naval repair PORT SHIP` consumes two currency, one timber and one local
  provision/supply unit per funded day. Base output is 100 hull-integrity units;
  earned Careening Stations makes it 115. Hull capacity is 10000. Repairs need
  an owned, living naval recipient at an operational dock and never heal at sea.
  Unknown legacy armament does not prevent ordinary repairs or invent a profile.
* `/naval mount PORT SHIP` installs a compatible carronade battery for 200
  currency, two timber and ten iron, taking seven days, from 1780. Completed
  Carronade Batteries, a qualified broadside-warship roster profile and paid
  mounts are all required. The +1000-bp source enters the existing exact gunfire
  rating calculation only for verified cannon attacks within 300 world units.
  A base-100 zero-rating control becomes 110. Long-range, spell, boarding and
  incompatible-weapon hits gain nothing. Existing doctrine, Cast Cannon and
  independent refit ratings retain their own sources.
* Carvel Hull Construction avoids 800 bp of actual voyage hull weather losses
  only for historically compatible carvel-built or paid-refitted ships, from
  1460. `/naval carvel PORT SHIP` requires an explicitly compatible refit profile
  and costs 200 currency, 20 timber and two iron, taking 30 days. It never
  automatically redesigns a legacy hull. The existing provisioned station-return
  circuit supplies geography and elapsed time; actual exposed days lose 100 hull
  integrity, reduced to 92 with the earned qualifying effect. Four exposures
  therefore cost 368 instead of 400 integrity. Supply-weather observations,
  navigation equipment and combat damage remain separate quantities. Zero hull
  integrity causes a real fleet loss, without combat invulnerability.

`/naval stop PORT` cancels the current project without refund. Service recipients
retire their representations while working; orders, voyages and scientific work
cannot double-use them. Repeated daily delivery, repeated research grants and
reconstruction cannot multiply output. Fixed-point repair/weather fractions and
maintenance installments persist. Capture cancels unfinished work and board
choices, preserves completed docks and ship gear, clears controller-specific
fractional research credit, and immediately re-evaluates the new controller's
own research and resource conditions.

Military snapshot schema **15** combines hull/service state (`h`), local shipyard
projects (`y`), land arsenals (`l`) and weapon deadlines (three-field `h`).
Versions 1–12 migrate with sound hulls, no invented paid mounts, refits, docks,
boards or projects, and no replayed historical losses or bills. Version 13 saves
from either implementation preserve their domain and initialize absent domain
state without funded projects. Three-field weapon deadlines and ten-field hull
records have independent validation and duplicate detection. Version 14 saves
from before finance integration retain land/naval state and initialize unfunded
canal projects; finance-only v14 saves retain canal/land state and initialize
unfunded naval state. Current saves require complete configured
land/naval/finance ledgers and every fleet's hull record.
Campaign envelopes remain unchanged. Parsing stages a detached ledger, rejects
invalid, duplicate, missing-current-version and future-day state, and campaign
load failure rolls back military authority together with research, treasury,
trade stock and projections. Active and inactive regions use the same campaign
runtime and calendar delivery.

`NavalServicesTests.wurst` executes registered research/actions, construction,
paid repairs/mounts, installed weapon callbacks, exact control comparisons,
negatives, source deduplication, capture, migration, rollback and a 50-year
fraction-conservation fixture. The integrated trace test exercises all seven
`naval_services` production probes. Focused evidence is retained under
`reports/issue-516`; the exact four release findings remain blocking until the
controller completes fresh integrated repository/runtime/traceability validation.
This work does not establish native-client launch or close #438.

The #562 closure verifier recognizes only Battlefleet Doctrine's exact
`unit:ship_of_the_line` → `ship_of_the_line_generic` paid commissioning consumer.
Generated consumer metadata derives its bills and eligibility from the roster and
scenario; it is not execution evidence. The isolated registered comparison,
negative/persistence tests and payment/work/completion/restore probes must pass
in the complete pinned suite for the exact audited revision and source digest.
Sibling naval effects remain separately blocked. The verifier reuses the existing
execution-evidence path; integrated-main audit regeneration remains the controller's
gate. See `reports/issue-562/README.md` for focused validation and closure steps.

The #569 repair verifier independently recognizes `careening_stations` →
`modifier:progression_careening_stations` → `hull_repair_throughput` at exactly
1500 basis points. Its generated consumer describes the scenario's daily bill,
operational dock and owned dockside recipient, missing-hull bound and independent
maintenance. The matched registered comparison earns only Careening Stations:
ten funded days restore 1150 versus 1000 integrity, paying two currency, one
timber and one local provision/supply per day in both arms. It also executes
snapshot/restore and repeated reconstruction/delivery. Separate tests cover full
hulls, legacy recipients without armament profiles, fractional credits, missing
inputs, access loss, capture, controller transfer, player/AI active/inactive
parity, migration and late-load rollback.

Repair recognition requires the complete passing pinned suite for the exact
audited revision/source digest, with successful payment, actual repair and restore
probes in that isolated comparison. Commissioning and combined naval traces cannot
replace it. Battlefleet recognition remains independent; carronade and carvel
findings require their own evidence. Focused results are developer validation
only. After integration, the controller must run the complete suite and regenerate
release-blocker, runtime-acceptance and requirement-traceability audits with that
revision's fresh execution evidence before closing the exact repair finding.

The #571 Carvel verifier independently recognizes `carvel_hull_construction` →
`modifier:progression_carvel_hull_construction` → `voyage_hull_weather_resilience`
at exactly 800 basis points. Its generated consumer records the authored built
and refit profiles, 1460 service boundary, 200-currency/20-timber/two-iron/30-day
refit recipe, actual exposure and independent provisions, maintenance, navigation
and combat quantities. The isolated registered comparison earns only Carvel:
equally provisioned compatible hulls take four actual 100-integrity exposures and
lose 368 versus 400 integrity. It executes weather, hull commits and mid-voyage
snapshot/restore, including duplicate delivery and research reconstruction.

Separate tests cover incompatible/unrefitted hulls, the exact service boundary,
unfunded maintenance, missing provisions, calm days, paid refit completion,
fractional carry through save/resume and interruption, destruction, capture,
player/AI and active/inactive parity, migration and failed campaign restoration.
Voyage support is validated after detached snapshot parsing has read all hull
profiles, so existing saves with voyage records before profile records resume
without a schema change; missing or incompatible profiles still reject.

Recognition requires the complete passing pinned suite for the audited revision
and source digest, with voyage-specific exposure, actual hull commit and
persistence probes in the isolated Carvel comparison. Commissioning, repair and
combined traces cannot replace it. Prior naval recognition remains independent.
`reports/issue-571` contains focused developer evidence only; after integration
the controller must run the complete suite and regenerate release-blocker,
runtime-acceptance and requirement-traceability audits before the exact Carvel
finding can disappear. Starting fleets and other research systems are unchanged.

## Army food and canal freight consumers (#519)

`ArmyFoodLogistics.wurst` consumes the two approved logistics modifiers through
`/logistics food DEPOT FORCE` and `/logistics freight PROJECT GOOD QUANTITY
[reverse]`. `/logistics inspect` shows bills, expected delivery, rate, workforce,
control, historical kit and connected-route conditions; `/finance inspect` retains
the separate paid canal construction preview. AI governments invoke exactly the
same actions on campaign authority, including when the region is inactive.

`scenario/progression/army-food-logistics.json` owns the quantities, costs and
route selection. A food depot is an authored warehouse/market with real grain.
One delivery withdraws 100 grain and pays 1 treasury currency for handling with
one available local worker. Ordinary waste is 25; bakeries avoid
`floor(25 * 800 / 10000) = 2`, delivering 77 supply versus 75. The force must be
living, supplied, controlled, within 768 map units, and carry an available land
roster profile with its real technology prerequisites. The depot and force must
share a traversable land component from the packaged terrain raster. Depot
positions use the materialized market service anchors or a verified land
approach within 512 map units. Warehouses without such an approach remain
ineligible. Strategic settlement coordinates do not substitute for these physical
services. Current source has 423 operational depot approaches; Hohhot, Karakorum,
Pskov and Thessaloniki have no qualifying approach in the packaged terrain. Unknown,
blocked, isolated, exhausted or out-of-era recipients gain no research output.
Historical sword/bow/levy formations qualify for food without firearm equipment;
the existing firearm and artillery predicates continue to gate their own effects.

Canal freight is local transshipment on the authored Yangzhou–Zhenjiang river
connection between canal nodes at the Grand Canal/Yangtze crossing. It requires
the completed paid Yangzhou canal quay, supporting technology, both lawfully
administered accessible endpoints, ten available workers at each, real allowed
grain/timber stock and destination commodity storage. The existing works still
cost 1000 principal, 100 financing before eligible finance research, 20 timber,
and 90 days at 2 treasury currency per funded labor day. Logistics research creates
no project and pays none of those bills. Throughput is 100 stock units per campaign
day, plus `floor(100 * 1000 / 10000) = 10` with canal research. Freight costs
`ceil(quantity * 100 / 10000)`, minimum one treasury currency. Stocks move without
creating income, provenance lots, food or merchant XP. Both directions and all
commodities consume one daily capacity bucket. Rejected transactions consume
nothing; missed days never bank capacity. Rates add once per typed identity before
rounding, and retained future research has no effect before its historical year.

Military snapshot **v17** retains a required `z,PROJECT,DAY,USED` record for each canal.
All v1–v16 inputs remain accepted through existing migrations: paid canal works
survive and absent freight counters initialize empty. Missing/duplicate/malformed
v17 records and future-day counters reject before authority replacement. Capture
retains completed infrastructure and today's consumed freight capacity; use and
bonuses are re-evaluated against both current controllers and their research.
Campaign rollback restores grain, treasury, army supply, canal usage and the
replaceable entitlement layer together. Immutable navigation and facility
configuration are reconstructed from source rather than serialized handles.

`ArmyFoodLogisticsTests.wurst` covers registered research and actions, exact
same-condition controls, resource/gear/era/infrastructure/geography negatives,
deduplication and layer repair, active/inactive parity, travel, capture, migrations,
failed campaign restore and fifty years of freight/food conservation. Production
probes and fail-closed `army_food_logistics.verified_bindings` require the complete
same-revision interpreter evidence before the two exact research release findings
can close. Focused development results do not replace the controller's integrated
repository/runtime/traceability audit; native launch #438 remains separately owned.

## Foundries and precision manufacturing consumer (#518)

`scenario/progression/industry.json` supplies paid batch recipes, equipment and
labor costs. The generator qualifies authored production plus existing market
and warehouse services: Stockholm and Liaoyang refine iron; Milan, Nuremberg and
Vienna manufacture gun barrels. Mining sites without warehouse infrastructure
remain material suppliers. These accounting quantities are bounded gameplay
batches, not historical population or tonnage estimates. No 1450 forces, stocks,
wealth, equipment or research completions are added.

Use `/industry inspect iron_refining:stockholm` or
`/industry inspect gun_barrels:milan` for the bill, requirements and expected
result; `equip`, `start` and `stop` use the same facility ID. Government legal
control, a serving administrator, prerequisite technology and accessible local
markets are required. Machinery costs 120 minor currency, 10 tools, 20 timber
and 10 manpower assigned as the durable workshop workforce, and takes 90 days.
Completed machinery/workforce transfers with a settlement; capture cancels
unfinished commissioning and work without refund and conveys no research.

A refining batch reserves 200 existing raw-material `iron` units (the catalogue's
ore/feedstock aggregate), 50 timber for charcoal fuel, 2 tools for wear, and 20
minor currency. Ten funded workdays produce 100 manufactured `iron_goods`, or
`100 + floor(100 * 700 / 10000) = 107` after Blast Furnace Practice, from 1500.
It never produces raw iron. A barrel batch reserves 100 iron goods, 20 timber,
5 tools and 40 currency. It produces 30 `arms` units representing finished
barrels in the existing ordnance commodity. Work advances by 100 units a day,
or exactly 106 after Boring Mills from 1750: `ceil(10000 / 106) = 95` funded
days versus 100. Both jobs pay one currency and one local supply per workday.
Missing daily inputs or finished-stock capacity suspend work without replaying
missed days. Existing artillery procurement still buys its roster equipment,
crew and supply and completes its own construction; manufactured stock changes
no existing cannon's damage, ship hull or combat gear.

Inputs consume accessible local market stock first, then delivered local
warehouse cargo and its FIFO provenance. Added material/output market definitions
start with zero stock and zero liquidity; existing trade access and physical
warehouse delivery rules still apply. This permits supply through real trade
without minting a counterparty's money. Player and AI controllers use the same
`IndustryLedger` and campaign resource adapter, independent of the loaded region.

Military snapshot v17 retains one complete `i` record per facility: equipment owner,
ready day, batch owner, integer basis-point work and last processed day. Legacy saves without industry records
migrate to uncommissioned industry; campaign, RPG and trade schema versions are
unchanged. Validation stages the complete ledger, rejects duplicate/missing,
unknown, malformed and controller-inconsistent records, and joins ordinary
campaign rollback with treasury, manpower, supplies, markets and cargo state.
Research layers are rebuilt from completions and deduplicate typed unlocks.

The two exact release findings remain blocking without current-source pinned
production execution. The release audit verifies the transcript and industry
payment/labor/output probes from the comparative production test before removing
these identities. Definition generation, Python simulations and a merged PR alone
cannot close them. The #438 native launch blocker remains separately owned.

The integrated military snapshot v18 requires complete industry, finance,
canal freight and banking ledgers. Independent v17 banking or logistics saves
retain their existing ledger and initialize the absent domain empty. Independent v15 layouts migrate their existing paid work;
industry v16 saves initialize absent freight counters empty, and logistics v16
saves initialize absent industry unfunded. Partially present ledgers still reject.
V14 finance saves may also lack naval state; missing domains never grant completed
infrastructure or free production.

## Chancery Archives and municipal government (#525)

`scenario/progression/administrative-contracts.json` owns these routine delegated
balance rules. Archives operate first: completed Chancery Archives research
passively adds `floor(500 * current administrator skill / 100)` basis points to
local tax collection efficiency. A serving administrator needs skill at least 40,
positive capacity and this exact settlement's jurisdiction. At the annual tax
boundary the archive operation costs `ceil(normal annual tax * 25 / 10000)`,
minimum one minor currency unit; no enactment or construction bill is added.
Unfunded archives contribute zero for that collection. Research never supplies
an administrator, records, money or sovereignty.

Chartered Municipal Government retains the catalogue's Archives prerequisite and
11% minimum urbanization. Its registered research action now additionally needs
at least one currently lawful, qualified local jurisdiction meeting that threshold.
Adoption exposes `/civic municipal DISTRICT`; it enacts nothing automatically.
The elected local policy costs 1% of normal annual tax, rounded up, requires a
90-day transition, and pays 0.5% annual upkeep in advance. It adds 400 basis points
to that district's collection efficiency while qualified, urbanized and funded.
`/civic municipal-repeal DISTRICT` ends it without a refund. Repeated enactment
rejects while pending or active; repeal and re-enactment restart the paid
transition and grant no loyalty, receipts or permanent modifier.

The district's initial urbanization is scenario accounting data: 20% for authored
capital, trade center, trade hub or caravan center roles, and 5% elsewhere. These
are conservative gameplay shares of the named local tax district, not claims
about national historical population. The current value persists independently of
buildings and can support later development systems. There is no urbanization
increase from research, appointment or enactment. The authoritative catalogue
continues to supply the adoption threshold; the compiler rejects a lost Archives
prerequisite. Abstract communities use the same roles, jurisdiction and ledger.

`/civic inspect DISTRICT` shows local urbanization, skill qualification, operation
bills, enactment costs, transition, upkeep and collection rates. Lawful operation
requires matching current controller and legal owner, no hostile occupation or
attack, and a serving administrator of that controller. Replacement uses the new
holder's skill immediately; absence of a Warcraft representation has no effect.
Capture cancels municipal authority without a refund or entitlement transfer;
urbanization survives. Recapture requires a new paid choice. Loss of qualification
or funding suspends benefit; no missed output is replayed on recovery.

Archive and municipal rates add once by typed content identity to the independent
survey collection contribution from #512, with one final integer rounding and a
cap at normal taxable capacity. Existing market liquidity supplies every receipt;
no generic gold grant exists. For annual capacity 10,001 and ordinary collection
9,000 basis points, the control collects 9,000, skill-50 archives collect 9,225
and archives plus a funded charter collect 9,585. Archive operation costs 26;
municipal enactment costs 101 and upkeep 51. Unavailable liquidity further limits
all three. Appointment, research and charter activation preserve all legal and
political control identities.

Military snapshot **v19** adds a required `u` record per configured civic district
for municipal owner, transition, prepaid-through date and current urbanization.
The existing `g` civic records and conflict membership `m` records retain their
meaning. V1–v18 saves initialize absent charters inactive and urbanization from
the scenario; existing paid surveys, policies and other domains survive. Partial,
duplicate, foreign-owner, malformed and future-dated current ledgers reject in
staged parsing. Campaign rollback restores the entire ledger with treasury,
markets and research. The two release findings only close with fresh same-source
pinned production execution, including comparative outcomes and late rollback;
controller integration must regenerate all three audits on the new main revision.

The integrated v19 codec preserves main’s banking `b` and freight `z` records.
Independent v18 municipal saves used six-field `b` records; migration recognizes
their arity and preserves those charters while initializing absent banking inactive.
V18 banking saves retain bank policies and initialize absent charters inactive.
V19 requires both complete ledgers; malformed or partial legacy ledgers reject.

## Civil Service Examinations local records administration (#573)

`administrative-contracts.json` adds the exact completed research identity
`civil_service_examinations` → `modifier:progression_civil_service_examinations`
as a fixed **500 basis point** collection-efficiency source. Its existing
1650 preferred year and Provincial Audits/Fleet Victualling prerequisites remain
authoritative. It changes no 1450 officials, wealth, forces or starting research.

The current district must be lawfully controlled, with a serving official of
that controller, matching jurisdiction, positive capacity and Administration at
least 40. At each annual collection, the existing records service must pay
`ceil(annual taxable capacity * 25 / 10000)` (minimum one currency unit) from the
existing government treasury before receipts arrive. Archives and Examinations
share this bill once; Archives retain their independently skill-scaled rate.
No new office, treasury, construction project or persisted service is introduced.

The fixed Examinations source adds once to Archives, completed survey and any
operational municipal charter before the existing final rounding. For taxable
capacity 10000 at base collection 9000 bp, isolated funded Examinations collect
9450 versus the matched control's 9000, with a 25-unit bill. Every receipt
withdraws actual local market liquidity and is capped by taxable capacity.
Failed funding contributes nothing for that year; later receipts never fund an
earlier missed bill. Repeated research provenance, reconciliation or annual
callbacks cannot multiply sources or repeat a bill. Replacement, capture and
recapture re-read current authority, entitlement and qualification. Research and
appointment produce no receipts and change no ownership, sovereignty or loyalty.

`/civic inspect DISTRICT` reports qualification, the shared bill, affordability,
and expected funded collection with current survey/municipal layers and local
liquidity. The annual boundary rechecks all conditions. Existing research views
show the exact typed identity and binding through the civic effect adapter.
Examinations adds no fields to the integrated military v21 or campaign/RPG schemas: annual service accounting
uses the existing committed civic day, treasury, liquidity and collected counter.
Legacy saves without civic history anchor on their first live day without
fabricating past service or receipts. Late failed-load tests restore these
resources and the annual cursor atomically after a real funded collection.

The exact release finding closes only when complete pinned execution, raw
transcript, source revision/digest and instrumented input hashes verify together.
Its own matched comparison must observe registration, registered research and
dispatch, current skill, campaign clock, annual advance, payment and collection.
Archives/municipal coverage cannot substitute. Focused, stale, incomplete,
failed or tampered evidence cannot establish closure. After integration, the
controller must run the complete pinned suite and repository/framework checks,
then regenerate release-blocker, runtime-acceptance and requirement-traceability
audits on the same new main revision. The planning audit tracks
`release:RESEARCH-UNBOUND-CIVIL-SERVICE-EXAMINATIONS-MODIFIER-PROGRESSION-CIVIL-SERVICE-EXAMINATIONS`.
No player QA is required.

## Funded local medical care (#572)

`scenario/progression/medical-care.json` binds the exact Pest Hospitals and
Clinical Records modifiers at 500 basis points each, retaining their catalogue
prerequisites and availability. `/civic inspect DISTRICT` opens the existing
research management context and shows bills, qualification, deadlines, treated
days and actual disease outcomes. Research creates no infrastructure or stock.

`/civic care DISTRICT` commissions civic isolation care for 1% of normal annual
district tax, rounded up, plus the district's existing medical-material bill.
Preparation takes 90 days. Operation prepays 0.5% annual tax for 365 days and
each actual exposed treatment day consumes one local medical-material stock
unit. The service needs a lawful civic center, accessible supplies and a serving
local administrator meeting the existing administration skill/capacity threshold.
Loss of staff, access, research or supplies suspends treatment without replay.

Clinical Records automatically maintains case records only during funded
isolation care or the existing paid medical response. Each treated day pays one
treasury minor unit and one existing `cloth` stock unit in an atomic transaction.
Clinical research can authorize that ordinary response action; Anatomy alone
supplies its separate 2500 bp contribution. The response's 2% tax/material bill,
90-day duration, quarantine trade penalty and 90-day cooldown retain their rules.
Failed record payment contributes nothing and never partially debits its bill.

All qualified sources add once before one calculation against available exposed
local manpower: 100 losses become 95 with either modifier, 90 with both, and 65
with both plus Epidemic Control. Fractional avoided people carry in integer
ten-thousandths between treated days and survive reload; unpaid or unexposed
days spend no credit. Combat casualties never enter this authority. Player/AI and
active/inactive regions share the campaign ledger and resource adapter.

Military snapshot **v21** requires one `r` record per civic district, holding care
owner, ready/paid-through days, disease fraction and treated/recorded day counts.
V1–v20 migration initializes absent care inactive and unfunded, retaining existing
civic state. Staging rejects duplicate, partial, malformed, foreign-owner and
future-dated ledgers before replacement. Campaign rollback includes these fields,
treasury, manpower, stocks and research. Capture preserves completed isolation
infrastructure but clears prepaid authority and fractional credit; unfinished
preparation is cancelled. A qualified successor pays new operation/materials and
receives neither research nor free treatment.

Generated exact consumer metadata is checked against the scenario and executable
registration. `pest_hospitals` and `clinical_records` have separate comparative
execution gates; neither a sibling trace nor a merged PR establishes closure.
After integration the controller must run the complete pinned suite and regenerate
release-blocker, runtime-acceptance and requirement-traceability audits on the new
main revision. Focused development evidence leaves both findings blocked until
that production evidence passes. No player QA is required.

## Codified Law and Overseas Colonial Councils local revenue (#585)

`scenario/progression/local-revenue-contracts.json` owns two distinct consumers.
Completed `codified_law` → `modifier:progression_codified_law` contributes 500 bp
through the existing funded records service. Current lawful control, a serving
local official of the controller, matching district jurisdiction, positive capacity
and Administration ≥40 are required. Law, Archives and Examinations share one
annual 25 bp records-operation bill, paid before annual collection.

Completed `colonial_councils` → `policy:progression_colonial_councils` enables an
explicit `/civic council DISTRICT` choice. It retains Archives and the catalogue's
16% adoption urbanization requirement. Adoption and operation require a qualified
overseas administrative district. The scenario authors directed Lisbon–Goa and
Goa–Malacca maritime connections using the existing port and Indian Ocean/strait
geography evidence. These are possible administrative connections, not claims of
1450 colonial ownership. Both endpoints must currently have the same lawful
controller, serving local offices and accessible stocked, unblocked markets;
the recipient must have Administration ≥40. Regional separation, a visit,
occupation or an authored connection by itself cannot grant colonial authority.
Other overseas districts remain unsupported until their connections are authored.

Enactment atomically charges ceil(1% of normal annual district tax) plus
ceil(0.5%) prepaid annual upkeep. A 90-day transition precedes the first funded
365-day interval. Renewals prepay the next interval; a failed renewal contributes
zero until a later successful payment buys future operation. Access, authority,
research and urbanization are checked again at collection. `/civic council-repeal`
clears the choice without a refund. Research never enacts a council, changes
sovereignty or ownership, grants allegiance, or appoints/replaces an official.
Capture/recapture clears council choice, transition and prepaid funding. Official
replacement rechecks the new official without duplicating the bill or policy.

All compatible sources add once to the existing relative collection-efficiency
bucket before final rounding. At capacity 10,000 and 9,000 bp base collection,
isolated operating Law collects 9,450 and isolated operating Councils 9,360,
before service expenses. Council operation can remain prepaid while the separate
records bill is unaffordable; this does not grant a records contribution. Actual
receipts are capped at normal taxable capacity and withdrawn from existing local
market money. Research, command and civic inspection views expose entitlements,
requirements, bills, deadlines, funding and actual cumulative receipts.

Military/settlement snapshot v23 combines navigation source attribution with mandatory `C` records keyed by stable
district and controller IDs. Each record stores council choice, ready day and
funded-through day. v1–v22 saves migrate missing councils inactive while retaining
existing civic, municipal, medical, administrator and economic state. The independent
v22 council layout retains councils and migrates missing coastal equipment and
source attribution; the v22 navigation layout retains equipment and source
fractions and migrates councils inactive. Duplicate,
unknown, foreign-controller, missing v23 or impossible deadline records reject
before mutation. Staged ledger forks preserve immutable connection definitions;
late campaign-load failure rolls back council funding, annual accounting, actual
money and research together. Object representations never own these records.

Each identity has its own registered-research production comparison and minimum
observed-call requirements. Focused development runs cannot close release
findings. The controller must run complete pinned execution and repository and
framework validation after integration, then regenerate release-blocker,
runtime-acceptance and requirement-traceability reports on the new main revision.
Each finding closes only with its own current verified evidence; no player QA
is required.

## Coastal position-finding tuning (issue #574)

The delegated coastal consumer uses 800 bp of actual position-finding overhead,
only on authored circuit days with usable shoreline bearings/charts and a
compatible owned vessel. Its paid practical chart/bearing kit costs 120 treasury
minor units, two existing cloth stock units and seven preparation days. This
does not require later precision instruments or alter authored research gates.
See [Coastal Triangulation](COASTAL_TRIANGULATION.md) for source composition,
commissioning, persistence and the complete-evidence closure contract.
