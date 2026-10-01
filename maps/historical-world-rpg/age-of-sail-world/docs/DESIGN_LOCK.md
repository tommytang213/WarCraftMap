# Design Lock v0.1

This file records requirements already agreed with the player. They are defaults unless deliberately revised later.

## Campaign

- Single-player.
- Target the latest Warcraft III.
- Primary language: English.
- Global Age of Sail / early-modern historical sandbox, roughly 1450-1820.
- Campaign is intentionally extremely long; content and systems should support 100+ hour play rather than a normal WC3 map session.
- The player is an individual inside a living world, not an abstract country.

## Reusable architecture

- Engine and scenario content are separate.
- A future historical timeline/location should reuse the same systems and swap scenario data, terrain, units, technology, events, quests and assets.
- Avoid Age-of-Sail-specific assumptions in shared modules.

## World hierarchy

- Countries/polities contain provinces/states/regions and settlements.
- Administrative naming may differ by culture while exposing understandable generic equivalents where useful.
- Ownership, control, occupation, governance and sovereignty are distinct concepts.
- Provinces and cities can change hands through war.
- Settlements can grow and world state can evolve over time.

## AI territorial warfare doctrine

- AI territorial warfare uses a hybrid doctrine: historical ambitions, rivalries, claims, strategic pressures, and regional interests bias otherwise state-driven strategic decisions.
- Historical pressures are scenario data and modifiers, not scripts. They may raise or lower the attractiveness of wars, objectives, alliances, rivalries, or peace terms, but must not force a war or guarantee a historical outcome when current campaign state no longer supports it.
- State-driven evaluation remains authoritative. AI polities should consider current ownership/control, claims, border and maritime access, settlement and trade-route value, military and naval strength, manpower/supply, treasury and economy, war exhaustion, diplomacy, alliances, threats, terrain, technology, institutions, and other relevant campaign state before choosing war or peace.
- War goals should be limited and explicit where practical: recover or press claims, seize strategic ports or provinces, protect trade or allies, weaken a rival, secure access, suppress rebellion, or pursue broader expansion when conditions justify it. AI should not default to indiscriminate total conquest merely because a target is weaker.
- Peace evaluation should reflect the war's goals, achieved control, relative strength, losses, exhaustion, economic cost, alliance situation, and continuing strategic risk. Terms should be proportionate to plausible objectives and campaign state.
- Historical biases must weaken, disappear, or redirect when alternate-history divergence removes their basis. A polity should not pursue an obsolete historical rivalry or objective forever after the relevant territory, government, alliance, route, or strategic condition has materially changed.
- AI polities use the same authoritative ownership, control, diplomacy, war, military, economy, technology, tradition, save/persistence, and cross-map systems as other campaign actors. Doctrine chooses actions; it does not bypass those systems.
- Decisions must be deterministic from authoritative campaign state plus the campaign's deterministic random source where tie-breaking or bounded variation is useful, so uninterrupted and resumed simulations remain equivalent and testable.
- Historical weighting and state-driven utility coefficients belong in scenario/configuration data rather than hardcoded Age-of-Sail assumptions in shared engine code.
- The goal is a recognizable historical strategic texture without railroading the campaign: plausible historical pressures should be visible, while sufficiently changed world state should produce correspondingly different AI behavior.

## Technology

- Large technology trees with multiple branches.
- Technology availability/cost changes with historical time.
- Ahead-of-time technology is possible, not absolutely forbidden; extreme early research should be exceptionally expensive/difficult.
- Technologies can have cross-tree prerequisites.
- Institutions/technology adoption can diffuse unevenly through provinces.
- Countries can have unique/special units and other distinct content.

## Player origin, allegiance and titles

- Origin/current allegiance matters and governments reward contribution.
- Rewards can include money, equipment, privileges, special access, titles/peerage and land.
- Allegiance may change; the active government's reward track becomes the relevant one after changing allegiance, subject to reputation/history rules.
- Titles use culturally appropriate names plus a generic tier in parentheses for clarity.
- A sovereign normally grants ranks below its own sovereign tier.
- Empire-tier rulers may grant subordinate king-tier titles/realms where appropriate; this does not make the player the imperial sovereign.
- Land holding, control, sovereignty, autonomy and tax obligations are separate.
- Independent sovereign land has no overlord tax, but still has normal administration/upkeep costs.

## Settlement-level economy and trade identity

