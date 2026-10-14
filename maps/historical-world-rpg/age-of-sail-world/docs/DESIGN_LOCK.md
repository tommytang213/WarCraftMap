# Design Lock v0.1

<!-- req:REQ-0001 --> This file records requirements already agreed with the player. They are defaults unless deliberately revised later.

## Campaign

- <!-- req:REQ-0002 --> Single-player.
- <!-- req:REQ-0003 --> Target the latest Warcraft III.
- <!-- req:REQ-0004 --> Primary language: English.
- <!-- req:REQ-0005 --> Global Age of Sail / early-modern historical sandbox, roughly 1450-1820.
- <!-- req:REQ-0006 --> Campaign is intentionally extremely long; content and systems should support 100+ hour play rather than a normal WC3 map session.
- <!-- req:REQ-0007 --> The player is an individual inside a living world, not an abstract country.

## Reusable architecture

- <!-- req:REQ-0008 --> Engine and scenario content are separate.
- <!-- req:REQ-0009 --> A future historical timeline/location should reuse the same systems and swap scenario data, terrain, units, technology, events, quests and assets.
- <!-- req:REQ-0010 --> Avoid Age-of-Sail-specific assumptions in shared modules.

## World hierarchy

- <!-- req:REQ-0011 --> Countries/polities contain provinces/states/regions and settlements.
- <!-- req:REQ-0012 --> Administrative naming may differ by culture while exposing understandable generic equivalents where useful.
- <!-- req:REQ-0013 --> Ownership, control, occupation, governance and sovereignty are distinct concepts.
- <!-- req:REQ-0014 --> Provinces and cities can change hands through war.
- <!-- req:REQ-0015 --> Settlements can grow and world state can evolve over time.

## AI territorial warfare doctrine

- <!-- req:REQ-0016 --> AI territorial warfare uses a hybrid doctrine: historical ambitions, rivalries, claims, strategic pressures, and regional interests bias otherwise state-driven strategic decisions.
- <!-- req:REQ-0017 --> Historical pressures are scenario data and modifiers, not scripts. They may raise or lower the attractiveness of wars, objectives, alliances, rivalries, or peace terms, but must not force a war or guarantee a historical outcome when current campaign state no longer supports it.
- <!-- req:REQ-0018 --> State-driven evaluation remains authoritative. AI polities should consider current ownership/control, claims, border and maritime access, settlement and trade-route value, military and naval strength, manpower/supply, treasury and economy, war exhaustion, diplomacy, alliances, threats, terrain, technology, institutions, and other relevant campaign state before choosing war or peace.
- <!-- req:REQ-0019 --> War goals should be limited and explicit where practical: recover or press claims, seize strategic ports or provinces, protect trade or allies, weaken a rival, secure access, suppress rebellion, or pursue broader expansion when conditions justify it. AI should not default to indiscriminate total conquest merely because a target is weaker.
- <!-- req:REQ-0020 --> Peace evaluation should reflect the war's goals, achieved control, relative strength, losses, exhaustion, economic cost, alliance situation, and continuing strategic risk. Terms should be proportionate to plausible objectives and campaign state.
- <!-- req:REQ-0021 --> Historical biases must weaken, disappear, or redirect when alternate-history divergence removes their basis. A polity should not pursue an obsolete historical rivalry or objective forever after the relevant territory, government, alliance, route, or strategic condition has materially changed.
- <!-- req:REQ-0022 --> AI polities use the same authoritative ownership, control, diplomacy, war, military, economy, technology, tradition, save/persistence, and cross-map systems as other campaign actors. Doctrine chooses actions; it does not bypass those systems.
- <!-- req:REQ-0023 --> Decisions must be deterministic from authoritative campaign state plus the campaign's deterministic random source where tie-breaking or bounded variation is useful, so uninterrupted and resumed simulations remain equivalent and testable.
- <!-- req:REQ-0024 --> Historical weighting and state-driven utility coefficients belong in scenario/configuration data rather than hardcoded Age-of-Sail assumptions in shared engine code.
- <!-- req:REQ-0025 --> The goal is a recognizable historical strategic texture without railroading the campaign: plausible historical pressures should be visible, while sufficiently changed world state should produce correspondingly different AI behavior.

## Release-scale content density targets

- <!-- req:REQ-0026 --> The 1450 campaign start should resemble the historically meaningful settlement and political geography of the era rather than assigning an arbitrary equal number of cities to every polity. Large, urbanized, maritime, commercially dense, or administratively complex states should receive correspondingly broader settlement coverage; tiny, nomadic, decentralized, island, or sparsely urbanized polities may legitimately have fewer or differently structured centers.
- <!-- req:REQ-0027 --> Major capitals, ports, fortified towns, trade centers, provincial/regional seats, historically important cities, and locations needed for routes, events, characters, quests, and warfare should be authored at approximately their real locations and associated with the appropriate 1450 polity/province/control situation. Minor villages and communities may remain abstract when representing them physically would add little gameplay value.
- <!-- req:REQ-0028 --> As a release-scale planning target, the global authored settlement catalogue should be on the order of 800-1,200 meaningful settlements, with additional minor communities allowed in abstract state. This is a density target, not a quota: historical geography, map readability, and gameplay relevance take priority over forcing every polity to an equal count.
- <!-- req:REQ-0029 --> Release-scale progression should target roughly 180-250 technologies and 20-30 institutions/reforms across the 1450-1820 span, with meaningful branch depth and era progression rather than long empty gaps.
- <!-- req:REQ-0030 --> Historical/conditional authored event coverage should target roughly 200-300 significant event definitions, with dynamic systems able to produce many more campaign event instances from current world state.
- <!-- req:REQ-0031 --> Quest content should target roughly 400-600 authored campaign/regional/personal/polity/event-linked quests and chains plus a substantial independent catalogue of settlement-local random side-quest families. Local random quests are not the same system as event, campaign, country/polity, personal, or historical quests.
- <!-- req:REQ-0032 --> Military content should target roughly 350-500+ player-facing land/naval types or meaningful variants across common, regional/cultural, polity-specific, elite, era/technology, merchant, transport, specialist, and warship layers. Shared runtime templates remain encouraged where mechanics overlap.
- <!-- req:REQ-0033 --> Player-usable RPG inventory should target roughly 300-500 ordinary equipment/consumable/tool items, 100+ unique/historical/legendary items, and about 50-80 authored equipment sets. Bulk trade goods are a separate economic catalogue and do not substitute for usable RPG inventory.
- <!-- req:REQ-0034 --> Named historical/recruitable hero coverage should target roughly 100-150+ authored characters across regions and eras, with generated officials and minor characters supplementing rather than replacing authored major figures.
- <!-- req:REQ-0035 --> These ranges are release-planning targets rather than hard ceilings. The final content audit should flag clearly thin regions, eras, major powers, gameplay roles, store inventories, progression branches, or quest/event density even if a global raw-count minimum is technically met.

## Technology

- <!-- req:REQ-0036 --> Large technology trees with multiple branches.
- <!-- req:REQ-0037 --> Technology availability/cost changes with historical time.
- <!-- req:REQ-0038 --> Ahead-of-time technology is possible, not absolutely forbidden; extreme early research should be exceptionally expensive/difficult.
- <!-- req:REQ-0039 --> Technologies can have cross-tree prerequisites.
- <!-- req:REQ-0040 --> Institutions/technology adoption can diffuse unevenly through provinces.
- <!-- req:REQ-0041 --> Countries can have unique/special units and other distinct content.

## Player origin, allegiance and titles

- <!-- req:REQ-0042 --> Origin/current allegiance matters and governments reward contribution.
- <!-- req:REQ-0043 --> Rewards can include money, equipment, privileges, special access, titles/peerage and land.
- <!-- req:REQ-0044 --> Allegiance may change; the active government's reward track becomes the relevant one after changing allegiance, subject to reputation/history rules.
- <!-- req:REQ-0045 --> Titles use culturally appropriate names plus a generic tier in parentheses for clarity.
- <!-- req:REQ-0046 --> A sovereign normally grants ranks below its own sovereign tier.
- <!-- req:REQ-0047 --> Empire-tier rulers may grant subordinate king-tier titles/realms where appropriate; this does not make the player the imperial sovereign.
- <!-- req:REQ-0048 --> Land holding, control, sovereignty, autonomy and tax obligations are separate.
- <!-- req:REQ-0049 --> Independent sovereign land has no overlord tax, but still has normal administration/upkeep costs.

## Settlement-level economy and trade identity

