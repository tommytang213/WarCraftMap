# Playable runtime acceptance

Result: **PASS**

Each stage below records source text found, including references to tests; this audit does not execute those tests or establish control-flow reachability. Built W3N/W3X structure and compiled-text checks are separate from real-client smoke.

| System | Data | Headless | Runtime | Player-facing | Release validated |
|---|---:|---:|---:|---:|---:|
| `campaign_launch` | yes | yes | yes | yes | artifact gate |
| `origin_selection` | yes | yes | yes | yes | artifact gate |
| `country_diplomacy` | yes | yes | yes | yes | artifact gate |
| `trade` | yes | yes | yes | yes | artifact gate |
| `army_fleet_control` | yes | yes | yes | yes | artifact gate |
| `city_capture` | yes | yes | yes | yes | artifact gate |
| `garrisons` | yes | yes | yes | yes | artifact gate |
| `administration` | yes | yes | yes | yes | artifact gate |
| `heroes` | yes | yes | yes | yes | artifact gate |
| `inventory_equipment` | yes | yes | yes | yes | artifact gate |
| `technology_institutions` | yes | yes | yes | yes | artifact gate |
| `quests_journal` | yes | yes | yes | yes | artifact gate |
| `treasures_discovery` | yes | yes | yes | yes | artifact gate |
| `save_autosave_load` | yes | yes | yes | yes | artifact gate |
| `cross_map_travel` | yes | yes | yes | yes | artifact gate |
| `world_map` | yes | yes | yes | yes | artifact gate |
| `remote_management` | yes | yes | yes | yes | artifact gate |
| `government_rewards` | yes | yes | yes | yes | artifact gate |
| `religion` | yes | yes | yes | yes | artifact gate |
| `piracy` | yes | yes | yes | yes | artifact gate |

## Declared smoke journeys (source references only)

- `new-campaign-core-loops`
- `save-travel-remote-return`

## Failures

No unresolved source-readiness failures. The RC packager supplies the built-artifact gate; real-client smoke is tracked separately.