- Economic production, consumption, availability, and pricing are primarily settlement-level rather than a single fixed goods list shared by an entire region.
- A region's climate, geography, resources, institutions, trade access, and historical economy should influence what its settlements tend to produce or demand, but settlements within the same region should still differ meaningfully.
- Individual cities and ports may have distinct local specialties, industries, raw materials, manufactured goods, luxury goods, food surpluses, shortages, import dependencies, and trade-service roles according to historical/geographic context and gameplay value.
- Major trade centers and ports may stock many goods they do not produce locally because trade routes, shipping, caravans, warehouses, and merchant activity bring them in.
- A settlement should not be limited to only its signature production good. Signature goods indicate comparative advantage or notable local production, while ordinary local consumption and traded inventory may cover a much broader set.
- Supply, demand, production capacity, war, blockade, occupation, seasonal or historical events, technology, infrastructure, and trade connectivity may change local stock and prices over time.
- Nearby settlements may share some common staple goods while differing in quantities, prices, specialties, imports, and shortages. Avoid making every city unique merely for the sake of uniqueness when shared geography genuinely supports similar production.
- Regional content data should therefore define settlement-specific economic profiles and use region-level rules as modifiers/defaults rather than as the authoritative complete market inventory.
- The current small economy catalog is prototype content and must not be interpreted as the intended final breadth of goods.

## Characters

- Named recruitable characters have skills, traits, quests and relationships.
- Loyalty/relationship thresholds can produce buffs/debuffs and special content.
- A high-investment permanent loyalty state such as Oathbound is supported.
- Relationships between companions may create synergies or friction.

## Equipment identity, rarity, level, and comparison

- Equipment uses separate, explicit dimensions for power and identity rather than collapsing everything into one rarity label.
- Every player-usable equipment item has a player-facing item level / power level for quick comparison. The intended long-campaign scale supports item levels up to roughly the same order as hero progression (target level cap 300), while scenario data may use narrower bands for specific eras or categories.
- Item level represents the item's overall stat/effect budget and is primarily a comparison aid, not an absolute statement that a higher-level item is always better for every build.
- Rarity/quality is a separate field and should communicate affix/effect complexity, craftsmanship, scarcity, and ceiling. Use a clear ordered ladder such as Common, Fine, Superior, Rare, Epic, Legendary, and Relic/Artifact, with exact labels kept data-driven.
- Identity/provenance is also separate from rarity: generic, regional/cultural, polity-specific, profession/specialist, quest reward, equipment-set piece, unique historical item, legendary/relic, or other authored identity may coexist with any appropriate power level.
- Era, technology, institutions, local production, trade access, settlement wealth, polity/culture, merchant type, and quest/event state determine plausible availability. Historical/unique items remain persistent singular identities unless explicitly authored otherwise.
- Equipment comparison UI should show item level, rarity, major stats/effects, equipment-set membership, requirements, and green/red deltas against the currently equipped item. Build-specific abilities, resistances, passives, set thresholds, and conditional effects must remain visible so a lower-level specialized item can rationally outperform a higher-level generic one.
- Equipment may support bounded enhancement/refinement where appropriate, but enhancement must not erase historical/technological gating or make every old item converge into the same endgame stat block.
- Player-facing stores distinguish bulk trade goods from usable RPG inventory. Settlement merchant types may include general merchants, armourers/weaponsmiths, gunsmiths, tailors/outfitters, apothecaries, booksellers/cartographers, horse dealers, military suppliers, relic/artifact merchants, ship chandlers, and dockyards, with inventory generated from authoritative local context.

## Persistent individual ship progression and refits

- Ships are persistent individual vessels. Two vessels of the same archetype may diverge through installed equipment/refits, crew quality, experience/veterancy, captain/admiral effects, damage/maintenance state, and historical service.
- Ship equipment/refit categories may include armament, hull, rigging/sails, navigation, cargo/logistics, crew/marines, protection/safety, flagship/command facilities, and other historically/plausibly appropriate systems.
- Refit availability is constrained by hull compatibility, campaign year, technology/institutions, polity/region, dockyard capability, resources, money, and other authoritative state.
- Individual ships accumulate persistent experience from meaningful service such as battles, victories, voyages, storms, exploration, trade/escort operations, and other scenario-defined accomplishments.
- Ship experience provides continuous, player-visible improvement rather than bonuses so tiny that normal play cannot perceive them. Early meaningful service should produce a noticeable few-percent improvement; established veteran ships should commonly reach roughly 10-20% effective improvement in relevant areas, while exceptionally long-lived elite/legendary vessels may reach roughly 25-40% combined improvement across selected relevant stats/effects.
- Experience bonuses are distributed by role/history rather than multiplying every stat equally. A veteran gunnery ship may improve reload/accuracy/broadside discipline, while an exploration vessel may improve navigation, storm handling, range, supply efficiency, or maneuvering.
- Continuous veterancy uses diminishing returns or similarly bounded scaling so an ancient obsolete hull does not overpower a vastly superior later design merely through age. Hull, technology, equipment, and era remain the primary power envelope.
- Milestones such as Experienced, Veteran, Elite, Famous, and Legendary layer distinctive traits, passives, or specialization choices on top of continuous scaling.
- Persistent vessel history may record battles, defeated ships, voyages, storms survived, distance sailed, ports visited, discoveries, commanders served under, and other notable service for gameplay, traits, naming, and player attachment.

## Long-campaign hero progression and persistence