- <!-- req:REQ-0050 --> Economic production, consumption, availability, and pricing are primarily settlement-level rather than a single fixed goods list shared by an entire region.
- <!-- req:REQ-0051 --> A region's climate, geography, resources, institutions, trade access, and historical economy should influence what its settlements tend to produce or demand, but settlements within the same region should still differ meaningfully.
- <!-- req:REQ-0052 --> Individual cities and ports may have distinct local specialties, industries, raw materials, manufactured goods, luxury goods, food surpluses, shortages, import dependencies, and trade-service roles according to historical/geographic context and gameplay value.
- <!-- req:REQ-0053 --> Major trade centers and ports may stock many goods they do not produce locally because trade routes, shipping, caravans, warehouses, and merchant activity bring them in.
- <!-- req:REQ-0054 --> A settlement should not be limited to only its signature production good. Signature goods indicate comparative advantage or notable local production, while ordinary local consumption and traded inventory may cover a much broader set.
- <!-- req:REQ-0055 --> Supply, demand, production capacity, war, blockade, occupation, seasonal or historical events, technology, infrastructure, and trade connectivity may change local stock and prices over time.
- <!-- req:REQ-0056 --> Nearby settlements may share some common staple goods while differing in quantities, prices, specialties, imports, and shortages. Avoid making every city unique merely for the sake of uniqueness when shared geography genuinely supports similar production.
- <!-- req:REQ-0057 --> Regional content data should therefore define settlement-specific economic profiles and use region-level rules as modifiers/defaults rather than as the authoritative complete market inventory.
- <!-- req:REQ-0058 --> The current small economy catalog is prototype content and must not be interpreted as the intended final breadth of goods.

## Playable markets and merchant standing

- <!-- req:REQ-0059 --> Settlement commodity markets are player-facing projections of authoritative campaign state. Every quote uses current local stock, supply/demand pressure, production and consumption, imports and connectivity, shortages, war, blockade, occupation, technology, institutions, and active event/quest modifiers. A UI quote is informational and is recalculated when a transaction commits.
- <!-- req:REQ-0060 --> Buying and selling are atomic conserved exchanges of cargo and currency. Cargo must enter an eligible authoritative personal, ship, fleet, warehouse, army, or other explicitly supported store and must respect that store's capacity and commodity compatibility. Warcraft items, units, frames, and cached price text are representations, never the authority.
- <!-- req:REQ-0061 --> Market UI shows the commodity, available quantity, current buy/sell price, recent observed trend, and known realized or projected profit/loss. Exact information and disruption causes are limited to what the player has discovered or unlocked; the UI must not leak undiscovered markets or hidden campaign state.
- <!-- req:REQ-0062 --> Stock movement changes the next quote and large orders use marginal/midpoint pressure. Transaction IDs, persisted market observations, deterministic integer pricing, bounded price floors/ceilings, and campaign-time-driven updates prevent duplicate trades, stale-price arbitrage, save/load rerolls, and unbounded refresh farming.
- <!-- req:REQ-0063 --> Merchant standing is a dedicated persistent player progression value, separate from polity, settlement, country, faction, and character reputation. It rewards legitimate realized trade profit, volume, route distance/difficulty, diversity, reliability, contracts, and rare cargo only through data-authored contributions.
- <!-- req:REQ-0064 --> Repeating the same commodity/route receives diminishing standing, and cargo without a recorded legitimate cost basis may be sold but cannot generate ordinary profit-based standing. Splitting an order, reopening the UI, changing maps, or reloading a save must not reset saturation, repetition, transaction, or cost-basis history.
- <!-- req:REQ-0065 --> Data-defined standing tiers may unlock merchant introductions and specialists, larger or major contracts, warehouse/services access, better market information, convoy opportunities, trade-network privileges, and financing only when a scenario implements authoritative debt and repayment. Standing never silently grants unsupported credit or bypasses government access, war, blockade, technology, institutional, quest, or cultural requirements.
- <!-- req:REQ-0066 --> Market stock/history, cargo stores and cost basis, processed transaction IDs, route/repetition history, realized profit, merchant standing, and unlocked benefits persist in campaign saves and across physical-map transitions. Quests, exploration, ships/fleets, governments, wars, historical events, technologies, and institutions integrate through stable IDs and explicit modifiers rather than hardcoded Age of Sail content in the shared trade engine.

## Characters

- <!-- req:REQ-0067 --> Named recruitable characters have skills, traits, quests and relationships.
- <!-- req:REQ-0068 --> Loyalty/relationship thresholds can produce buffs/debuffs and special content.
- <!-- req:REQ-0069 --> A high-investment permanent loyalty state such as Oathbound is supported.
- <!-- req:REQ-0070 --> Relationships between companions may create synergies or friction.

## Equipment identity, rarity, level, and comparison

- <!-- req:REQ-0071 --> Equipment uses separate, explicit dimensions for power and identity rather than collapsing everything into one rarity label.
- <!-- req:REQ-0072 --> Every player-usable equipment item has a player-facing item level / power level for quick comparison. The intended long-campaign scale supports item levels up to roughly the same order as hero progression (target level cap 300), while scenario data may use narrower bands for specific eras or categories.
- <!-- req:REQ-0073 --> Item level represents the item's overall stat/effect budget and is primarily a comparison aid, not an absolute statement that a higher-level item is always better for every build.
- <!-- req:REQ-0074 --> Rarity/quality is a separate field and should communicate affix/effect complexity, craftsmanship, scarcity, and ceiling. Use a clear ordered ladder such as Common, Fine, Superior, Rare, Epic, Legendary, and Relic/Artifact, with exact labels kept data-driven.
- <!-- req:REQ-0075 --> Identity/provenance is also separate from rarity: generic, regional/cultural, polity-specific, profession/specialist, quest reward, equipment-set piece, unique historical item, legendary/relic, or other authored identity may coexist with any appropriate power level.
- <!-- req:REQ-0076 --> Era, technology, institutions, local production, trade access, settlement wealth, polity/culture, merchant type, and quest/event state determine plausible availability. Historical/unique items remain persistent singular identities unless explicitly authored otherwise.
- <!-- req:REQ-0077 --> Equipment comparison UI should show item level, rarity, major stats/effects, equipment-set membership, requirements, and green/red deltas against the currently equipped item. Build-specific abilities, resistances, passives, set thresholds, and conditional effects must remain visible so a lower-level specialized item can rationally outperform a higher-level generic one.
- <!-- req:REQ-0078 --> Equipment may support bounded enhancement/refinement where appropriate, but enhancement must not erase historical/technological gating or make every old item converge into the same endgame stat block.
- <!-- req:REQ-0079 --> Player-facing stores distinguish bulk trade goods from usable RPG inventory. Settlement merchant types may include general merchants, armourers/weaponsmiths, gunsmiths, tailors/outfitters, apothecaries, booksellers/cartographers, horse dealers, military suppliers, relic/artifact merchants, ship chandlers, and dockyards, with inventory generated from authoritative local context.

## Persistent individual ship progression and refits

- <!-- req:REQ-0080 --> Ships are persistent individual vessels. Two vessels of the same archetype may diverge through installed equipment/refits, crew quality, experience/veterancy, captain/admiral effects, damage/maintenance state, and historical service.
- <!-- req:REQ-0081 --> Ship equipment/refit categories may include armament, hull, rigging/sails, navigation, cargo/logistics, crew/marines, protection/safety, flagship/command facilities, and other historically/plausibly appropriate systems.
- <!-- req:REQ-0082 --> Refit availability is constrained by hull compatibility, campaign year, technology/institutions, polity/region, dockyard capability, resources, money, and other authoritative state.
- <!-- req:REQ-0083 --> Individual ships accumulate persistent experience from meaningful service such as battles, victories, voyages, storms, exploration, trade/escort operations, and other scenario-defined accomplishments.
- <!-- req:REQ-0084 --> Ship experience provides continuous, player-visible improvement rather than bonuses so tiny that normal play cannot perceive them. Early meaningful service should produce a noticeable few-percent improvement; established veteran ships should commonly reach roughly 10-20% effective improvement in relevant areas, while exceptionally long-lived elite/legendary vessels may reach roughly 25-40% combined improvement across selected relevant stats/effects.
- <!-- req:REQ-0085 --> Experience bonuses are distributed by role/history rather than multiplying every stat equally. A veteran gunnery ship may improve reload/accuracy/broadside discipline, while an exploration vessel may improve navigation, storm handling, range, supply efficiency, or maneuvering.
- <!-- req:REQ-0086 --> Continuous veterancy uses diminishing returns or similarly bounded scaling so an ancient obsolete hull does not overpower a vastly superior later design merely through age. Hull, technology, equipment, and era remain the primary power envelope.
- <!-- req:REQ-0087 --> Milestones such as Experienced, Veteran, Elite, Famous, and Legendary layer distinctive traits, passives, or specialization choices on top of continuous scaling.
- <!-- req:REQ-0088 --> Persistent vessel history may record battles, defeated ships, voyages, storms survived, distance sailed, ports visited, discoveries, commanders served under, and other notable service for gameplay, traits, naming, and player attachment.

