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

- The global world uses separate logical regional map instances rather than one physically contiguous world terrain.
- The initial implementation remains within the project's single packaged `.w3x`: regions are isolated playable terrain instances/areas managed by the scenario/runtime rather than separate Warcraft map files.
- Crossing a valid land or sea boundary transitions the player and other locally relevant runtime representations to the geographically adjacent region and reconstructs them at the corresponding entry boundary.
- Regional adjacency follows real-world geography and compass direction. For example, leaving Europe westward across the Atlantic leads toward eastern North America; leaving Europe eastward leads toward Asia/Middle East rather than America.
- Long-distance ocean travel may use direct region-to-region routes with campaign-time advancement and encounter/event hooks rather than requiring one enormous continuously rendered ocean. Dedicated ocean/encounter instances may be used where gameplay benefits.
- Each region uses gameplay-compressed geography rather than one rigid global projection or uniform scale. Preserve recognizable coastlines, relative direction, major geographic relationships, settlement ordering, and important travel routes while compressing empty distance aggressively.
- Regions not currently active remain authoritative abstract campaign state. Their armies, fleets, settlements, characters, economy, wars, and events continue through strategic simulation without keeping their Warcraft object representations loaded.
- Region transitions must preserve authoritative unit, party, fleet, quest, inventory, and campaign state; transient Warcraft objects are reconstructed from stable IDs/state after arrival.
- Transition boundaries and entry points must be explicit scenario data so geography/navigation remains reusable and testable.

## Quest location and map assistance

- The quest journal must retain stable-ID location context for quest givers, turn-in locations, objectives, relevant settlements, regions, and other known destinations so the player is not required to remember where a quest originated.
- Quest entries should provide a direct `Show on Map` / `Track` action where a meaningful destination exists.
- Showing a quest on the map should open or focus the appropriate world/region map context, select the relevant region and settlement/location, and visibly mark the destination.
- For cross-region objectives, the helper should show a useful route breadcrumb through known region transitions from the player's current physical region to the destination, e.g. current region -> ocean/adjacent region -> target region -> target settlement.
- When the player reaches the destination region, the helper may provide a local marker, minimap ping, or directional indicator toward the known quest location.
- Returning to a quest giver or turn-in point must be supported explicitly; completed objectives should still retain their return destination until the quest is actually turned in.
- Visiting a settlement or accepting a quest there is sufficient to record that settlement as known for later navigation.
- Quest/map assistance must not reveal unrelated undiscovered geography, hidden locations, secret objectives, or information the quest intentionally withholds. A quest may reveal an exact destination, only a region, or no marker at all according to its scenario data.
- The world/region map should support centering or focusing on a known named settlement/location without physically moving the player's character.
- Quest navigation is informational only: tracking or viewing a destination does not teleport units or bypass travel.

## Remote regional management

- The player can manage owned or authorized holdings in other regions without physically traveling there.
- Remote management uses a regional management view: switch the camera and UI context to a selected region, click its buildings, and choose building upgrades or management actions directly.
- Entering a remote regional management view does not move the player's character, party, army, fleet, or physical campaign location.
- Remote regional management is modal and follows the existing campaign pause policy.
- A remote management view should instantiate only the regional representations needed for management and visual context rather than the full regional population.
- Leaving the management view restores the camera and UI to the player's physical region and prior local context.
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