- Recruited named heroes persist after their historical initial-availability window closes; the historical window gates first availability/recruitment rather than removing an already recruited hero.
- Recruited heroes must not disappear merely because the historical death/end date is reached. Once recruited, they belong to the campaign's alternate-history state unless removed by an explicit gameplay rule chosen for that campaign.
- The target named-hero level cap is 300 for the long campaign. Levels should provide frequent incremental growth plus regular meaningful perk/ability/mastery decisions rather than hundreds of cosmetic numbers.
- Hero progression is multi-axis: character level, core skills, profession/mastery tracks, personal/signature trees, equipment and sets, relationships, loyalty/Oathbound, titles/offices, command experience, quest unlocks, and other scenario-defined progression may advance independently.
- Late-era historical heroes should enter at a contextually appropriate starting level/skill state based on campaign year, career/reputation, role, and world/player progression rather than universally starting at level 1.
- The recruited strategic hero roster has no arbitrary gameplay cap. Physical co-location is a runtime/performance concern separate from ownership; the initial target for simultaneously instantiated player-side heroes in one active field group is at least 32, and may be raised after performance validation.
- Recruited heroes may instead serve as governors, advisers, army commanders, fleet commanders, specialists, or other remote assignments while retaining one authoritative physical location.
- Ordinary combat defeat of a recruited named hero should default to a recoverable wounded/incapacitated state rather than silently deleting a long-invested character; any permanent-death mode must be an explicit campaign rule rather than the default.

## Units and ownership

- Do not use native WC3 food as the strategic ownership cap.
- Strategic armies/fleets may represent many soldiers/ships without spawning every represented entity simultaneously.
- Economic/logistical cost is the intended practical limiter.
- Summoned units need no special city-damage exception beyond normal rules.

## Unit roster and combat identity

- The ordinary military roster should be predominantly historically grounded for each polity and period, with deliberate gameplay-friendly variance where it improves fun, readability, balance, or faction identity.
- Historical progression matters: unit types, weapons, formations, ships, and battlefield roles should broadly fit the campaign date and technology state rather than appearing arbitrarily centuries early.
- Slight alternate-history divergence is allowed through technology, exceptional national development, player actions, rare content, and balance adjustments; this is not a museum-level simulation.
- Every meaningful combat unit type should have a distinct gameplay identity rather than being only a renamed stat variant. Different types may be distinguished by passive traits, active abilities, auras, formations, weapon behavior, morale or discipline effects, movement rules, resistances, buffs, debuffs, counters, logistics traits, terrain roles, boarding/siege roles, or other scenario-appropriate mechanics.
- Not every unit needs every category of mechanic. Prefer a small number of clear, meaningful traits or abilities per type over ability clutter.
- National/special units may exaggerate real historical strengths for gameplay while remaining recognizable as historically inspired.
- Marines, naval infantry, boarding troops, and other historically appropriate specialist roles are supported where relevant.
- Named/recruitable heroes may use substantially stronger RPG or supernatural mechanics than ordinary units while the surrounding world and normal military roster remain predominantly historical.
- Hero abilities may include persistent mana-powered protection such as a personal Mana Shield that can extend to friendly units within selectable preset ranges. Such group protection uses the hero as the shared mana source, can remain active without a fixed duration while mana is available, and may support self-only and multiple group-range modes.

## Layered military and naval rosters

- Final military content uses layered roster composition rather than requiring every polity to duplicate every ordinary role.
- Common/global archetypes cover roles that genuinely transfer across regions or are useful as shared mechanical bases.
- Regional/cultural families provide historically appropriate local identities, equipment, formations, ship traditions, and ordinary troops.
- Polity-specific variants provide meaningful national/state identity where history or gameplay justifies it.
- Elite, guard, specialist, famous, and otherwise unique formations sit above those shared layers where appropriate.
- Major powers and long-lived militarily important polities should have broader multi-era rosters than minor polities. Minor polities may rely primarily on regional/common families while still receiving distinctive units, modifiers, traditions, or specialists when justified.
- A polity roster is resolved from the authoritative controller/polity, region or culture, campaign date, technology, institutions, reforms, resources, military traditions, and other scenario requirements. Calendar date alone must not grant units whose enabling development has not occurred.
- Unit availability, obsolescence, upgrades, and replacement chains should visibly represent military evolution across the 1450-1820 campaign instead of leaving one early-game signature unit to represent a polity for centuries.
- Settlement garrisons, AI armies, recruitable military units, and other ordinary forces should consume the same authoritative roster families so city defenders do not become a disconnected parallel unit catalogue.
- Naval content is equal in importance to land content for the Age of Sail scenario. Reusable hull/runtime families should support a substantially broader player-facing catalogue of regional, polity-specific, merchant, transport, patrol, raiding, boarding, and warship variants across multiple eras.
- Shared hulls or runtime templates may back several historically distinct player-facing vessels when their mechanics genuinely overlap; visual identity, armament, stats, abilities, requirements, role, and availability may still differ.
- Roster breadth must be judged across regions, polities, roles, and eras rather than by a raw global archetype count.

## Political offices and settlement administration