## Long-campaign hero progression and persistence

- <!-- req:REQ-0089 --> Recruited named heroes persist after their historical initial-availability window closes; the historical window gates first availability/recruitment rather than removing an already recruited hero.
- <!-- req:REQ-0090 --> Recruited heroes must not disappear merely because the historical death/end date is reached. Once recruited, they belong to the campaign's alternate-history state unless removed by an explicit gameplay rule chosen for that campaign.
- <!-- req:REQ-0091 --> The target named-hero level cap is 300 for the long campaign. Levels should provide frequent incremental growth plus regular meaningful perk/ability/mastery decisions rather than hundreds of cosmetic numbers.
- <!-- req:REQ-0092 --> Hero progression is multi-axis: character level, core skills, profession/mastery tracks, personal/signature trees, equipment and sets, relationships, loyalty/Oathbound, titles/offices, command experience, quest unlocks, and other scenario-defined progression may advance independently.
- <!-- req:REQ-0093 --> Late-era historical heroes should enter at a contextually appropriate starting level/skill state based on campaign year, career/reputation, role, and world/player progression rather than universally starting at level 1.
- <!-- req:REQ-0094 --> The recruited strategic hero roster has no arbitrary gameplay cap. Physical co-location is a runtime/performance concern separate from ownership; the initial target for simultaneously instantiated player-side heroes in one active field group is at least 32, and may be raised after performance validation.
- <!-- req:REQ-0095 --> Recruited heroes may instead serve as governors, advisers, army commanders, fleet commanders, specialists, or other remote assignments while retaining one authoritative physical location.
- <!-- req:REQ-0096 --> Ordinary combat defeat of a recruited named hero should default to a recoverable wounded/incapacitated state rather than silently deleting a long-invested character; any permanent-death mode must be an explicit campaign rule rather than the default.

## Units and ownership

- <!-- req:REQ-0097 --> Do not use native WC3 food as the strategic ownership cap.
- <!-- req:REQ-0098 --> Strategic armies/fleets may represent many soldiers/ships without spawning every represented entity simultaneously.
- <!-- req:REQ-0099 --> Economic/logistical cost is the intended practical limiter.
- <!-- req:REQ-0100 --> Summoned units need no special city-damage exception beyond normal rules.

## Unit roster and combat identity

- <!-- req:REQ-0101 --> The ordinary military roster should be predominantly historically grounded for each polity and period, with deliberate gameplay-friendly variance where it improves fun, readability, balance, or faction identity.
- <!-- req:REQ-0102 --> Historical progression matters: unit types, weapons, formations, ships, and battlefield roles should broadly fit the campaign date and technology state rather than appearing arbitrarily centuries early.
- <!-- req:REQ-0103 --> Slight alternate-history divergence is allowed through technology, exceptional national development, player actions, rare content, and balance adjustments; this is not a museum-level simulation.
- <!-- req:REQ-0104 --> Every meaningful combat unit type should have a distinct gameplay identity rather than being only a renamed stat variant. Different types may be distinguished by passive traits, active abilities, auras, formations, weapon behavior, morale or discipline effects, movement rules, resistances, buffs, debuffs, counters, logistics traits, terrain roles, boarding/siege roles, or other scenario-appropriate mechanics.
- <!-- req:REQ-0105 --> Not every unit needs every category of mechanic. Prefer a small number of clear, meaningful traits or abilities per type over ability clutter.
- <!-- req:REQ-0106 --> National/special units may exaggerate real historical strengths for gameplay while remaining recognizable as historically inspired.
- <!-- req:REQ-0107 --> Marines, naval infantry, boarding troops, and other historically appropriate specialist roles are supported where relevant.
- <!-- req:REQ-0108 --> Named/recruitable heroes may use substantially stronger RPG or supernatural mechanics than ordinary units while the surrounding world and normal military roster remain predominantly historical.
- <!-- req:REQ-0109 --> Hero abilities may include persistent mana-powered protection such as a personal Mana Shield that can extend to friendly units within selectable preset ranges. Such group protection uses the hero as the shared mana source, can remain active without a fixed duration while mana is available, and may support self-only and multiple group-range modes.

## Layered military and naval rosters

- <!-- req:REQ-0110 --> Final military content uses layered roster composition rather than requiring every polity to duplicate every ordinary role.
- <!-- req:REQ-0111 --> Common/global archetypes cover roles that genuinely transfer across regions or are useful as shared mechanical bases.
- <!-- req:REQ-0112 --> Regional/cultural families provide historically appropriate local identities, equipment, formations, ship traditions, and ordinary troops.
- <!-- req:REQ-0113 --> Polity-specific variants provide meaningful national/state identity where history or gameplay justifies it.
- <!-- req:REQ-0114 --> Elite, guard, specialist, famous, and otherwise unique formations sit above those shared layers where appropriate.
- <!-- req:REQ-0115 --> Major powers and long-lived militarily important polities should have broader multi-era rosters than minor polities. Minor polities may rely primarily on regional/common families while still receiving distinctive units, modifiers, traditions, or specialists when justified.
- <!-- req:REQ-0116 --> A polity roster is resolved from the authoritative controller/polity, region or culture, campaign date, technology, institutions, reforms, resources, military traditions, and other scenario requirements. Calendar date alone must not grant units whose enabling development has not occurred.
- <!-- req:REQ-0117 --> Unit availability, obsolescence, upgrades, and replacement chains should visibly represent military evolution across the 1450-1820 campaign instead of leaving one early-game signature unit to represent a polity for centuries.
- <!-- req:REQ-0118 --> Settlement garrisons, AI armies, recruitable military units, and other ordinary forces should consume the same authoritative roster families so city defenders do not become a disconnected parallel unit catalogue.
- <!-- req:REQ-0119 --> Naval content is equal in importance to land content for the Age of Sail scenario. Reusable hull/runtime families should support a substantially broader player-facing catalogue of regional, polity-specific, merchant, transport, patrol, raiding, boarding, and warship variants across multiple eras.
- <!-- req:REQ-0120 --> Shared hulls or runtime templates may back several historically distinct player-facing vessels when their mechanics genuinely overlap; visual identity, armament, stats, abilities, requirements, role, and availability may still differ.
- <!-- req:REQ-0121 --> Roster breadth must be judged across regions, polities, roles, and eras rather than by a raw global archetype count.

## Political offices and settlement administration

