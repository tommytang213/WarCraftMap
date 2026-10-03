# Phase 8 release-blocker audit

Result: **FAIL**

Unresolved campaign blockers: **6**

## Severity taxonomy

| ID | Release blocking | Definition |
|---|---:|---|
| `campaign_blocker` | yes | A reproducible failure that prevents starting, progressing, saving, loading, travelling, recovering, or completing otherwise reachable campaign content. |
| `critical_unclassified` | yes | A critical validation failure whose campaign impact has not yet been classified. |
| `major` | no | A bounded loss of optional content or degraded behavior with a deterministic workaround; no mandatory route or persisted authority is lost. |
| `minor` | no | Cosmetic, informational, or low-impact behavior that does not impede campaign play. |

## Deterministic campaign journeys

| Stable ID | Branch | Seed | Regions | Maps | Result |
|---|---|---:|---:|---:|---|
| `JOURNEY-ATLANTIC-TO-PACIFIC` | maritime_expansion | 1450 | 7 | 8 | pass |
| `JOURNEY-ALTERNATE-HISTORY` | alternate_history | 1701 | 7 | 8 | pass |

## Player-facing runtime acceptance

| System | Data complete | Headless simulation complete | Runtime integrated | Player-facing complete | Release-validated |
|---|---:|---:|---:|---:|---:|
| `campaign_launch` | yes | yes | yes | yes | yes |
| `origin_selection` | yes | yes | yes | yes | yes |
| `country_diplomacy` | yes | yes | yes | yes | yes |
| `trade` | yes | no | no | no | no |
| `army_fleet_control` | yes | yes | yes | yes | yes |
| `city_capture` | yes | yes | yes | yes | yes |
| `garrisons` | yes | yes | yes | yes | yes |
| `administration` | yes | yes | yes | yes | yes |
| `heroes` | yes | yes | no | no | no |
| `inventory_equipment` | yes | yes | no | no | no |
| `technology_institutions` | yes | yes | no | no | no |
| `quests_journal` | yes | yes | no | no | no |
| `treasures_discovery` | yes | yes | no | no | no |
| `save_autosave_load` | yes | yes | yes | yes | yes |
| `cross_map_travel` | yes | yes | yes | yes | yes |
| `world_map` | yes | yes | yes | yes | yes |
| `remote_management` | yes | yes | yes | yes | yes |
| `government_rewards` | yes | yes | yes | yes | yes |
| `religion` | yes | yes | yes | yes | yes |
| `piracy` | yes | yes | no | no | no |

## Findings

| Stable ID | Severity | Class | Context | Disposition |
|---|---|---|---|---|
| `RUNTIME-MISSING-HEROES` | campaign_blocker | missing_runtime_integration | scenario/runtime-integration.json | unresolved |
| `RUNTIME-MISSING-INVENTORY-EQUIPMENT` | campaign_blocker | missing_runtime_integration | scenario/runtime-integration.json | unresolved |
| `RUNTIME-MISSING-QUESTS-JOURNAL` | campaign_blocker | missing_runtime_integration | scenario/runtime-integration.json | unresolved |
| `RUNTIME-MISSING-TECHNOLOGY-INSTITUTIONS` | campaign_blocker | missing_runtime_integration | scenario/runtime-integration.json | unresolved |
| `RUNTIME-MISSING-TRADE` | campaign_blocker | missing_runtime_integration | scenario/runtime-integration.json | unresolved |
| `RUNTIME-MISSING-TREASURES-DISCOVERY` | campaign_blocker | missing_runtime_integration | scenario/runtime-integration.json | unresolved |

## Audited release evidence

- 31 tracked validation reports
- 7 hashed release inputs
- 5 supported release-save schemas migrated and authority-checked
- 2 deterministic 1450–1820 soak runs
- Fresh start, supported-save migration, manual save, rolling autosave, checkpoints, native save/load, interrupted transition recovery, and representation reconstruction are journey-gated.
