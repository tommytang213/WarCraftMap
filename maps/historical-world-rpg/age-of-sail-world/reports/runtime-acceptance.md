# Playable runtime acceptance

Result: **FAIL**

Automated candidate ready: **false**

Source markers establish static readiness only. Production integration requires passing executable tests with production-entry traces for the same revision and source contents. Artifact verification inspects the exact built bytes; it does not execute Warcraft III.

| Evidence level | Status | Execution |
|---|---|---|
| sourceStatic | pass | not_applicable |
| runtimeIntegration | fail | not_run |
| builtArtifact | fail | not_run |
| realClient | not_run | not_run |

Real-client release status: `blocked_pending_real_forsaken_kingdom_launch_smoke`.

| System | Data | Headless | Runtime | Player-facing | Release validated |
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

## Declared smoke journeys (source references only)

- `new-campaign-core-loops`
- `save-travel-remote-return`

## Failures

- required integration executionStatus is not completed
- required executable production-path evidence is missing
- runtimeIntegration: required evidence does not pass
- runtimeIntegration: execution is missing, not_run or stale
- runtimeIntegration: verified logSha256 is missing or malformed
- runtimeIntegration: verified inputSetSha256 is missing or malformed
- same-revision built W3N/W3X verification is missing
- builtArtifact: required evidence does not pass
- builtArtifact: execution is missing, not_run or stale
- builtArtifact: verified artifactSha256 is missing or malformed
- campaign_launch: required production integration/release validation is incomplete
- origin_selection: required production integration/release validation is incomplete
- country_diplomacy: required production integration/release validation is incomplete
- trade: required production integration/release validation is incomplete
- army_fleet_control: required production integration/release validation is incomplete
- city_capture: required production integration/release validation is incomplete
- garrisons: required production integration/release validation is incomplete
- administration: required production integration/release validation is incomplete
- heroes: required production integration/release validation is incomplete
- inventory_equipment: required production integration/release validation is incomplete
- technology_institutions: required production integration/release validation is incomplete
- quests_journal: required production integration/release validation is incomplete
- treasures_discovery: required production integration/release validation is incomplete
- save_autosave_load: required production integration/release validation is incomplete
- cross_map_travel: required production integration/release validation is incomplete
- world_map: required production integration/release validation is incomplete
- remote_management: required production integration/release validation is incomplete
- government_rewards: required production integration/release validation is incomplete
- religion: required production integration/release validation is incomplete
- piracy: required production integration/release validation is incomplete
