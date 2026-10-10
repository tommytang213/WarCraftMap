# Live authored quest stages

The live RPG journal consumes the `campaign_quests.py` projection of authored
quests, using the stage/objective/prerequisite semantics of
`_shared/engine/quest_event.py`. Generator version 23 emits all 304 multi-stage
quests, including initial stages, objective IDs, condition IDs, every entity
reference, successor edges, prerequisites and per-objective guidance. Packaging
rejects differences from the authored projection. Definitions remain scenario
content; `QuestStages.wurst` owns the reusable mechanism.

Acceptance checks completed prerequisite quests. A validated objective delivery
can affect only the stage active when delivery began. Single-successor stages
advance automatically; forks wait for `/queststage QUEST STAGE`, which accepts
only an authored successor after every current objective is complete. The journal
lists the current objective and available stage IDs. No branch is selected by
catalogue order. Readiness requires a completed terminal stage. A subsequent
physical `/turnin QUEST HERO` or `/interact LOCATION` awards the existing bounded
reward once. Acceptance, objective delivery and turn-in are separate actions.

`scenario/quest-condition-bindings.json` owns condition adapters. Travel to a
settlement is proved by a fresh physical interaction there; quest-location aliases
resolve to the same canonical settlement. Explicitly bound settlement deliveries
and reports use that boundary too. Protection obligations remain domain work.
The actor, loaded map, party map, movement class, distance and commit-time checks
from #381 still apply. Neither an absent building nor its destruction controls
persistent quest authority. Tracking and remote command context confer no presence.

Other conditions use `QuestConditionAuthority`: a domain must validate a stable
receipt against quest, active stage, objective, condition and all entity references.
Receipts are deduplicated per quest. No release command supplies receipts or sets
objective completion. Existing unscoped combat/settlement notifications cannot
prove an authored objective. An uninstalled condition adapter is a fail-closed
integration blocker, shown in the journal and generated `questIntegrationBlockers`.
The recording condition boundary in execution tests proves the state-machine
contract; it does **not** implement diplomatic recognition, archive deposits,
trade contracts, protection, historical events or other unfinished domain actions.

The Printed Compact therefore requires a verified London visit, a legal choice
of `negotiate` or `secure_archive`, a matching domain receipt for that branch, and
a verified return to Lisbon. Lisbon interactions alone cannot progress it. Its
live diplomacy/archive adapters remain explicitly outstanding. Authored treasury,
title and other reward batches, and settlement-local random quest integration,
remain separately accountable; this repair retains the existing bounded XP/currency
reward path without claiming those wider systems are complete.

Guidance follows the first incomplete objective in the active stage, then the
authored turn-in destination when ready. Conditions never supply marker coordinates.
Approximate guidance retains its authored search areas; regional guidance reveals
only the region; hidden and unfulfilled clue-gated guidance disclose no target.
Guidance is rebuilt from definitions and saved progress without replaying events.

## Save contract and migration

RPG domain **v5** extends each existing six-field `q` record with:

| Field | Meaning |
|---|---|
| `activeStageId` | Current authored stage, or empty before acceptance |
| `reachedStageIds` | Ordered legal path, including the initial stage |
| `completedObjectiveIds` | Only completed objectives from that path |
| `processedReceiptIds` | Consumed domain receipts |
| `legacyTerminal` | Explicit terminal outcome with unknown legacy history |

ID lists use `id~` tokens. Candidate validation rejects unknown IDs, duplicate
IDs/receipts, skipped or cyclic edges, unfinished predecessor stages, objectives
from unselected branches and premature readiness. All validation precedes mutation.
The original counter field is zero for authored graphs and cannot advance them.
Legacy non-graph consumers retain their counter codec. Hero v4 rank records are
unchanged. Campaign envelopes 1–8 still carry this independently versioned domain.

| Source RPG domain | Migration |
|---|---|
| v1 empty domain | Offered quests, no stage/objective/receipt history |
| v2–v4 offered | Offered with empty history |
| v2–v4 active or ready | Active at the initial authored stage, no completed objectives |
| v2–v4 complete or failed | Preserve status, cooldown, completion count, currency and hero rewards; mark `legacyTerminal` and retain empty stage/objective history |
| v5 | Validate and restore the exact selected path and evidence |

Legacy counters cannot identify which objectives were accomplished. Migration
neither fabricates that evidence nor retracts recorded terminal outcomes or rewards.
Resaving v5 is idempotent. The campaign transaction checkpoint includes these fields,
so failed reconstruction restores both authority and projections. Cross-map travel
uses the same codec and does not reevaluate conditions during reconstruction.

`AuthoredQuestTests.wurst` dispatches production acceptance, branch and interaction
commands for both Printed Compact paths, negative delivery cases, missing adapters,
prerequisites, turn-in, legacy codec migration and rollback. `RpgInteractionTests`
retains the physical rejection suite. The populated startup transfer fixture carries
a partial authored branch through actual travel and destination startup.
`test_quest_generation.py` compares every graph/prerequisite in generated JSON and
Wurst and rejects omitted stages, prerequisites and unsupported bindings. These are
developer-side tests; no incremental player QA is required.
