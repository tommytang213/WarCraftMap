# Development Roadmap

<!-- req:ROAD-0001 --> The player should not be pulled into repetitive feature testing. Development gates are organized around automated/developer-side verification and a near-final player acceptance playthrough.

## Phase 0 — Repository bootstrap

- [x] <!-- req:ROAD-0002 --> Repository initialized
- [x] <!-- req:ROAD-0003 --> Category/map folder structure established
- [x] <!-- req:ROAD-0004 --> Agreed design constraints recorded
- [x] <!-- req:ROAD-0005 --> Pin Warcraft/Wurst project patch target to `v3.0`
- [x] <!-- req:ROAD-0006 --> Select Lua backend
- [x] <!-- req:ROAD-0007 --> Add initial Wurst project configuration/bootstrap package
- [x] <!-- req:ROAD-0008 --> Add CI typecheck workflow
- [x] <!-- req:ROAD-0009 --> First Wurst CI typecheck passed
- [x] <!-- req:ROAD-0010 --> Commit/create the clean source map folder
- [x] <!-- req:ROAD-0011 --> Establish reproducible source-map -> release `.w3x` packaging
- [x] <!-- req:ROAD-0012 --> Add full CI build artifact after the source map exists

## Phase 1 — Engine contracts

- [x] <!-- req:ROAD-0013 --> Stable ID conventions
- [x] <!-- req:ROAD-0014 --> Initial polity/province/settlement data contract
- [x] <!-- req:ROAD-0015 --> Ownership/control represented separately in starting world data
- [x] <!-- req:ROAD-0016 --> Unit/army/fleet model
- [x] <!-- req:ROAD-0017 --> Character/loyalty/relationship model
- [x] <!-- req:ROAD-0018 --> Technology/institution graph schema
- [x] <!-- req:ROAD-0019 --> Title/land/vassal model
- [x] <!-- req:ROAD-0020 --> Save schema + migration registry
- [x] <!-- req:ROAD-0021 --> Personal inventory, equipment, and tiered backpack contract
- [x] <!-- req:ROAD-0022 --> Navigation-zone/safe-position model

## Phase 2 — Headless validation foundation

- [x] <!-- req:ROAD-0023 --> Initial world data validator
- [x] <!-- req:ROAD-0024 --> Duplicate/missing world-reference detection
- [x] <!-- req:ROAD-0025 --> Technology cycle/reachability checks
- [x] <!-- req:ROAD-0026 --> Quest/event reference checks
- [x] <!-- req:ROAD-0027 --> Economy invariant tests
- [x] <!-- req:ROAD-0028 --> Save round-trip tests
- [x] <!-- req:ROAD-0029 --> Save migration tests
- [x] <!-- req:ROAD-0030 --> Inventory routing, validation, and over-capacity recovery tests
- [x] <!-- req:ROAD-0031 --> Navigation graph/connectivity validation and recovery-policy tests
- [x] <!-- req:ROAD-0032 --> Long timeline simulation harness

## Phase 3 — Warcraft runtime foundation

- [x] <!-- req:ROAD-0033 --> Latest-WC3 compatibility module
- [x] <!-- req:ROAD-0034 --> Map build pipeline
- [x] <!-- req:ROAD-0035 --> Command router + paged /help
- [x] <!-- req:ROAD-0036 --> UI pause policy for management screens
- [x] <!-- req:ROAD-0037 --> Campaign save manager
- [x] <!-- req:ROAD-0038 --> 15-slot rolling autosave scheduler
- [x] <!-- req:ROAD-0039 --> /unstuck + last-safe-position system
- [x] <!-- req:ROAD-0040 --> Player-only emergency invulnerability command

## Phase 4 — Core world simulation