- <!-- req:REQ-0122 --> Political/administrative office is distinct from legal ownership, territorial holding, control, sovereignty, and title/land ownership. Appointing a character to govern a settlement or province does not by itself transfer the settlement away from the player/controller.
- <!-- req:REQ-0123 --> Every authoritative settlement normally has an administrator or equivalent office holder. The player-facing title should use a culturally and historically appropriate term where practical while exposing a clear generic role such as Administrator or Governor.
- <!-- req:REQ-0124 --> Historically important or well-attested officials may be authored named characters. Otherwise the campaign deterministically generates a culturally appropriate persistent minor official with a plausible personal name, origin, skills, traits, loyalty, age/lifespan data, allegiance, and office identity. Do not expose runtime-style labels such as `Governor_017` to the player.
- <!-- req:REQ-0125 --> Generated officials are lightweight authoritative characters, not anonymous Warcraft units. Their identity remains stable across save/load, map transitions, reconstruction, and inactive-region simulation.
- <!-- req:REQ-0126 --> A settlement acquired or captured by the player/controller automatically receives an acting/local administrator if no eligible explicit appointment exists. The player is never forced through a blocking appointment dialog merely to keep a newly acquired settlement functional.
- <!-- req:REQ-0127 --> The player may replace the automatic administrator with an eligible recruited hero, historical character, generated official, noble/title holder, or other valid character. The player retains normal settlement management authority after delegating administration.
- <!-- req:REQ-0128 --> Administrative jurisdiction may cover one settlement or, for sufficiently capable/high-ranking offices, multiple settlements or an entire province/region. Administrative capacity, rank, skills, government structure, distance, unrest, integration, institutions, technology, and similar factors may affect efficiency.
- <!-- req:REQ-0129 --> A character has one authoritative physical location. Administrative jurisdiction over multiple settlements never creates authoritative clones. A governor travelling with the player may continue to provide permitted remote administrative effects, but cannot simultaneously appear as the same physical combatant in another city.
- <!-- req:REQ-0130 --> Add a scenario-neutral Administration/Governance skill or equivalent administrative rating rather than forcing unrelated skills to represent general civil administration. Other existing skills may provide secondary office effects where relevant.
- <!-- req:REQ-0131 --> Administrator effects may derive from Administration/Governance, Command, Engineering, Tradecraft, Diplomacy, Scholarship, traits, profession, title/rank, local conditions, government form, and scenario modifiers. Different strengths should produce meaningfully different economic, construction, unrest, institution, supply, garrison, defense, or recovery outcomes.
- <!-- req:REQ-0132 --> Appointment, promotion, tenure, demotion, dismissal, dispossession, and other office changes may affect character loyalty and relationships. Rewards must depend on meaningful prestige/responsibility change and history so repeatedly appointing/dismissing the same character cannot farm loyalty.
- <!-- req:REQ-0133 --> Oathbound remains the permanent high-loyalty state: ordinary negative office consequences cannot reduce an Oathbound character's loyalty.
- <!-- req:REQ-0134 --> Removing a sufficiently disloyal, powerful, locally supported, or militarily entrenched administrator may create refusal, defection, mutiny, rebellion, separatism, or related events according to explicit authoritative conditions. Risky removal must present a useful warning rather than surprise the player with an unexplained settlement loss.
- <!-- req:REQ-0135 --> Office state, jurisdiction, appointment history, administrative effects, succession/replacement state, and any rebellion consequences are authoritative campaign data and persist across saves and physical-map transitions.
- <!-- req:REQ-0136 --> Major polities should eventually have appropriate ruler/sovereign or collective-governance representation in addition to settlement administrators. Decentralized or collective political structures must not be forced into a fake singular monarch solely to satisfy the office system.
- <!-- req:REQ-0137 --> The same office framework may support settlement administrators, provincial governors, sovereign/ruler roles, army commanders, and fleet commanders while keeping the responsibilities and gameplay effects of each office distinct.

## Settlement administrator presentation and local defense

- <!-- req:REQ-0138 --> Every governed settlement exposes its administrator clearly through the settlement/government UI, including name, culturally appropriate office title, loyalty where knowable, relevant skills/traits, jurisdiction, residence/physical location, capacity/efficiency, and major active effects.
- <!-- req:REQ-0139 --> Each settlement has a recognizable government/administration interaction point or equivalent presentation appropriate to its visual set. If the administrator is physically resident and locally instantiated, their actual character representation may appear there with a clear name/title treatment.
- <!-- req:REQ-0140 --> If the appointed administrator is physically elsewhere, do not instantiate a duplicate of that character. A deterministic deputy/local official or abstract office representation may stand in locally and should be identified as acting on behalf of the absent administrator where appropriate.
- <!-- req:REQ-0141 --> Settlement defenders are authoritative local-defense/garrison state, not free player army units. When physically instantiated they use a dedicated allied/AI defense controller and are not directly commandable by the player even when defending a player-controlled settlement.
- <!-- req:REQ-0142 --> Players must not be able to exploit settlement defenders as free expeditionary troops, cargo, equipment sources, disposable recruitment, or permanent field armies.
- <!-- req:REQ-0143 --> A settlement under attack instantiates its currently available garrison/local-defense force. If combat remains active, additional reinforcement waves may spawn after data-driven intervals only while authoritative reserve/manpower/supply remains available.
- <!-- req:REQ-0144 --> Reinforcement waves are bounded by persistent garrison strength, reserves, manpower, supply, buildings, policies, and other authoritative limits. A settlement must never produce infinite defenders merely because an attack remains in progress.
- <!-- req:REQ-0145 --> Garrison casualties and resource expenditure persist back into authoritative state. After a data-driven combat-quiet period, unnecessary runtime defenders may despawn and the surviving force is represented abstractly again; defenders must not instantly reset to full strength.
- <!-- req:REQ-0146 --> Garrison replenishment outside combat follows explicit campaign rules and consumes appropriate time/resources/manpower rather than occurring as a free runtime respawn.
- <!-- req:REQ-0147 --> Defender composition and strength may change over the campaign according to controlling polity, region/culture, campaign date, technology, institutions, reforms, available resources, settlement class, fortifications, buildings, military traditions, administrator skills/traits, wealth/manpower, unrest, recent conquest, and other scenario data.
- <!-- req:REQ-0148 --> Technology and institutional progress may unlock different defender types, improved equipment, additional specialists/artillery, larger or better-organized reserves, stronger fortifications, or other qualitative changes; defender progression is not limited to flat stat scaling.
- <!-- req:REQ-0149 --> Administrator Command, Administration/Governance, Engineering, Tradecraft and other relevant abilities may improve organization, reserve readiness, morale, fortification repair, supply, reinforcement cadence, or similar bounded defense effects, but cannot create manpower or unavailable technology from nothing.
- <!-- req:REQ-0150 --> A resident administrator/commander may join the AI-controlled settlement defense as their actual character. An absent administrator does not appear as a combat clone; a deputy/local commander handles local defense instead.
- <!-- req:REQ-0151 --> Existing City Core capture and defensive-layout reconstruction rules remain authoritative. The local-defense system extends those rules rather than replacing the ownership/control/capture model.

## Controller military traditions

- <!-- req:REQ-0152 --> Player-controlled forces and AI-controlled polities maintain independent persistent military-tradition progression rather than sharing one global combat-experience value.
- <!-- req:REQ-0153 --> Traditions are controller-scoped and category-specific. Scenario data may define tracks such as infantry, cavalry, artillery, naval, marine/boarding, siege, or other appropriate military categories without hardcoding those names into the shared engine.
- <!-- req:REQ-0154 --> Relevant combat by a unit contributes experience to its controller's matching tradition track. Enemy kills are a primary supported source; scenario/balance data may also award weighted experience for other meaningful combat contribution so the system is not tied only to literal last-hit ownership.
- <!-- req:REQ-0155 --> Tradition progression benefits all currently controlled units that qualify for that tradition category, including units represented abstractly while another physical map is active. Runtime units receive the derived modifiers when instantiated or when controller/tradition state changes.
- <!-- req:REQ-0156 --> Tradition belongs to the controller, not permanently to the individual unit. If a unit changes controller, its controller-wide tradition modifiers are recalculated from the new controller's state; the previous controller keeps its accumulated tradition.
- <!-- req:REQ-0157 --> The core numerical tradition bonus is continuous and experience-proportional rather than a discrete level table. Do not require fixed "level X -> bonus Y" thresholds for ordinary stat progression: every additional unit of valid tradition experience should contribute proportionally according to the tradition's data-driven coefficient/curve (for example, if 100 XP grants Y bonus, 1,000 XP grants 10Y under a linear coefficient).
- <!-- req:REQ-0158 --> Controller tradition experience has no ordinary hard progression ceiling or maximum tradition level. Long-running player and AI controllers may continue improving as they accumulate valid experience across the campaign. Balance should come from experience rates, coefficients, opposing progression, costs, counters, and scenario tuning rather than an arbitrary cap that makes further combat experience worthless.
- <!-- req:REQ-0159 --> Milestone thresholds may unlock additional category-wide buffs, passive effects, doctrines, formations, morale/discipline mechanics, logistics advantages, or other qualitative rewards once the controller reaches the required tradition experience.
- <!-- req:REQ-0160 --> Milestone rewards are additive to the continuous XP-derived progression and must not replace, cap, reset, or stall it. Reaching 10,000 XP may grant a milestone buff while 10,001 XP still gives a slightly larger continuous numerical bonus than 10,000 XP.
- <!-- req:REQ-0161 --> Reached milestone rewards remain active for that controller/tradition and normally stack with earlier milestones unless a specific scenario-defined milestone explicitly upgrades/replaces an earlier effect.
- <!-- req:REQ-0162 --> Milestone XP thresholds and effects are data-driven per tradition, so different military categories may have different milestone spacing and rewards.
- <!-- req:REQ-0163 --> Do not require every tradition to raise every numerical stat. Each tradition's affected attributes and coefficients are data-driven so infantry, cavalry, artillery, naval, and other categories can scale differently while preserving their distinct roles.
- <!-- req:REQ-0164 --> Tradition state is authoritative campaign data and must persist across saves, physical-map transitions, inactive-region simulation, and remote command.
- <!-- req:REQ-0165 --> AI controllers use the same progression rules as the player unless scenario data deliberately defines a historical/special starting value or modifier.

