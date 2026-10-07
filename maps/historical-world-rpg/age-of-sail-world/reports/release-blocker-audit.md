# Phase 9 release-blocker audit

Result: **FAIL**

Unresolved campaign blockers: **21**

## Severity taxonomy

| ID | Release blocking | Definition |
|---|---:|---|
| `campaign_blocker` | yes | A reproducible failure that prevents starting, progressing, saving, loading, travelling, recovering, or completing otherwise reachable campaign content. |
| `critical_unclassified` | yes | A critical validation failure whose campaign impact has not yet been classified. |
| `major` | no | A bounded loss of optional content or degraded behavior with a deterministic workaround; no mandatory route or persisted authority is lost. |
| `minor` | no | Cosmetic, informational, or low-impact behavior that does not impede campaign play. |

## Declared campaign journeys and executed save fixtures

Each row executes save serialization/loading and schema-3 migration. Regions, maps, systems and end dates describe the declared itinerary; they are not evidence of executing that itinerary or native Warcraft saves. The soak below separately executes the headless simulation fixture.

| Stable ID | Declared branch | Seed | Declared regions | Declared maps | Save fixture result |
|---|---|---:|---:|---:|---|
| `JOURNEY-ATLANTIC-TO-PACIFIC` | maritime_expansion | 1450 | 7 | 8 | pass |
| `JOURNEY-ALTERNATE-HISTORY` | alternate_history | 1701 | 7 | 8 | pass |

## Player-facing runtime acceptance

Static readiness, executed production integration, built-artifact inspection and real-client status are separate. Source/test names and declared itineraries cannot satisfy integration. Missing same-revision execution or artifact evidence blocks this gate.

| System | Data complete | Headless simulation complete | Runtime integrated | Player-facing complete | Release-validated |
|---|---:|---:|---:|---:|---:|
| `campaign_launch` | yes | no | no | no | no |
| `origin_selection` | yes | no | no | no | no |
| `country_diplomacy` | yes | no | no | no | no |
| `trade` | yes | no | no | no | no |
| `army_fleet_control` | yes | no | no | no | no |
| `city_capture` | yes | no | no | no | no |
| `garrisons` | yes | no | no | no | no |
| `administration` | yes | no | no | no | no |
| `heroes` | yes | no | no | no | no |
| `inventory_equipment` | yes | no | no | no | no |
| `technology_institutions` | yes | no | no | no | no |
| `quests_journal` | yes | no | no | no | no |
| `treasures_discovery` | yes | no | no | no | no |
| `save_autosave_load` | yes | no | no | no | no |
| `cross_map_travel` | yes | no | no | no | no |
| `world_map` | yes | no | no | no | no |
| `remote_management` | yes | no | no | no | no |
| `government_rewards` | yes | no | no | no | no |
| `religion` | yes | no | no | no | no |
| `piracy` | yes | no | no | no | no |

## Findings

| Stable ID | Severity | Class | Context | Disposition |
|---|---|---|---|---|
| `RUNTIME-EVIDENCE-INCOMPLETE` | campaign_blocker | missing_runtime_integration | runtime-acceptance | unresolved |
| `RUNTIME-MISSING-ADMINISTRATION` | campaign_blocker | missing_runtime_integration | scenario/runtime-integration.json | unresolved |
| `RUNTIME-MISSING-ARMY-FLEET-CONTROL` | campaign_blocker | missing_runtime_integration | scenario/runtime-integration.json | unresolved |
| `RUNTIME-MISSING-CAMPAIGN-LAUNCH` | campaign_blocker | missing_runtime_integration | scenario/runtime-integration.json | unresolved |
| `RUNTIME-MISSING-CITY-CAPTURE` | campaign_blocker | missing_runtime_integration | scenario/runtime-integration.json | unresolved |
| `RUNTIME-MISSING-COUNTRY-DIPLOMACY` | campaign_blocker | missing_runtime_integration | scenario/runtime-integration.json | unresolved |
| `RUNTIME-MISSING-CROSS-MAP-TRAVEL` | campaign_blocker | missing_runtime_integration | scenario/runtime-integration.json | unresolved |
| `RUNTIME-MISSING-GARRISONS` | campaign_blocker | missing_runtime_integration | scenario/runtime-integration.json | unresolved |
| `RUNTIME-MISSING-GOVERNMENT-REWARDS` | campaign_blocker | missing_runtime_integration | scenario/runtime-integration.json | unresolved |
| `RUNTIME-MISSING-HEROES` | campaign_blocker | missing_runtime_integration | scenario/runtime-integration.json | unresolved |
| `RUNTIME-MISSING-INVENTORY-EQUIPMENT` | campaign_blocker | missing_runtime_integration | scenario/runtime-integration.json | unresolved |
| `RUNTIME-MISSING-ORIGIN-SELECTION` | campaign_blocker | missing_runtime_integration | scenario/runtime-integration.json | unresolved |
| `RUNTIME-MISSING-PIRACY` | campaign_blocker | missing_runtime_integration | scenario/runtime-integration.json | unresolved |
| `RUNTIME-MISSING-QUESTS-JOURNAL` | campaign_blocker | missing_runtime_integration | scenario/runtime-integration.json | unresolved |
| `RUNTIME-MISSING-RELIGION` | campaign_blocker | missing_runtime_integration | scenario/runtime-integration.json | unresolved |
| `RUNTIME-MISSING-REMOTE-MANAGEMENT` | campaign_blocker | missing_runtime_integration | scenario/runtime-integration.json | unresolved |
| `RUNTIME-MISSING-SAVE-AUTOSAVE-LOAD` | campaign_blocker | missing_runtime_integration | scenario/runtime-integration.json | unresolved |
| `RUNTIME-MISSING-TECHNOLOGY-INSTITUTIONS` | campaign_blocker | missing_runtime_integration | scenario/runtime-integration.json | unresolved |
| `RUNTIME-MISSING-TRADE` | campaign_blocker | missing_runtime_integration | scenario/runtime-integration.json | unresolved |
| `RUNTIME-MISSING-TREASURES-DISCOVERY` | campaign_blocker | missing_runtime_integration | scenario/runtime-integration.json | unresolved |
| `RUNTIME-MISSING-WORLD-MAP` | campaign_blocker | missing_runtime_integration | scenario/runtime-integration.json | unresolved |

## Audited release evidence

- 31 tracked validation reports
- 8 hashed release inputs
- 7 supported release-save schemas migrated and authority-checked
- 2 deterministic 1450–1820 soak runs
- Journey rows execute campaign-save round trips and migration; their route/system coverage is declared metadata.
- Native Warcraft save/load, physical-map launches and real-client journeys are not executed by this audit.