- [x] <!-- req:ROAD-0041 --> Countries/polities
- [x] <!-- req:ROAD-0042 --> Provinces/states
- [x] <!-- req:ROAD-0043 --> Settlements
- [x] <!-- req:ROAD-0044 --> Timeline/eras
- [x] <!-- req:ROAD-0045 --> Technology/institutions
- [x] <!-- req:ROAD-0046 --> Economy/trade
- [x] <!-- req:ROAD-0047 --> Diplomacy/war
- [x] <!-- req:ROAD-0048 --> Armies/fleets
- [x] <!-- req:ROAD-0049 --> City capture/rebuild
- [x] <!-- req:ROAD-0050 --> Titles/land/taxation
- [x] <!-- req:ROAD-0051 --> Characters/relationships
- [x] <!-- req:ROAD-0052 --> Controller military tradition / category combat-experience progression
- [x] <!-- req:ROAD-0053 --> Equipment set definitions and partial/full threshold-bonus resolution
- [x] <!-- req:ROAD-0054 --> Quests/events/exploration

## Phase 5 — Age of Sail world content

- [x] <!-- req:ROAD-0055 --> Early performance stress harness and provisional budgets
- [x] <!-- req:ROAD-0056 --> Synthetic large-world simulation tests before full content population
- [x] <!-- req:ROAD-0057 --> Maximum-reasonable local battle performance test
- [x] <!-- req:ROAD-0058 --> Global geography/navigation topology
- [x] <!-- req:ROAD-0059 --> Multi-map campaign packaging and per-region/subregion physical map build pipeline
- [x] <!-- req:ROAD-0060 --> Cross-map campaign persistence, visited-map reconstruction, and versioned state transfer
- [x] <!-- req:ROAD-0061 --> Regional instance activation, boundary transitions, and cross-map/cross-region travel
- [x] <!-- req:ROAD-0062 --> Cross-region troop command and remote regional building management (authoritative simulation layer; physical cross-map command loading still integrates with the multi-map runtime)
- [x] <!-- req:ROAD-0063 --> World/region map presentation, discovery knowledge, and reusable location/search-area focus APIs
- [x] <!-- req:ROAD-0064 --> Custom quest journal and quest-to-map tracking integration
- [x] <!-- req:ROAD-0065 --> Europe
  - [x] <!-- req:ROAD-0066 --> Regional instances and geographic reference data
  - [x] <!-- req:ROAD-0067 --> 1450 political baseline (polities, provinces, sovereignty, and conflicts)
  - [x] <!-- req:ROAD-0068 --> Authoritative terrain generation and land/naval/amphibious/flying navigation
  - [x] <!-- req:ROAD-0069 --> Settlements and playable content
- [x] <!-- req:ROAD-0070 --> Africa
  - [x] <!-- req:ROAD-0071 --> Regional instances and geographic reference data
  - [x] <!-- req:ROAD-0072 --> 1450 political baseline (polities, provinces, sovereignty, tributary relationships, and conflicts)
  - [x] <!-- req:ROAD-0073 --> Authoritative terrain generation and land/naval/amphibious/flying navigation
  - [x] <!-- req:ROAD-0074 --> Settlements and playable content
- [x] <!-- req:ROAD-0075 --> Middle East / India
  - [x] <!-- req:ROAD-0076 --> Authoritative terrain generation and land/naval/amphibious/flying navigation
  - [x] <!-- req:ROAD-0077 --> Regional instances and geographic reference data
  - [x] <!-- req:ROAD-0078 --> 1450 political baseline (polities, provinces, sovereignty, and conflicts)
- [x] <!-- req:ROAD-0079 --> Southeast Asia
  - [x] <!-- req:ROAD-0080 --> Regional instances and geographic reference data
  - [x] <!-- req:ROAD-0081 --> 1450 political baseline (polities, provinces, sovereignty, tributary relationships, and conflicts)
  - [x] <!-- req:ROAD-0082 --> Authoritative terrain generation and land/naval/amphibious/flying navigation
  - [x] <!-- req:ROAD-0083 --> 1450 political baseline and authoritative settlement content
  - [x] <!-- req:ROAD-0084 --> Ports, trade routes, transitions, economy profiles, and abstract activation data
