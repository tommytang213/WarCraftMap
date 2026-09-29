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
- [x] Establish reproducible source-map -> release `.w3x` packaging
- [x] Add full CI build artifact after the source map exists

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
- [x] Economy invariant tests
- [x] Save round-trip tests
- [x] Save migration tests
- [x] Inventory routing, validation, and over-capacity recovery tests
- [x] Navigation graph/connectivity validation and recovery-policy tests
- [x] Long timeline simulation harness

## Phase 3 — Warcraft runtime foundation

- [x] Latest-WC3 compatibility module
- [x] Map build pipeline
- [x] Command router + paged /help
- [x] UI pause policy for management screens
- [x] Campaign save manager
- [x] 15-slot rolling autosave scheduler
- [x] /unstuck + last-safe-position system
- [x] Player-only emergency invulnerability command

## Phase 4 — Core world simulation

- [x] Countries/polities
- [x] Provinces/states
- [x] Settlements
- [x] Timeline/eras
- [x] Technology/institutions
- [x] Economy/trade
- [x] Diplomacy/war
- [x] Armies/fleets
- [x] City capture/rebuild
- [x] Titles/land/taxation
- [x] Characters/relationships
- [x] Quests/events/exploration

## Phase 5 — Age of Sail world content

- [x] Early performance stress harness and provisional budgets
- [x] Synthetic large-world simulation tests before full content population
- [x] Maximum-reasonable local battle performance test
- [x] Global geography/navigation topology
- [x] Multi-map campaign packaging and per-region/subregion physical map build pipeline
- [x] Cross-map campaign persistence, visited-map reconstruction, and versioned state transfer
- [ ] Regional instance activation, boundary transitions, and cross-map/cross-region travel
- [x] Cross-region troop command and remote regional building management (authoritative simulation layer; physical cross-map command loading still integrates with the multi-map runtime)
- [x] World/region map presentation, discovery knowledge, and reusable location/search-area focus APIs
- [x] Custom quest journal and quest-to-map tracking integration
- [x] Europe
  - [x] Regional instances and geographic reference data
  - [x] 1450 political baseline (polities, provinces, sovereignty, and conflicts)
  - [x] Authoritative terrain generation and land/naval/amphibious/flying navigation
  - [x] Settlements and playable content
- [ ] Africa
  - [x] Regional instances and geographic reference data
  - [x] 1450 political baseline (polities, provinces, sovereignty, tributary relationships, and conflicts)
  - [x] Authoritative terrain generation and land/naval/amphibious/flying navigation
  - [x] Settlements and playable content
- [x] Middle East / India
  - [x] Authoritative terrain generation and land/naval/amphibious/flying navigation
  - [x] Regional instances and geographic reference data
  - [x] 1450 political baseline (polities, provinces, sovereignty, and conflicts)
- [x] Southeast Asia
  - [x] Regional instances and geographic reference data
  - [x] 1450 political baseline (polities, provinces, sovereignty, tributary relationships, and conflicts)
  - [x] Authoritative terrain generation and land/naval/amphibious/flying navigation
  - [x] 1450 political baseline and authoritative settlement content
  - [x] Ports, trade routes, transitions, economy profiles, and abstract activation data
- [ ] East Asia
  - [x] Regional instances and geographic reference data
  - [x] 1450 political baseline (polities, provinces, sovereignty, tributary relationships, and conflicts)
  - [x] Authoritative terrain generation and land/naval/amphibious/flying navigation
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
- [ ] Finalize performance budgets against full-world content
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
