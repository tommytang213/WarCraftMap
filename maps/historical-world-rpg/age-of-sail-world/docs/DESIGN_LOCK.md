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
- A player-facing MC-only invulnerability command may be provided so native `whosyourdaddy` is unnecessary for recovery.

## Development workflow

- The player is not expected to act as incremental QA.
- Prefer automated tests, simulations, static validation, debug tooling and developer-side testing.
- Player involvement during development should be limited mainly to design decisions.
- Serious player testing is expected near a feature-complete/full release candidate.