- Political/administrative office is distinct from legal ownership, territorial holding, control, sovereignty, and title/land ownership. Appointing a character to govern a settlement or province does not by itself transfer the settlement away from the player/controller.
- Every authoritative settlement normally has an administrator or equivalent office holder. The player-facing title should use a culturally and historically appropriate term where practical while exposing a clear generic role such as Administrator or Governor.
- Historically important or well-attested officials may be authored named characters. Otherwise the campaign deterministically generates a culturally appropriate persistent minor official with a plausible personal name, origin, skills, traits, loyalty, age/lifespan data, allegiance, and office identity. Do not expose runtime-style labels such as `Governor_017` to the player.
- Generated officials are lightweight authoritative characters, not anonymous Warcraft units. Their identity remains stable across save/load, map transitions, reconstruction, and inactive-region simulation.
- A settlement acquired or captured by the player/controller automatically receives an acting/local administrator if no eligible explicit appointment exists. The player is never forced through a blocking appointment dialog merely to keep a newly acquired settlement functional.
- The player may replace the automatic administrator with an eligible recruited hero, historical character, generated official, noble/title holder, or other valid character. The player retains normal settlement management authority after delegating administration.
- Administrative jurisdiction may cover one settlement or, for sufficiently capable/high-ranking offices, multiple settlements or an entire province/region. Administrative capacity, rank, skills, government structure, distance, unrest, integration, institutions, technology, and similar factors may affect efficiency.
- A character has one authoritative physical location. Administrative jurisdiction over multiple settlements never creates authoritative clones. A governor travelling with the player may continue to provide permitted remote administrative effects, but cannot simultaneously appear as the same physical combatant in another city.
- Add a scenario-neutral Administration/Governance skill or equivalent administrative rating rather than forcing unrelated skills to represent general civil administration. Other existing skills may provide secondary office effects where relevant.
- Administrator effects may derive from Administration/Governance, Command, Engineering, Tradecraft, Diplomacy, Scholarship, traits, profession, title/rank, local conditions, government form, and scenario modifiers. Different strengths should produce meaningfully different economic, construction, unrest, institution, supply, garrison, defense, or recovery outcomes.
- Appointment, promotion, tenure, demotion, dismissal, dispossession, and other office changes may affect character loyalty and relationships. Rewards must depend on meaningful prestige/responsibility change and history so repeatedly appointing/dismissing the same character cannot farm loyalty.
- Oathbound remains the permanent high-loyalty state: ordinary negative office consequences cannot reduce an Oathbound character's loyalty.
- Removing a sufficiently disloyal, powerful, locally supported, or militarily entrenched administrator may create refusal, defection, mutiny, rebellion, separatism, or related events according to explicit authoritative conditions. Risky removal must present a useful warning rather than surprise the player with an unexplained settlement loss.
- Office state, jurisdiction, appointment history, administrative effects, succession/replacement state, and any rebellion consequences are authoritative campaign data and persist across saves and physical-map transitions.
- Major polities should eventually have appropriate ruler/sovereign or collective-governance representation in addition to settlement administrators. Decentralized or collective political structures must not be forced into a fake singular monarch solely to satisfy the office system.
- The same office framework may support settlement administrators, provincial governors, sovereign/ruler roles, army commanders, and fleet commanders while keeping the responsibilities and gameplay effects of each office distinct.

## Settlement administrator presentation and local defense

- Every governed settlement exposes its administrator clearly through the settlement/government UI, including name, culturally appropriate office title, loyalty where knowable, relevant skills/traits, jurisdiction, residence/physical location, capacity/efficiency, and major active effects.
- Each settlement has a recognizable government/administration interaction point or equivalent presentation appropriate to its visual set. If the administrator is physically resident and locally instantiated, their actual character representation may appear there with a clear name/title treatment.
- If the appointed administrator is physically elsewhere, do not instantiate a duplicate of that character. A deterministic deputy/local official or abstract office representation may stand in locally and should be identified as acting on behalf of the absent administrator where appropriate.
- Settlement defenders are authoritative local-defense/garrison state, not free player army units. When physically instantiated they use a dedicated allied/AI defense controller and are not directly commandable by the player even when defending a player-controlled settlement.
- Players must not be able to exploit settlement defenders as free expeditionary troops, cargo, equipment sources, disposable recruitment, or permanent field armies.
- A settlement under attack instantiates its currently available garrison/local-defense force. If combat remains active, additional reinforcement waves may spawn after data-driven intervals only while authoritative reserve/manpower/supply remains available.
- Reinforcement waves are bounded by persistent garrison strength, reserves, manpower, supply, buildings, policies, and other authoritative limits. A settlement must never produce infinite defenders merely because an attack remains in progress.
- Garrison casualties and resource expenditure persist back into authoritative state. After a data-driven combat-quiet period, unnecessary runtime defenders may despawn and the surviving force is represented abstractly again; defenders must not instantly reset to full strength.
- Garrison replenishment outside combat follows explicit campaign rules and consumes appropriate time/resources/manpower rather than occurring as a free runtime respawn.
- Defender composition and strength may change over the campaign according to controlling polity, region/culture, campaign date, technology, institutions, reforms, available resources, settlement class, fortifications, buildings, military traditions, administrator skills/traits, wealth/manpower, unrest, recent conquest, and other scenario data.
- Technology and institutional progress may unlock different defender types, improved equipment, additional specialists/artillery, larger or better-organized reserves, stronger fortifications, or other qualitative changes; defender progression is not limited to flat stat scaling.
- Administrator Command, Administration/Governance, Engineering, Tradecraft and other relevant abilities may improve organization, reserve readiness, morale, fortification repair, supply, reinforcement cadence, or similar bounded defense effects, but cannot create manpower or unavailable technology from nothing.
- A resident administrator/commander may join the AI-controlled settlement defense as their actual character. An absent administrator does not appear as a combat clone; a deputy/local commander handles local defense instead.
- Existing City Core capture and defensive-layout reconstruction rules remain authoritative. The local-defense system extends those rules rather than replacing the ownership/control/capture model.