## Religion and faith traditions

- <!-- req:REQ-0166 --> Religion is a reusable, scenario-neutral system. Faith traditions, denominations,
  reforms, schisms, syncretic and local traditions, their relationships, labels,
  influence curves, and benefit profiles are scenario data; the engine contains no
  closed list of religions.
- <!-- req:REQ-0167 --> Personal faith/affiliations, polity-supported faiths, government tolerance or
  persecution policy, settlement/province population composition, institutions,
  and global influence are separate authoritative domains. A character may be
  non-aligned or carry weighted affiliations; a polity may support multiple or no
  faiths; a mixed region is not collapsed into its largest community.
- <!-- req:REQ-0168 --> Current influence is recomputed from authoritative population shares, active
  centers and institutions, government support, prestige, and persistent event
  effects. Alternate-history rise, decline, reform, and suppression therefore alter
  effects dynamically instead of preserving a frozen historical starting score.
- <!-- req:REQ-0169 --> A main character's passive benefits combine two independent inputs: personal
  investment/progression and current campaign influence. Both axes use deterministic
  integer diminishing-return curves, and each scenario-authored attribute has a hard
  cap. Benefit profiles are narrow and thematic, never blanket statistical
  superiority.
- <!-- req:REQ-0170 --> Conversion is an atomic campaign action with an explicit cost, deterministic
  sequence, campaign time, prior/new faith, and reputation consequences. Its history
  is authoritative and cannot be rerolled by loading or changing maps.
- <!-- req:REQ-0171 --> The system exposes stable context (personal faith, government support, local
  share, policy, institutional state) to quests, events, diplomacy, offices,
  settlement unrest/stability, recruitment, and content availability. Those systems
  decide their scenario-authored outcomes; Warcraft objects are not authority.
- <!-- req:REQ-0172 --> Faith state, regional composition, policies, institutions, influence inputs,
  conversion history, and derived-effect inputs persist across saves and physical-map
  transitions. Runtime modifiers and the religion overview are reconstructed. The
  overview names each benefit and cap and explains the current personal-investment
  and campaign-influence inputs.
- <!-- req:REQ-0173 --> Deterministic tests cover mixed regions, rise and decline, alternate-history
  divergence, conversion history, independent scaling axes, diminishing caps, and
  1450-1820 save/resume equivalence.

## City capture

- <!-- req:REQ-0174 --> Civilian facilities are invulnerable.
- <!-- req:REQ-0175 --> Military defenses are destructible.
- <!-- req:REQ-0176 --> Each capturable settlement has an authoritative City Core/capture structure.
- <!-- req:REQ-0177 --> Destruction of the valid enemy City Core during a legal conflict triggers capture.
- <!-- req:REQ-0178 --> On capture, controller changes, old military defenses are cleaned up, and the city's predefined defensive layout respawns at its original locations under the new controller.
- <!-- req:REQ-0179 --> New defenses receive exactly 5 seconds of post-capture immunity/capture cooldown to prevent immediate hostile survivor/third-party recapture loops.
- <!-- req:REQ-0180 --> City functionality must not become irrecoverably broken because an object was unexpectedly destroyed.
- <!-- req:REQ-0181 --> Persistent city state is authoritative; Warcraft object instances are representations of that state.

## Saving

- <!-- req:REQ-0182 --> Native Warcraft save/load must be regression-tested and must not intentionally be broken.
- <!-- req:REQ-0183 --> Separate versioned campaign persistence is required for long-term compatibility.
- <!-- req:REQ-0184 --> 15 rolling timed autosave slots.
- <!-- req:REQ-0185 --> Manual save slots.
- <!-- req:REQ-0186 --> Separate session-start and major-milestone recovery checkpoints.
- <!-- req:REQ-0187 --> Autosaves should defer during unsafe transitional states instead of serializing half-completed state changes.
- <!-- req:REQ-0188 --> Save data includes format/build/scenario version metadata and integrity checks.
- <!-- req:REQ-0189 --> Save-format changes require migrations whenever practical.
- <!-- req:REQ-0190 --> Failed/incompatible loads must not overwrite the original save.

## Recovery commands

- <!-- req:REQ-0191 --> `/unstuck` applies to selected eligible mobile units.
- <!-- req:REQ-0192 --> If no eligible selection exists because nothing is selected, it may recover the main character.
- <!-- req:REQ-0193 --> Mixed selections move eligible mobile units and skip structures.
- <!-- req:REQ-0194 --> If only ineligible objects such as buildings are selected, report the issue and do not silently move something else.
- <!-- req:REQ-0195 --> Buildings, walls, towers, city cores, destructibles and dummy/system units must never be moved by `/unstuck`.
- <!-- req:REQ-0196 --> Recovery must be connectivity-aware, not merely pathability-aware.
- <!-- req:REQ-0197 --> Ships must not be moved into isolated/decorative lakes or disconnected water.
- <!-- req:REQ-0198 --> Land units must not be moved onto unreachable/disconnected land.
- <!-- req:REQ-0199 --> Track last-known-safe position/navigation zone for important active units.
- <!-- req:REQ-0200 --> Prefer nearby reachable safe position, then verified last-safe position, then a valid connected recovery anchor.
- <!-- req:REQ-0201 --> If safety cannot be proven, fail without moving the unit.
- <!-- req:REQ-0202 --> `/unstuck all` may operate on physically active player-controlled mobile units in the current relevant region, never abstract world entities.

## Commands

- <!-- req:REQ-0203 --> `/help` lists player commands.
- <!-- req:REQ-0204 --> Help is paged: `/help 2`, `/help 3`, etc.
- <!-- req:REQ-0205 --> Topic help is supported, e.g. `/help unstuck`.
- <!-- req:REQ-0206 --> Invalid page numbers produce a clear message.
- <!-- req:REQ-0207 --> Release builds hide internal developer/debug commands.
- <!-- req:REQ-0208 --> A player-facing `/god` command is provided so native `whosyourdaddy` is unnecessary for recovery.
- <!-- req:REQ-0209 --> `/god` applies to all player-controlled runtime entities, not only the main character. This includes player-controlled heroes/companions, ordinary units, summons, ships, structures, and any other controllable Warcraft runtime objects.
- <!-- req:REQ-0210 --> While `/god` is enabled, newly created, spawned, acquired, or otherwise transferred player-controlled runtime entities inherit the same protection automatically.
- <!-- req:REQ-0211 --> `/god` toggles the mode; `/god on` and `/god off` are idempotent explicit forms.
- <!-- req:REQ-0212 --> The mode is a session/recovery convenience rather than campaign progression. It is excluded from custom campaign persistence and defaults to OFF for a new session and after loading campaign state.
- <!-- req:REQ-0213 --> If protected runtime objects are reconstructed while `/god` remains enabled in the same active session, protection is reapplied to their replacements.
- <!-- req:REQ-0214 --> Command feedback must clearly report whether player-wide god mode is ON or OFF.

## UI pause policy

- <!-- req:REQ-0215 --> The campaign is single-player, so opening a modal management screen pauses the entire campaign simulation.
- <!-- req:REQ-0216 --> While a modal management screen is open, campaign time progression, strategic AI actions, combat/travel simulation, economy ticks, and event progression are paused.
- <!-- req:REQ-0217 --> Inventory/equipment, character/companion management, technology, economy/trade management, titles/land/government, fleet/army management, journal/encyclopedia, and full strategic-management/map screens are modal for this policy unless deliberately reclassified later.
- <!-- req:REQ-0218 --> Passive/non-modal UI such as HUD panels, tooltips, notifications/toasts, and small informational overlays does not pause the campaign.
- <!-- req:REQ-0219 --> Nested/modal screen transitions keep the campaign paused until the final modal management screen closes.
- <!-- req:REQ-0220 --> Closing a management screen must restore the pause state that existed before the first modal management screen opened; it must not unpause a game that the player had already manually paused.

## World-map representation and regional traversal

