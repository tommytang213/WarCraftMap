# Development Roadmap

The player should not be pulled into repetitive feature testing. Development gates are organized around automated/developer-side verification and a near-final player acceptance playthrough.

## Phase 0 — Repository bootstrap

- [x] Repository initialized
- [x] Category/map folder structure established
- [x] Agreed design constraints recorded
- [ ] Pin current WC3/toolchain versions
- [ ] Establish reproducible build command
- [ ] Establish CI/static validation

## Phase 1 — Engine contracts

- [ ] Stable ID conventions
- [ ] Polity/province/settlement schemas
- [ ] Ownership/control model
- [ ] Unit/army/fleet model
- [ ] Character/loyalty/relationship model
- [ ] Technology/institution graph schema
- [ ] Title/land/vassal model
- [ ] Save schema + migration registry
- [ ] Navigation-zone/safe-position model

## Phase 2 — Headless validation foundation

- [ ] Data schema validator
- [ ] Duplicate/missing reference detection
- [ ] Technology cycle/reachability checks
- [ ] Quest/event reference checks
- [ ] Economy invariant tests
- [ ] Save round-trip tests
- [ ] Save migration tests
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

## Phase 6 — Full-world integration and balancing

- [ ] Multi-century simulation soak tests
- [ ] Performance budgets
- [ ] Economy balancing
- [ ] AI territorial warfare
- [ ] Save/load stress testing
- [ ] Native WC3 save/load regression
- [ ] City/world integrity recovery tests

## Phase 7 — Player release candidate

The first serious player test target: a substantially complete game intended to be played normally rather than as feature-by-feature QA.

- [ ] Full content pass
- [ ] Release save compatibility
- [ ] No known campaign-blocking defects
- [ ] Recovery tooling documented
- [ ] RC build packaged