## Controller military traditions

- Player-controlled forces and AI-controlled polities maintain independent persistent military-tradition progression rather than sharing one global combat-experience value.
- Traditions are controller-scoped and category-specific. Scenario data may define tracks such as infantry, cavalry, artillery, naval, marine/boarding, siege, or other appropriate military categories without hardcoding those names into the shared engine.
- Relevant combat by a unit contributes experience to its controller's matching tradition track. Enemy kills are a primary supported source; scenario/balance data may also award weighted experience for other meaningful combat contribution so the system is not tied only to literal last-hit ownership.
- Tradition progression benefits all currently controlled units that qualify for that tradition category, including units represented abstractly while another physical map is active. Runtime units receive the derived modifiers when instantiated or when controller/tradition state changes.
- Tradition belongs to the controller, not permanently to the individual unit. If a unit changes controller, its controller-wide tradition modifiers are recalculated from the new controller's state; the previous controller keeps its accumulated tradition.
- The core numerical tradition bonus is continuous and experience-proportional rather than a discrete level table. Do not require fixed "level X -> bonus Y" thresholds for ordinary stat progression: every additional unit of valid tradition experience should contribute proportionally according to the tradition's data-driven coefficient/curve (for example, if 100 XP grants Y bonus, 1,000 XP grants 10Y under a linear coefficient).
- Controller tradition experience has no ordinary hard progression ceiling or maximum tradition level. Long-running player and AI controllers may continue improving as they accumulate valid experience across the campaign. Balance should come from experience rates, coefficients, opposing progression, costs, counters, and scenario tuning rather than an arbitrary cap that makes further combat experience worthless.
- Milestone thresholds may unlock additional category-wide buffs, passive effects, doctrines, formations, morale/discipline mechanics, logistics advantages, or other qualitative rewards once the controller reaches the required tradition experience.
- Milestone rewards are additive to the continuous XP-derived progression and must not replace, cap, reset, or stall it. Reaching 10,000 XP may grant a milestone buff while 10,001 XP still gives a slightly larger continuous numerical bonus than 10,000 XP.
- Reached milestone rewards remain active for that controller/tradition and normally stack with earlier milestones unless a specific scenario-defined milestone explicitly upgrades/replaces an earlier effect.
- Milestone XP thresholds and effects are data-driven per tradition, so different military categories may have different milestone spacing and rewards.
- Do not require every tradition to raise every numerical stat. Each tradition's affected attributes and coefficients are data-driven so infantry, cavalry, artillery, naval, and other categories can scale differently while preserving their distinct roles.
- Tradition state is authoritative campaign data and must persist across saves, physical-map transitions, inactive-region simulation, and remote command.
- AI controllers use the same progression rules as the player unless scenario data deliberately defines a historical/special starting value or modifier.

## City capture

- Civilian facilities are invulnerable.
- Military defenses are destructible.
- Each capturable settlement has an authoritative City Core/capture structure.
- Destruction of the valid enemy City Core during a legal conflict triggers capture.
- On capture, controller changes, old military defenses are cleaned up, and the city's predefined defensive layout respawns at its original locations under the new controller.
- New defenses receive exactly 5 seconds of post-capture immunity/capture cooldown to prevent immediate hostile survivor/third-party recapture loops.
- City functionality must not become irrecoverably broken because an object was unexpectedly destroyed.
- Persistent city state is authoritative; Warcraft object instances are representations of that state.

## Saving

- Native Warcraft save/load must be regression-tested and must not intentionally be broken.
- Separate versioned campaign persistence is required for long-term compatibility.
- 15 rolling timed autosave slots.
- Manual save slots.
- Separate session-start and major-milestone recovery checkpoints.
- Autosaves should defer during unsafe transitional states instead of serializing half-completed state changes.
- Save data includes format/build/scenario version metadata and integrity checks.
- Save-format changes require migrations whenever practical.
- Failed/incompatible loads must not overwrite the original save.

## Recovery commands

