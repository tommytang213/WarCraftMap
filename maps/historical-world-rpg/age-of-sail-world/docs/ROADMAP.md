# Development Roadmap

The player should not be pulled into repetitive feature testing. Development gates are organized around automated/developer-side verification and a near-final player acceptance playthrough.

## Phase 0 — Repository bootstrap

- [x] Repository initialized
- [x] Category/map folder structure established
- [x] Agreed design constraints recorded
- [x] Pin Warcraft/Wurst project patch target to `v3.0`
- [x] Select Lua backend
- [x] Add initial Wurst project configuration/bootstrap package
- [x] Add CI typecheck workflow
- [x] First Wurst CI typecheck passed
- [x] Commit/create the clean source map folder
- [ ] Establish reproducible source-map -> release `.w3x` packaging
- [ ] Add full CI build artifact after the source map exists

## Phase 1 — Engine contracts

- [x] Stable ID conventions
- [x] Initial polity/province/settlement data contract
- [x] Ownership/control represented separately in starting world data
- [x] Unit/army/fleet model
- [x] Character/loyalty/relationship model
- [x] Technology/institution graph schema
- [x] Title/land/vassal model
- [x] Save schema + migration registry
- [x] Personal inventory, equipment, and tiered backpack contract
- [x] Navigation-zone/safe-position model

## Phase 2 — Headless validation foundation

- [x] Initial world data validator
- [x] Duplicate/missing world-reference detection
- [x] Technology cycle/reachability checks
- [x] Quest/event reference checks
- [ ] Economy invariant tests
- [x] Save round-trip tests
- [x] Save migration tests
- [x] Inventory routing, validation, and over-capacity recovery tests
- [x] Navigation graph/connectivity validation and recovery-policy tests
- [ ] Long timeline simulation harness

## Phase 3 — Warcraft runtime foundation

- [ ] Latest-WC3 compatibility module
- [ ] Map build pipeline
- [ ] Command router + paged /help
- [ ] UI pause policy for management screens
- [ ] Campaign save manager
- [ ] 15-slot rolling autosave scheduler
- [ ] /unstuck + last-safe-position system
- [ ] Player-only emergency invulnerability command

## Phase 4 — Core world simulation

- [ ] Countries/polities
- [ ] Provinces/states
- [ ] Settlements
- [ ] Timeline/eras
- [ ] Technology/institutions
- [ ] Economy/trade
- [ ] Diplomacy/war
- [ ] Armies/fleets
- [ ] City capture/rebuild
- [ ] Titles/land/taxation
- [ ] Characters/relationships
- [ ] Quests/events/exploration

## Phase 5 — Age of Sail world content

- [ ] Global geography/navigation topology
- [ ] Europe
- [ ] Africa
- [ ] Middle East / India
- [ ] Southeast Asia
- [ ] East Asia
- [ ] Americas / Caribbean
- [ ] Pacific
- [ ] Historical tech/event timeline
- [ ] Country-specific units/content
- [ ] Recruitable characters
- [ ] Regional and long-chain quests
- [ ] Treasures/secrets

## Phase 6 — Visual/content production

- [ ] Stock/Reforged asset catalogue and historical-fit matrix
- [ ] Country/unit visual language
- [ ] Settlement/building visual sets
- [ ] Custom icons/textures where needed
- [ ] Custom 3D models where stock assets are insufficient
- [ ] Sound/music/ambient pass
- [ ] Placeholder-removal audit

## Phase 7 — Full-world integration and balancing

- [ ] Multi-century simulation soak tests
- [ ] Performance budgets
- [ ] Economy balancing
- [ ] AI territorial warfare
- [ ] Save/load stress testing
- [ ] Native WC3 save/load regression
- [ ] City/world integrity recovery tests

## Phase 8 — Player release candidate

The first serious player test target: a substantially complete game intended to be played normally rather than as feature-by-feature QA.

- [ ] Full content pass
- [ ] Release save compatibility
- [ ] No known campaign-blocking defects
- [ ] Recovery tooling documented
- [ ] RC build packaged