- <!-- req:REQ-0221 --> The purpose of regional partitioning is to make the playable world physically larger than Warcraft III's single-map terrain ceiling. The full world must therefore not be packed into one physical `.w3x`.
- <!-- req:REQ-0222 --> A logical world region is backed by one or more separate physical Warcraft map files/submaps. Each physical map receives its own terrain-size budget, and a large logical region such as Europe may use multiple physical maps when needed for geographic scale, density, or performance.
- <!-- req:REQ-0223 --> The current single `AgeOfSailWorld.w3x` remains only a bootstrap/runtime-validation map while the multi-map campaign pipeline is implemented; it is not the intended final container for all world terrain.
- <!-- req:REQ-0224 --> Crossing a valid land or sea boundary saves/commits authoritative campaign state, changes to the geographically adjacent physical map, and reconstructs the player and other locally relevant runtime representations at the corresponding entry boundary.
- <!-- req:REQ-0225 --> Regional adjacency follows real-world geography and compass direction. For example, leaving Europe westward across the Atlantic leads toward eastern North America; leaving Europe eastward leads toward Asia/Middle East rather than America.
- <!-- req:REQ-0226 --> Ordinary geographic transitions should be edge-to-edge rather than requiring the player to enter an arbitrary trigger circle: reaching a valid shared map boundary transfers to the corresponding boundary of the adjacent physical map.
- <!-- req:REQ-0227 --> Preserve the player's position along the shared boundary using a normalized/correspondence coordinate rather than assuming identical raw Warcraft coordinates. For example, crossing 37% of the way along one map's west edge should normally place the player about 37% of the way along the geographically corresponding east edge of the destination map; reverse or transform the coordinate where edge orientation/geographic projection requires it.
- <!-- req:REQ-0228 --> If neighboring maps deliberately use identical aligned edge scales, the raw coordinate may remain effectively unchanged (for example source y=100 -> destination y=100).
- <!-- req:REQ-0229 --> Boundary arrival may snap only as much as necessary to the nearest valid connected land/water/pathable entry point, avoiding cliffs, blocked terrain, decorative water, or other invalid spawn positions while retaining the intended geographic correspondence.
- <!-- req:REQ-0230 --> Long-distance ocean travel may use direct region-to-region routes with campaign-time advancement and encounter/event hooks rather than requiring enormous continuously rendered oceans. Dedicated ocean/encounter maps may be used where gameplay benefits.
- <!-- req:REQ-0231 --> Each physical map uses gameplay-compressed geography while preserving recognizable coastlines, relative direction, major geographic relationships, settlement ordering, and important travel routes. Empty distance may be compressed, but splitting into maps should be preferred over crushing an entire continent into an implausibly small area merely to fit one map.
- <!-- req:REQ-0232 --> Regions/maps not currently loaded remain authoritative abstract campaign state. Their armies, fleets, settlements, characters, economy, wars, and events continue through strategic simulation without keeping their Warcraft object representations loaded.
- <!-- req:REQ-0233 --> Cross-map transitions must preserve authoritative character, unit, party, fleet, quest, inventory, settlement, diplomacy, economy, technology, and campaign state. Transient Warcraft objects are reconstructed from stable IDs/state after a map loads.
- <!-- req:REQ-0234 --> Revisiting a previously visited physical map should restore/reconstruct its authoritative changed state rather than reset conquered cities, destroyed/rebuilt defenses, moved armies, completed quests, market state, or other persistent campaign changes.
- <!-- req:REQ-0235 --> Prefer versioned authoritative campaign-state serialization/reconstruction over depending on opaque raw Warcraft map-save state as the sole source of truth. Native campaign/game-cache or map-transition facilities may be used as transport/bootstrap mechanisms where reliable.
- <!-- req:REQ-0236 --> Transition boundaries, physical-map IDs, adjacency, entry points, and map-package paths must be explicit scenario data so geography/navigation remains reusable and testable.

## Geographic fidelity and Europe content scope

- <!-- req:REQ-0237 --> Regional terrain should be derived from real-world geography and then scaled down for Warcraft play. Real-world location, compass direction, relative placement, coastline shape, major distance relationships, and connectivity are the starting point rather than hand-authored fantasy layouts.
- <!-- req:REQ-0238 --> Use a broadly consistent base scale within and between neighboring regions, with controlled local distortion only where Warcraft object scale, readability, pathing, performance, or gameplay spacing requires it.
- <!-- req:REQ-0239 --> Important locations must remain geographically sensible relative to one another. A city, port, river, island, mountain range, strait, or neighboring polity should not be moved to a contradictory side of another feature merely to fill space.
- <!-- req:REQ-0240 --> Divide Europe into as many regional instances as are needed to preserve the chosen geographic scale and performance budget. Region boundaries should follow practical low-density, maritime, mountain, or other natural seams where possible rather than being forced to match modern national borders.
- <!-- req:REQ-0241 --> Europe uses the political situation at the 1450 campaign start as its historical baseline. Include major sovereign and de-facto polities plus smaller states that materially affect warfare, diplomacy, trade, quests, or regional identity. Extremely fine political fragmentation may be simplified for terrain readability, but historically important entities should remain representable in authoritative scenario state.
- <!-- req:REQ-0242 --> Provinces/states should use historically meaningful regional or administrative groupings where practical, merging only when the real subdivision is too fine to produce useful Warcraft gameplay.
- <!-- req:REQ-0243 --> Settlement coverage should prioritize capitals, major ports, major trade centers, strategically important fortified towns, and locations needed for historical events, characters, quests, or travel. The map is not required to include every real village.
- <!-- req:REQ-0244 --> Port coverage should include historically/gameplay-significant coastal and river ports needed for naval movement, trade, exploration, diplomacy, and regional transitions.
- <!-- req:REQ-0245 --> Preserve recognizable major coastlines, islands, rivers, mountain systems, straits, and other navigation-defining terrain. Small-scale terrain detail and border wiggles may be generalized.
- <!-- req:REQ-0246 --> Political borders should broadly match the selected historical baseline at campaign start, then evolve through the normal ownership/control/war systems rather than remaining visually or logically fixed.
- <!-- req:REQ-0247 --> The same real-geography-first scaling rule is the default for every later Phase 5 world region, including Africa, the Middle East/India, Southeast Asia, East Asia, the Americas/Caribbean, and the Pacific.
- <!-- req:REQ-0248 --> Do not request a new player design decision merely to repeat the same regional-scope questions for each continent. Region boundaries, compression, included polities, provinces, settlements, ports, terrain, borders, and travel connections should be derived from these locked rules, historical/geographic evidence, gameplay relevance, and performance budgets.
- <!-- req:REQ-0249 --> Region-specific historical features such as trans-Saharan routes, Indian Ocean trade, major straits, island chains, caravan corridors, or similar geography are implementation/research details under this rule, not separate player design blockers unless they expose a genuinely new gameplay choice not covered here.
- <!-- req:REQ-0250 --> Create a new regional `needs-design` blocker only when a materially new player-facing design choice cannot be resolved from the existing design lock, historical/geographic evidence, or established performance constraints.

## Treasures and secrets discovery

- <!-- req:REQ-0251 --> Campaign treasures and secrets use a hybrid deterministic model.
- <!-- req:REQ-0252 --> Historically meaningful or unique treasures keep fixed authored identity, historical/geographic context, and an appropriate fixed anchor region or location family. They must not be randomized into historically implausible parts of the world.
- <!-- req:REQ-0253 --> Within that historical anchor, the exact valid hiding place may vary deterministically per campaign among authored/geographically valid candidates. Secondary loot, guards, encounters, hazards, or supporting rewards may also vary deterministically.
- <!-- req:REQ-0254 --> Generic caches, pirate hoards, wreck salvage, hidden stores, ruins, and similar non-unique secrets may vary more freely, but still only within scenario-appropriate regions, terrain, navigation zones, and content pools.
- <!-- req:REQ-0255 --> Deterministic variation is derived from persistent campaign seed/state. Reloading, changing physical maps, revisiting a region, or restoring a save must not reroll a treasure's resolved location, reward variant, encounter, or discovery state.
- <!-- req:REQ-0256 --> Once a treasure/secret is resolved for a campaign, its authoritative result persists across saves, cross-map transitions, reconstruction, and inactive-region simulation.
- <!-- req:REQ-0257 --> Discovery may progress through hidden, region-only, approximate search-area, narrowed search-area, and exact-known states using the existing discovery/map/quest knowledge model.
- <!-- req:REQ-0258 --> Clues and search areas must always refer to the campaign's actual resolved treasure location and must never reveal information more precise than the player has earned.
- <!-- req:REQ-0259 --> A historically unique artifact normally keeps its unique identity/reward while its exact hiding place and secondary rewards may vary. Generic treasure rewards may be selected from deterministic, scenario-defined pools.
- <!-- req:REQ-0260 --> Treasure placement must validate accessibility, terrain/navigation compatibility, physical-map assignment, duplicate/exclusive placement rules, and conflict with settlements or other reserved content before campaign state is committed.
- <!-- req:REQ-0261 --> Treasure generation must be reproducible from the same campaign seed and authoritative inputs for testing, migration, and recovery.