- `/unstuck` applies to selected eligible mobile units.
- If no eligible selection exists because nothing is selected, it may recover the main character.
- Mixed selections move eligible mobile units and skip structures.
- If only ineligible objects such as buildings are selected, report the issue and do not silently move something else.
- Buildings, walls, towers, city cores, destructibles and dummy/system units must never be moved by `/unstuck`.
- Recovery must be connectivity-aware, not merely pathability-aware.
- Ships must not be moved into isolated/decorative lakes or disconnected water.
- Land units must not be moved onto unreachable/disconnected land.
- Track last-known-safe position/navigation zone for important active units.
- Prefer nearby reachable safe position, then verified last-safe position, then a valid connected recovery anchor.
- If safety cannot be proven, fail without moving the unit.
- `/unstuck all` may operate on physically active player-controlled mobile units in the current relevant region, never abstract world entities.

## Commands

- `/help` lists player commands.
- Help is paged: `/help 2`, `/help 3`, etc.
- Topic help is supported, e.g. `/help unstuck`.
- Invalid page numbers produce a clear message.
- Release builds hide internal developer/debug commands.
- A player-facing `/god` command is provided so native `whosyourdaddy` is unnecessary for recovery.
- `/god` applies to all player-controlled runtime entities, not only the main character. This includes player-controlled heroes/companions, ordinary units, summons, ships, structures, and any other controllable Warcraft runtime objects.
- While `/god` is enabled, newly created, spawned, acquired, or otherwise transferred player-controlled runtime entities inherit the same protection automatically.
- `/god` toggles the mode; `/god on` and `/god off` are idempotent explicit forms.
- The mode is a session/recovery convenience rather than campaign progression. It is excluded from custom campaign persistence and defaults to OFF for a new session and after loading campaign state.
- If protected runtime objects are reconstructed while `/god` remains enabled in the same active session, protection is reapplied to their replacements.
- Command feedback must clearly report whether player-wide god mode is ON or OFF.

## UI pause policy

- The campaign is single-player, so opening a modal management screen pauses the entire campaign simulation.
- While a modal management screen is open, campaign time progression, strategic AI actions, combat/travel simulation, economy ticks, and event progression are paused.
- Inventory/equipment, character/companion management, technology, economy/trade management, titles/land/government, fleet/army management, journal/encyclopedia, and full strategic-management/map screens are modal for this policy unless deliberately reclassified later.
- Passive/non-modal UI such as HUD panels, tooltips, notifications/toasts, and small informational overlays does not pause the campaign.
- Nested/modal screen transitions keep the campaign paused until the final modal management screen closes.
- Closing a management screen must restore the pause state that existed before the first modal management screen opened; it must not unpause a game that the player had already manually paused.

## World-map representation and regional traversal

- The purpose of regional partitioning is to make the playable world physically larger than Warcraft III's single-map terrain ceiling. The full world must therefore not be packed into one physical `.w3x`.
- A logical world region is backed by one or more separate physical Warcraft map files/submaps. Each physical map receives its own terrain-size budget, and a large logical region such as Europe may use multiple physical maps when needed for geographic scale, density, or performance.
- The current single `AgeOfSailWorld.w3x` remains only a bootstrap/runtime-validation map while the multi-map campaign pipeline is implemented; it is not the intended final container for all world terrain.
- Crossing a valid land or sea boundary saves/commits authoritative campaign state, changes to the geographically adjacent physical map, and reconstructs the player and other locally relevant runtime representations at the corresponding entry boundary.
- Regional adjacency follows real-world geography and compass direction. For example, leaving Europe westward across the Atlantic leads toward eastern North America; leaving Europe eastward leads toward Asia/Middle East rather than America.
- Ordinary geographic transitions should be edge-to-edge rather than requiring the player to enter an arbitrary trigger circle: reaching a valid shared map boundary transfers to the corresponding boundary of the adjacent physical map.
- Preserve the player's position along the shared boundary using a normalized/correspondence coordinate rather than assuming identical raw Warcraft coordinates. For example, crossing 37% of the way along one map's west edge should normally place the player about 37% of the way along the geographically corresponding east edge of the destination map; reverse or transform the coordinate where edge orientation/geographic projection requires it.
- If neighboring maps deliberately use identical aligned edge scales, the raw coordinate may remain effectively unchanged (for example source y=100 -> destination y=100).
- Boundary arrival may snap only as much as necessary to the nearest valid connected land/water/pathable entry point, avoiding cliffs, blocked terrain, decorative water, or other invalid spawn positions while retaining the intended geographic correspondence.
- Long-distance ocean travel may use direct region-to-region routes with campaign-time advancement and encounter/event hooks rather than requiring enormous continuously rendered oceans. Dedicated ocean/encounter maps may be used where gameplay benefits.
- Each physical map uses gameplay-compressed geography while preserving recognizable coastlines, relative direction, major geographic relationships, settlement ordering, and important travel routes. Empty distance may be compressed, but splitting into maps should be preferred over crushing an entire continent into an implausibly small area merely to fit one map.
- Regions/maps not currently loaded remain authoritative abstract campaign state. Their armies, fleets, settlements, characters, economy, wars, and events continue through strategic simulation without keeping their Warcraft object representations loaded.
- Cross-map transitions must preserve authoritative character, unit, party, fleet, quest, inventory, settlement, diplomacy, economy, technology, and campaign state. Transient Warcraft objects are reconstructed from stable IDs/state after a map loads.
- Revisiting a previously visited physical map should restore/reconstruct its authoritative changed state rather than reset conquered cities, destroyed/rebuilt defenses, moved armies, completed quests, market state, or other persistent campaign changes.
- Prefer versioned authoritative campaign-state serialization/reconstruction over depending on opaque raw Warcraft map-save state as the sole source of truth. Native campaign/game-cache or map-transition facilities may be used as transport/bootstrap mechanisms where reliable.
- Transition boundaries, physical-map IDs, adjacency, entry points, and map-package paths must be explicit scenario data so geography/navigation remains reusable and testable.

