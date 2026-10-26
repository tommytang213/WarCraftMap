# Playable runtime acceptance

Result: **PASS**

Automated candidate ready: **true**

Source markers establish static readiness only. Production integration requires passing executable tests with production-entry traces for the same revision and source contents. Artifact verification inspects the exact built bytes; it does not execute Warcraft III.

| Evidence level | Status | Execution |
|---|---|---|
| builtArtifact | pass | completed |
| realClient | not_run | not_run |
| runtimeIntegration | pass | completed |
| sourceStatic | pass | not_applicable |

Real-client release status: `blocked_pending_real_forsaken_kingdom_launch_smoke`.

| System | Data | Headless | Runtime | Player-facing | Release validated |
|---|---:|---:|---:|---:|---:|
| `campaign_launch` | yes | yes | yes | yes | yes |
| `origin_selection` | yes | yes | yes | yes | yes |
| `country_diplomacy` | yes | yes | yes | yes | yes |
| `trade` | yes | yes | yes | yes | yes |
| `army_fleet_control` | yes | yes | yes | yes | yes |
| `city_capture` | yes | yes | yes | yes | yes |
| `garrisons` | yes | yes | yes | yes | yes |
| `administration` | yes | yes | yes | yes | yes |
| `heroes` | yes | yes | yes | yes | yes |
| `inventory_equipment` | yes | yes | yes | yes | yes |
| `technology_institutions` | yes | yes | yes | yes | yes |
| `quests_journal` | yes | yes | yes | yes | yes |
| `treasures_discovery` | yes | yes | yes | yes | yes |
| `save_autosave_load` | yes | yes | yes | yes | yes |
| `cross_map_travel` | yes | yes | yes | yes | yes |
| `world_map` | yes | yes | yes | yes | yes |
| `remote_management` | yes | yes | yes | yes | yes |
| `government_rewards` | yes | yes | yes | yes | yes |
| `religion` | yes | yes | yes | yes | yes |
| `piracy` | yes | yes | yes | yes | yes |

## Declared smoke journeys (source references only)

- `new-campaign-core-loops`
- `save-travel-remote-return`

## Failures

Automated integration and artifact checks passed. Real-client status is tracked separately.