## Settlement-local random side quests

## Government contribution rewards

- <!-- req:REQ-0262 --> Government contribution rewards are polity-owned profiles, never one global
  reward table copied to every country. Profile coverage is mandatory for every
  active polity and may define its own culturally and politically appropriate
  money, equipment, office, privilege, access, title, land, favor, reputation,
  promise, and military or naval support tracks.
- <!-- req:REQ-0263 --> A profile's 1450 means are only its starting fallback. Every offer is resolved
  again from authoritative campaign state, including liquid treasury, economic
  and trade strength, controlled territory, war exhaustion and strategic urgency,
  military/naval condition, technology and institutions, ruler/government state,
  player reputation and favor, current allegiance, immutable origin, prior
  service, contribution type/magnitude, scarcity, and already-granted history.
- <!-- req:REQ-0264 --> Collapse cannot mint cash, equipment, units, titles, offices, or land that the
  polity cannot fund, supply, authorize, or control. Weak states remain attractive
  through their own affordable favors, privileges, access, exemptions, offices,
  promises, claims, and honors; alternate-history prosperity or expansion raises
  practical capacity rather than preserving a historical poverty ceiling.
- <!-- req:REQ-0265 --> Origin and current allegiance are separate fields. Allegiance controls ordinary
  service eligibility; origin is consulted only by explicitly authored
  history-sensitive rewards and never silently substitutes for allegiance.
- <!-- req:REQ-0266 --> Contribution source keys and grant keys are persistent and unique. Reward-track
  progress, consumed uniqueness/scarcity, and full grant history survive save/load
  and map transitions; title/office/land grants are non-repeatable and land must be
  under current polity control when offered and again when the transaction commits.
- <!-- req:REQ-0267 --> Explicit exceptional story/quest rewards may bypass ordinary affordability only
  through an authored override. Such overrides still obey stable identity,
  uniqueness, historical justification, and authoritative grant persistence.

- <!-- req:REQ-0268 --> Settlement-local random side quests are a distinct quest category. They must not be conflated with campaign quests, historical/event quests, country/polity quests, personal hero quests, scripted regional chains, treasures, or other authored story content.
- <!-- req:REQ-0269 --> Local random quests come from authored quest families/variants and are deterministically selected for settlements from campaign seed plus the settlement's starting/local context. They are not free-form dynamically generated narrative and must retain authored objectives, dialogue/description structures, reward rules, failure rules, and validation.
- <!-- req:REQ-0270 --> At campaign start, every ordinary playable settlement should normally expose at least one local random side quest. Sparse/remote locations may have only one or a very small pool, while larger, wealthier, denser, more connected, administratively important, militarily important, or commercially active settlements should support more simultaneous local quest opportunities.
- <!-- req:REQ-0271 --> Quest-slot density should follow settlement role and starting state rather than a flat quota. As an initial balancing shape: remote outposts/anchorages commonly expose about 1; small settlements about 1-2; ordinary towns about 2-4; major cities/ports about 4-7; and major capitals/metropolises about 6-10. These are tuning ranges, not mandatory exact counts.
- <!-- req:REQ-0272 --> Eligible local quest families depend on contextual tags such as settlement size/roles, polity/culture, economy and shortages, local production/trade, port/river/frontier status, nearby terrain/routes, administration, garrison/defense, crime/unrest, religion/culture where represented, professions/services, technology/era, and other authored starting/local state. A fishing-port quest pool should not be interchangeable with an inland court or frontier fort.
- <!-- req:REQ-0273 --> Random selection is deterministic and persistent. Save/load, map transitions, reopening a quest board, or re-entering a settlement must not reroll offers. Completed/failed/expired local quests may be replaced later only through explicit data-driven refill/cooldown rules.
- <!-- req:REQ-0274 --> Repetition must be bounded and varied. The same quest family may appear in multiple suitable settlements, but objectives, target locations, actors, quantities, risks, rewards, and authored variants should provide enough variation that the world does not read as one cloned noticeboard.
- <!-- req:REQ-0275 --> Local random quests may award money/currency, ordinary or rare equipment, region/culture/polity-appropriate equipment, consumables, materials/cargo, experience, skill/mastery progress, settlement reputation, polity/country reputation or favor, faction/profession reputation, access/services/discounts, information/discovery, and other scenario-defined rewards.
- <!-- req:REQ-0276 --> A local quest that materially helps a settlement, polity, army/fleet, trade network, or government may also apply a proportional authoritative world-state benefit where fictionally and mechanically appropriate, such as improved local prosperity, supply/readiness, garrison recovery, trade throughput, stability, reduced unrest, temporary polity modifiers, treasury/resources, diplomatic goodwill, or similar bounded effects.
- <!-- req:REQ-0277 --> Country/polity benefits are consequences of what the quest actually accomplished, not an automatic extra reward on every local errand. Helping a polity should normally improve the player's standing with it; larger strategic benefits require correspondingly relevant objectives.
- <!-- req:REQ-0278 --> Unique historical items, singular relics, major titles, permanent polity-scale modifiers, and other exceptional rewards must obey uniqueness and authored-gating rules and must not enter a repeatable/random reward table merely because they have an item/reward ID.
- <!-- req:REQ-0279 --> Reward value scales with difficulty, travel/time, danger, scarcity, settlement/polity means, relationship, era, and strategic significance. Repeatable/local-random content must include anti-farming rules so deterministic rerolls or trivial loops cannot print money, reputation, equipment, or permanent country buffs.
- <!-- req:REQ-0280 --> Local quest state remains authoritative even while its physical map is inactive. Accepting, completing, failing, expiring, or replacing a local quest must preserve stable IDs and deterministic reconstruction across save/load and map transitions.

## Quest location and map assistance

- <!-- req:REQ-0281 --> The quest journal must retain stable-ID location context for quest givers, turn-in locations, objectives, relevant settlements, regions, and other known destinations so the player is not required to remember where a quest originated.
- <!-- req:REQ-0282 --> Quest entries should provide a direct `Show on Map` / `Track` action where a meaningful destination exists.
- <!-- req:REQ-0283 --> Showing a quest on the map should open or focus the appropriate world/region map context, select the relevant region and settlement/location, and visibly mark the destination.
- <!-- req:REQ-0284 --> For cross-region objectives, the helper should show a useful route breadcrumb through known region transitions from the player's current physical region to the destination, e.g. current region -> ocean/adjacent region -> target region -> target settlement.
- <!-- req:REQ-0285 --> When the player reaches the destination region, the helper may provide a local marker, minimap ping, or directional indicator toward the known quest location.
- <!-- req:REQ-0286 --> Returning to a quest giver or turn-in point must be supported explicitly; completed objectives should still retain their return destination until the quest is actually turned in.
- <!-- req:REQ-0287 --> Visiting a settlement or accepting a quest there is sufficient to record that settlement as known for later navigation.
- <!-- req:REQ-0288 --> Quest/map assistance must not reveal unrelated undiscovered geography, hidden locations, secret objectives, or information the quest intentionally withholds. A quest may reveal an exact destination, only a region, an approximate search area, or no marker at all according to its scenario data.
- <!-- req:REQ-0289 --> Approximate quest knowledge should be visualized as a bounded search area rather than a false precise point. For example, a clue such as "somewhere in the Amazon" may highlight or ping a large circle/region covering the plausible search area.
- <!-- req:REQ-0290 --> Search areas may shrink, move, split, or become an exact marker as the player obtains better clues, explores, talks to characters, finds maps, or completes intermediate objectives.
- <!-- req:REQ-0291 --> The displayed uncertainty area is informational and should reflect only the precision of the clues actually known to the player.
- <!-- req:REQ-0292 --> Previously discovered exact locations may be shown precisely even when a later quest clue is broader. If the player has already visited or otherwise explicitly discovered the specific settlement, landmark, ruin, dungeon, port, or other destination and that knowledge is recorded in campaign state, the quest/map helper may use the exact known marker instead of downgrading it to a broad search area.
- <!-- req:REQ-0293 --> Revealing general fog-of-war or exploring a region does not automatically identify every hidden point of interest inside it; precise quest markers require that the destination itself is known or has been explicitly revealed by the quest/clue.
- <!-- req:REQ-0294 --> The world/region map should support centering or focusing on a known named settlement/location without physically moving the player's character.
- <!-- req:REQ-0295 --> Quest navigation is informational only: tracking or viewing a destination does not teleport units or bypass travel.

## Remote regional management