- [x] <!-- req:ROAD-0085 --> East Asia
  - [x] <!-- req:ROAD-0086 --> Regional instances and geographic reference data
  - [x] <!-- req:ROAD-0087 --> Authoritative terrain generation and land/naval/amphibious/flying navigation
  - [x] <!-- req:ROAD-0088 --> 1450 political baseline (polities, provinces, sovereignty, tributary relationships, and conflicts)
  - [x] <!-- req:ROAD-0089 --> Priority settlements, ports, trade routes, transitions, economy profiles, and abstract activation data
- [x] <!-- req:ROAD-0090 --> Americas / Caribbean
  - [x] <!-- req:ROAD-0091 --> Regional instances and geographic reference data
  - [x] <!-- req:ROAD-0092 --> 1450 political baseline (polities, provinces, confederated and decentralized authority, diplomacy, and conflicts)
  - [x] <!-- req:ROAD-0093 --> Authoritative terrain generation and land/naval/amphibious/flying navigation
  - [x] <!-- req:ROAD-0094 --> 1450 political baseline (polities, provinces, sovereignty, relationships, and conflicts)
  - [x] <!-- req:ROAD-0095 --> Priority settlements, ports, trade routes, transitions, economy profiles, and abstract activation data
- [x] <!-- req:ROAD-0096 --> Pacific
  - [x] <!-- req:ROAD-0097 --> Regional instances and geographic reference data
  - [x] <!-- req:ROAD-0098 --> 1450 political baseline (island polities, chiefdoms, confederated and decentralized communities, diplomacy, and political-center exceptions)
  - [x] <!-- req:ROAD-0099 --> Authoritative terrain generation and land/naval/amphibious/flying navigation
  - [x] <!-- req:ROAD-0100 --> 1450 political authority, priority settlements, ports, routes, transitions, economies, and abstract activation data
- [x] <!-- req:ROAD-0101 --> Historical tech/event timeline
- [x] <!-- req:ROAD-0102 --> Country-specific units/content
- [x] <!-- req:ROAD-0103 --> Recruitable characters
- [x] <!-- req:ROAD-0104 --> Regional and long-chain quests
- [x] <!-- req:ROAD-0105 --> Treasures/secrets

## Phase 6 — Visual/content production

<!-- req:ROAD-0106 --> Status: complete. All Phase 6 integration gates are recorded in the deterministic asset audit.

- [x] <!-- req:ROAD-0107 --> Stock/Reforged asset catalogue and historical-fit matrix
- [x] <!-- req:ROAD-0108 --> Country/unit visual language
- [x] <!-- req:ROAD-0109 --> Settlement/building visual sets
- [x] <!-- req:ROAD-0110 --> Custom icons/textures where needed
- [x] <!-- req:ROAD-0111 --> Custom 3D models where stock assets are insufficient
- [x] <!-- req:ROAD-0112 --> Sound/music/ambient pass
- [x] <!-- req:ROAD-0113 --> Placeholder-removal audit

## Phase 7 — Full-world integration and balancing

- [x] <!-- req:ROAD-0114 --> Multi-century simulation soak tests
- [x] <!-- req:ROAD-0115 --> Finalize performance budgets against full-world content
- [x] <!-- req:ROAD-0116 --> Economy balancing
- [x] <!-- req:ROAD-0117 --> AI territorial warfare
- [x] <!-- req:ROAD-0118 --> Save/load stress testing
- [x] <!-- req:ROAD-0119 --> Native WC3 save/load regression
- [x] <!-- req:ROAD-0120 --> City/world integrity recovery tests

## Phase 8 — Player release candidate

<!-- req:ROAD-0121 --> The first serious player test target: a substantially complete game intended to be played normally rather than as feature-by-feature QA. Phase 8 is a substantial content-completion pass, not merely final polish of the Phase 5 first-pass catalogues.

