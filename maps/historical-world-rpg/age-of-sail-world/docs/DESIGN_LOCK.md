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