- <!-- req:REQ-0296 --> The player can manage owned or authorized holdings in other regions without physically traveling there.
- <!-- req:REQ-0297 --> Remote regional access supports both management and active command. Switching to another owned/authorized region changes the camera and control context to that region so the player can click buildings and directly command eligible local troops there.
- <!-- req:REQ-0298 --> Entering a remote regional management view does not move the player's character, party, army, fleet, or authoritative physical campaign location.
- <!-- req:REQ-0299 --> Remote regional management is modal and follows the existing campaign pause policy.
- <!-- req:REQ-0300 --> If the requested command region is on another physical map, switching active command context may load that map and reconstruct the eligible local military/building/character representations there. The main character's authoritative location remains unchanged unless the character actually travels.
- <!-- req:REQ-0301 --> The player's main character keeps a separate physical-region/map location from the current command/view region. Leaving remote command can load/reconstruct the character's physical map and return control there without teleporting the character through the world model.
- <!-- req:REQ-0302 --> Multiple regions may contain player-owned troops and holdings at the same campaign time. Only the currently active command region needs full local Warcraft representations; player forces in other regions continue executing strategic orders and simulation in abstract state until their region becomes active.
- <!-- req:REQ-0303 --> Switching active command regions must preserve ongoing orders, battles, construction, movement, and other authoritative state so activity continues coherently across the whole world.
- <!-- req:REQ-0304 --> The feature may be opened from a world/region selector and by a player-facing command; exact command syntax can be chosen during UI implementation.
- <!-- req:REQ-0305 --> Remote management shows only campaign information the player is already authorized to know.

## Player-facing country interaction and negotiated peace

- <!-- req:REQ-0306 --> The player remains an individual. A country screen is reachable from a known
  country, its known ruler/government, map context, or a relevant quest; every
  entry path applies the same persistent discovery filter.
- <!-- req:REQ-0307 --> The screen reports the current relation and war state, whether the player
  currently serves the polity, immutable-origin/history relevance, reputation,
  favor and service standing, known government, active wars, discovered
  partners, territorial disputes/occupations, and currently eligible government
  interactions. Unknown rulers, partners, wars, territory, and clauses are not
  inferred merely because they exist in authoritative simulation state.
- <!-- req:REQ-0308 --> Serving, allegiance changes, rewards, privileges/access, and negotiations are
  eligibility-checked at commit time. Origin never changes with allegiance.
  Reward and access grants remain subject to their owning authoritative systems.
- <!-- req:REQ-0309 --> An active war involving the player or the polity they represent exposes a
  proper offer/response flow. Every offer names its conflict, parties, explicit
  terms, creation/expiry time, and initiator. AI governments may create offers
  through the same validation and persistence boundary as the player.
- <!-- req:REQ-0310 --> Territory terms identify province/settlement, grantor, and beneficiary. The
  grantor must legally own the territory and must either control it or be ceding
  it to its current wartime occupier. Every occupation is resolved explicitly at
  peace: named cessions transfer title and control; otherwise occupied territory
  returns to its legal owner. Territory state, not a Warcraft object, is final.
- <!-- req:REQ-0311 --> Treaty clauses are scenario data. The shared initial vocabulary covers
  territory, immediate payment/reparations, temporary tribute, recognition or
  independence, vassalage/overlordship, trade and military access, ceasefire,
  non-aggression, and alliance. Scenario extensions use stable clause IDs and the
  same authority checks. A government cannot cede territory it does not own,
  spend funds absent from its treasury without an authored debt mechanism, or
  grant a capability it lacks.
- <!-- req:REQ-0312 --> AI acceptance uses current war goals/balance, occupations, relative strength,
  casualties, exhaustion, economic cost and treasury pressure, allies, ongoing
  threat, strategic risk, diplomatic history, reputation, and the practical
  value/cost of terms. Historical pressure is a bounded bias only and never
  overrides authoritative alternate-history state.
- <!-- req:REQ-0313 --> Player explanations contain at most three plain-language reasons, never raw
  coefficients. Territory, sovereignty/independence, vassalage, and payments
  require an explicit confirmation before acceptance commits.
- <!-- req:REQ-0314 --> Pending, accepted, rejected, and expired offers; treaties and their clauses;
  cooldowns; discoveries; government rights; standing; territorial results; and
  diplomatic history use stable IDs and persist across save/load and map
  transitions. Warcraft screens and handles are projections and are never saved.

## Piracy, privateering, and independent free polities

- <!-- req:REQ-0315 --> Boarding, plunder, cargo seizure, ransom/prisoner disposition, vessel capture,
  scuttling, and coastal raids commit through one authoritative prize action.
  Physical Warcraft units are representations only; stable action/target IDs,
  cargo, proceeds, vessel disposition, victims, and consequences persist.
- <!-- req:REQ-0316 --> A target must be eligible and the war/crime authority must validate the act.
  Replayed action IDs return the original result, while per-target exhaustion
  prevents repeat farming. Rewards, bounties, cooldowns, risk, and pressure are
  scenario data and use integer authoritative values.
- <!-- req:REQ-0317 --> Pirate notoriety/outlaw status is separate from country standing and merchant
  reputation. A currently valid letter of marque makes attacks on its named
  targets lawful privateering, changes issuer/victim relations and rewards, and
  creates less notoriety. Commissions have explicit issue/expiry/revocation
  state; attacks outside them are piracy and may turn the captain outlaw.
- <!-- req:REQ-0318 --> Havens expose data-defined fences, black markets, smugglers, repairs, refits,
  recruitment, contracts, treasure, and intelligence subject to notoriety and
  access rules. They do not mint duplicate cargo or bypass the economy.
- <!-- req:REQ-0319 --> Sustained piracy raises bounded regional shipping risk, prices, convoying,
  escorts, patrols, port restrictions, bounties, diplomatic pressure,
  anti-piracy expeditions, and quest/event pressure. Pressure decays rather than
  permanently ratcheting, so suppression or collapse restores trade conditions.
- <!-- req:REQ-0320 --> A qualified outlaw captain with sufficient notoriety, accumulated prize
  wealth, prize history, and a durable controlled capital may explicitly found
  an independent polity. Government form, state name, and ruler/collective title
  are scenario data; republic, confederacy, kingdom, and future forms share the
  same transition and no ideology is hardcoded in the reusable engine.
- <!-- req:REQ-0321 --> The founded polity is substantive, not a label: its stable polity and
  territory records are handed to the ordinary sovereignty, settlement,
  government/office, economy, diplomacy, war/peace, military, technology,
  taxation/upkeep, AI, and reconstruction systems. Other countries persist
  hostility, non-recognition, tolerance, recognition, trade/embargo, alliance,
  or vassal status according to campaign state.
- <!-- req:REQ-0322 --> Commissions, notoriety, bounties, haven standing, exhausted targets, regional
  pressure, prize history, polity territory, government form, and recognition
  are versioned campaign state and must reconstruct without Warcraft handles.

## Performance and simulation scale

- <!-- req:REQ-0323 --> Performance is a design constraint throughout content production, not a cleanup task deferred until final integration.
- <!-- req:REQ-0324 --> Global campaign entities should remain authoritative abstract data whenever possible; only locally relevant armies, fleets, characters, settlements, effects, and other representations should become active Warcraft objects.
- <!-- req:REQ-0325 --> Avoid frame-rate polling for strategic systems. Prefer event-driven processing and coarse campaign-time ticks appropriate to each system.
- <!-- req:REQ-0326 --> Expensive Warcraft operations such as pathfinding, large unit-group scans, frequent timers, effects, AI orders, and handle creation must be limited to locally relevant gameplay where practical.
- <!-- req:REQ-0327 --> Phase 5 must include synthetic stress tests before the world is fully populated, including large abstract military/state counts, large character/relationship sets, large settlement/economy sets, accelerated campaign simulation, large saves, and a maximum-reasonable local battle.
- <!-- req:REQ-0328 --> Performance tests should establish measurable budgets for simulation-step time, visible hitching, save/load time, active-object counts, and local-battle frame rate before full-world content production makes regressions expensive.
- <!-- req:REQ-0329 --> Development hardware must not be treated as the minimum-performance target; engine-side scalability matters even when a powerful development PC can brute-force a workload.

## Development workflow

- <!-- req:REQ-0330 --> The player is not expected to act as incremental QA.
- <!-- req:REQ-0331 --> Prefer automated tests, simulations, static validation, debug tooling and developer-side testing.
- <!-- req:REQ-0332 --> Player involvement during development should be limited mainly to design decisions.
- <!-- req:REQ-0333 --> Serious player testing is expected near a feature-complete/full release candidate.