- [x] <!-- req:ROAD-0122 --> Full content pass
  - [x] <!-- req:ROAD-0123 --> Expand the land-unit roster into layered common, regional/cultural, polity-specific, era/technology, and elite/unique content with meaningful upgrade/replacement progression.
  - [x] <!-- req:ROAD-0124 --> Expand the naval roster with regional ship families, polity-specific vessels, merchant/transport/warship roles, era/technology progression, and meaningful variants built on reusable hull/runtime families.
  - [x] <!-- req:ROAD-0125 --> Implement settlement administration and political-office appointments, including deterministic culturally appropriate minor officials, player appointments, administrative capacity, loyalty consequences, and office/history persistence.
  - [x] <!-- req:ROAD-0126 --> Implement dynamic AI settlement garrisons and local-defense simulation: AI-controlled defenders, authoritative reserve/manpower state, bounded reinforcement waves, post-combat despawn/reconstruction, and technology/polity/region/administrator-driven composition.
  - [x] <!-- req:ROAD-0127 --> Expand historical rulers, commanders, admirals, recruitable characters, generated officials, personal quests, relationships, and office/command assignments.
  - [x] <!-- req:ROAD-0128 --> Expand the prototype goods catalogue into the authored settlement-level global commodity/trade set with production, consumption, availability, pricing, logistics, and regional differentiation.
  - [x] <!-- req:ROAD-0129 --> Expand technology/institution progression and historical/conditional event coverage across 1450–1820.
  - [x] <!-- req:ROAD-0130 --> Expand regional quests, campaign-spanning quest chains, personal quests, treasures, secrets, discoveries, and other exploration content.
  - [x] <!-- req:ROAD-0131 --> Audit every major region, polity, era, military category, settlement role, economy role, character role, quest type, treasure type, and progression branch for materially thin or placeholder-like player-facing content.
  - [x] <!-- req:ROAD-0132 --> Expand 1450 settlement coverage to historically grounded release-scale density, targeting roughly 800-1,200 meaningful authored settlements with real-world placement and appropriate polity/province/control context.
  - [x] <!-- req:ROAD-0133 --> Expand player-use stores and RPG inventory: region/era-aware merchant archetypes, common/regional/polity-specific/rare/unique equipment and consumables, item levels/rarities/comparison UI, 100+ unique/historical items, and roughly 50-80 equipment sets.
  - [x] <!-- req:ROAD-0134 --> Implement persistent individual ship equipment/refits, crew/veterancy/history progression, and meaningful continuous ship-experience bonuses with role-specific milestone traits.
  - [x] <!-- req:ROAD-0135 --> Expand named historical/recruitable heroes toward release-scale regional/era coverage and implement long-campaign hero progression to level 300 with deep skill/mastery/personal progression, unlimited recruited roster, and a high local field-group target subject to performance validation.
  - [x] <!-- req:ROAD-0136 --> Expand progression breadth toward roughly 180-250 technologies and 20-30 institutions/reforms across the full 1450-1820 timeline.
  - [x] <!-- req:ROAD-0137 --> Expand historical/conditional event breadth toward roughly 200-300 authored events with dynamic world-state-driven event instances.
  - [x] <!-- req:ROAD-0138 --> Expand world quest density toward roughly 400-600 authored campaign/regional/personal/polity/event-linked quests/chains plus a separate release-scale settlement-local random side-quest catalogue. Every ordinary playable settlement should normally expose at least one local random quest at campaign start, with more simultaneous opportunities in larger/wealthier/more connected cities; selection, persistence, rewards, and anti-farming rules follow the locked settlement-local quest design.
  - [x] <!-- req:ROAD-0139 --> Expand player-facing land/naval military breadth toward roughly 350-500+ meaningful types/variants while preserving shared runtime templates where appropriate.
  - [x] <!-- req:ROAD-0140 --> Re-run the final content-breadth audit against the release-scale density targets above; coverage presence alone is not sufficient to pass.
- [x] <!-- req:ROAD-0141 --> Release save compatibility
- [x] <!-- req:ROAD-0142 --> No known campaign-blocking defects
- [x] <!-- req:ROAD-0143 --> Recovery tooling documented
- [x] <!-- req:ROAD-0144 --> RC build packaged