## Geographic fidelity and Europe content scope

- Regional terrain should be derived from real-world geography and then scaled down for Warcraft play. Real-world location, compass direction, relative placement, coastline shape, major distance relationships, and connectivity are the starting point rather than hand-authored fantasy layouts.
- Use a broadly consistent base scale within and between neighboring regions, with controlled local distortion only where Warcraft object scale, readability, pathing, performance, or gameplay spacing requires it.
- Important locations must remain geographically sensible relative to one another. A city, port, river, island, mountain range, strait, or neighboring polity should not be moved to a contradictory side of another feature merely to fill space.
- Divide Europe into as many regional instances as are needed to preserve the chosen geographic scale and performance budget. Region boundaries should follow practical low-density, maritime, mountain, or other natural seams where possible rather than being forced to match modern national borders.
- Europe uses the political situation at the 1450 campaign start as its historical baseline. Include major sovereign and de-facto polities plus smaller states that materially affect warfare, diplomacy, trade, quests, or regional identity. Extremely fine political fragmentation may be simplified for terrain readability, but historically important entities should remain representable in authoritative scenario state.
- Provinces/states should use historically meaningful regional or administrative groupings where practical, merging only when the real subdivision is too fine to produce useful Warcraft gameplay.
- Settlement coverage should prioritize capitals, major ports, major trade centers, strategically important fortified towns, and locations needed for historical events, characters, quests, or travel. The map is not required to include every real village.
- Port coverage should include historically/gameplay-significant coastal and river ports needed for naval movement, trade, exploration, diplomacy, and regional transitions.
- Preserve recognizable major coastlines, islands, rivers, mountain systems, straits, and other navigation-defining terrain. Small-scale terrain detail and border wiggles may be generalized.
- Political borders should broadly match the selected historical baseline at campaign start, then evolve through the normal ownership/control/war systems rather than remaining visually or logically fixed.
- The same real-geography-first scaling rule is the default for every later Phase 5 world region, including Africa, the Middle East/India, Southeast Asia, East Asia, the Americas/Caribbean, and the Pacific.
- Do not request a new player design decision merely to repeat the same regional-scope questions for each continent. Region boundaries, compression, included polities, provinces, settlements, ports, terrain, borders, and travel connections should be derived from these locked rules, historical/geographic evidence, gameplay relevance, and performance budgets.
- Region-specific historical features such as trans-Saharan routes, Indian Ocean trade, major straits, island chains, caravan corridors, or similar geography are implementation/research details under this rule, not separate player design blockers unless they expose a genuinely new gameplay choice not covered here.
- Create a new regional `needs-design` blocker only when a materially new player-facing design choice cannot be resolved from the existing design lock, historical/geographic evidence, or established performance constraints.

## Treasures and secrets discovery

- Campaign treasures and secrets use a hybrid deterministic model.
- Historically meaningful or unique treasures keep fixed authored identity, historical/geographic context, and an appropriate fixed anchor region or location family. They must not be randomized into historically implausible parts of the world.
- Within that historical anchor, the exact valid hiding place may vary deterministically per campaign among authored/geographically valid candidates. Secondary loot, guards, encounters, hazards, or supporting rewards may also vary deterministically.
- Generic caches, pirate hoards, wreck salvage, hidden stores, ruins, and similar non-unique secrets may vary more freely, but still only within scenario-appropriate regions, terrain, navigation zones, and content pools.
- Deterministic variation is derived from persistent campaign seed/state. Reloading, changing physical maps, revisiting a region, or restoring a save must not reroll a treasure's resolved location, reward variant, encounter, or discovery state.
- Once a treasure/secret is resolved for a campaign, its authoritative result persists across saves, cross-map transitions, reconstruction, and inactive-region simulation.
- Discovery may progress through hidden, region-only, approximate search-area, narrowed search-area, and exact-known states using the existing discovery/map/quest knowledge model.
- Clues and search areas must always refer to the campaign's actual resolved treasure location and must never reveal information more precise than the player has earned.
- A historically unique artifact normally keeps its unique identity/reward while its exact hiding place and secondary rewards may vary. Generic treasure rewards may be selected from deterministic, scenario-defined pools.
- Treasure placement must validate accessibility, terrain/navigation compatibility, physical-map assignment, duplicate/exclusive placement rules, and conflict with settlements or other reserved content before campaign state is committed.
- Treasure generation must be reproducible from the same campaign seed and authoritative inputs for testing, migration, and recovery.

## Quest location and map assistance

- The quest journal must retain stable-ID location context for quest givers, turn-in locations, objectives, relevant settlements, regions, and other known destinations so the player is not required to remember where a quest originated.
- Quest entries should provide a direct `Show on Map` / `Track` action where a meaningful destination exists.
- Showing a quest on the map should open or focus the appropriate world/region map context, select the relevant region and settlement/location, and visibly mark the destination.
- For cross-region objectives, the helper should show a useful route breadcrumb through known region transitions from the player's current physical region to the destination, e.g. current region -> ocean/adjacent region -> target region -> target settlement.
- When the player reaches the destination region, the helper may provide a local marker, minimap ping, or directional indicator toward the known quest location.
- Returning to a quest giver or turn-in point must be supported explicitly; completed objectives should still retain their return destination until the quest is actually turned in.
- Visiting a settlement or accepting a quest there is sufficient to record that settlement as known for later navigation.
- Quest/map assistance must not reveal unrelated undiscovered geography, hidden locations, secret objectives, or information the quest intentionally withholds. A quest may reveal an exact destination, only a region, an approximate search area, or no marker at all according to its scenario data.
- Approximate quest knowledge should be visualized as a bounded search area rather than a false precise point. For example, a clue such as "somewhere in the Amazon" may highlight or ping a large circle/region covering the plausible search area.
- Search areas may shrink, move, split, or become an exact marker as the player obtains better clues, explores, talks to characters, finds maps, or completes intermediate objectives.
- The displayed uncertainty area is informational and should reflect only the precision of the clues actually known to the player.
- Previously discovered exact locations may be shown precisely even when a later quest clue is broader. If the player has already visited or otherwise explicitly discovered the specific settlement, landmark, ruin, dungeon, port, or other destination and that knowledge is recorded in campaign state, the quest/map helper may use the exact known marker instead of downgrading it to a broad search area.
- Revealing general fog-of-war or exploring a region does not automatically identify every hidden point of interest inside it; precise quest markers require that the destination itself is known or has been explicitly revealed by the quest/clue.
- The world/region map should support centering or focusing on a known named settlement/location without physically moving the player's character.
- Quest navigation is informational only: tracking or viewing a destination does not teleport units or bypass travel.

## Remote regional management

- The player can manage owned or authorized holdings in other regions without physically traveling there.
- Remote regional access supports both management and active command. Switching to another owned/authorized region changes the camera and control context to that region so the player can click buildings and directly command eligible local troops there.
- Entering a remote regional management view does not move the player's character, party, army, fleet, or authoritative physical campaign location.
- Remote regional management is modal and follows the existing campaign pause policy.
- If the requested command region is on another physical map, switching active command context may load that map and reconstruct the eligible local military/building/character representations there. The main character's authoritative location remains unchanged unless the character actually travels.
- The player's main character keeps a separate physical-region/map location from the current command/view region. Leaving remote command can load/reconstruct the character's physical map and return control there without teleporting the character through the world model.
- Multiple regions may contain player-owned troops and holdings at the same campaign time. Only the currently active command region needs full local Warcraft representations; player forces in other regions continue executing strategic orders and simulation in abstract state until their region becomes active.
- Switching active command regions must preserve ongoing orders, battles, construction, movement, and other authoritative state so activity continues coherently across the whole world.
- The feature may be opened from a world/region selector and by a player-facing command; exact command syntax can be chosen during UI implementation.
- Remote management shows only campaign information the player is already authorized to know.

## Performance and simulation scale

- Performance is a design constraint throughout content production, not a cleanup task deferred until final integration.
- Global campaign entities should remain authoritative abstract data whenever possible; only locally relevant armies, fleets, characters, settlements, effects, and other representations should become active Warcraft objects.
- Avoid frame-rate polling for strategic systems. Prefer event-driven processing and coarse campaign-time ticks appropriate to each system.
- Expensive Warcraft operations such as pathfinding, large unit-group scans, frequent timers, effects, AI orders, and handle creation must be limited to locally relevant gameplay where practical.
- Phase 5 must include synthetic stress tests before the world is fully populated, including large abstract military/state counts, large character/relationship sets, large settlement/economy sets, accelerated campaign simulation, large saves, and a maximum-reasonable local battle.
- Performance tests should establish measurable budgets for simulation-step time, visible hitching, save/load time, active-object counts, and local-battle frame rate before full-world content production makes regressions expensive.
- Development hardware must not be treated as the minimum-performance target; engine-side scalability matters even when a powerful development PC can brute-force a workload.

## Development workflow

- The player is not expected to act as incremental QA.
- Prefer automated tests, simulations, static validation, debug tooling and developer-side testing.
- Player involvement during development should be limited mainly to design decisions.
- Serious player testing is expected near a feature-complete/full release candidate.
