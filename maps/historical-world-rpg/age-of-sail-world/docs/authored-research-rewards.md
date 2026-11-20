# Scoped authored research rewards

## Scope and remaining gaps

Only quests whose authored outcome list contains `quest_technology_complete_research`
receive the new reward-batch adapter. This is data-driven, not a quest-ID switch.
Currently those are **Stars and Pepper** and **Ocean of Accounts**. Every eligible
outcome in their batch must be implemented before turn-in can commit.

Both currently remain blocked: Stars and Pepper also promises a treasury change
without an amount; Ocean of Accounts additionally promises unsupported treasury,
title, diplomatic and discovery effects. No amount or substitute effect is invented.
The journal and rejected turn-in name the unsupported outcome. They award neither
research nor generic XP/currency when an eligible sibling is unsupported.

The other 302 generated quests retain the existing generic reward path in this
bounded change. Their authored outcomes are **not** implemented by this adapter.
`scenario-runtime.json.questRewardIntegration` identifies the selected batches,
unsupported outcomes, reached-stage requirements and this remaining generic gap.
This is not evidence of complete quest chains or native acceptance.

## Authoritative semantics and intentional runtime differences

Python `_shared/engine/historical_events.py:apply_effects` implements
`complete_research` by idempotently adding a known target to `completedResearchIds`.
It neither charges a research cost nor unlocks prerequisites. Python's
`quest_event.py` applies eligible outcomes as an all-or-nothing external-state
replacement; `requiresReachedStageIds` is an all-required-stages subset condition.

The live Wurst port preserves those grant and batch semantics, with two explicit
runtime adaptations:

* Python's historical-state research list is global; the single-player live
  campaign stores this earned grant under the existing `player` research identity,
  regardless of national allegiance or the research resource port's controller.
* Live explicit `/turnin` and physical `/interact` turn-in share the same scoped
  transaction and research synchronization. They require the existing ready-state, recruited field hero,
  fresh physical turn-in and campaign-player boundary. A completed objective,
  branch selection, journal visit or load is not a reward delivery.

In particular, a supported earned grant of Standardized Charts does not silently
grant Celestial Navigation or Movable Type Printing, and does not simulate a paid
research purchase. Ordinary paid research keeps its cost/prerequisite/eligibility
rules unchanged. Unknown/malformed target definitions fail closed.

## Atomicity and persistence

Normal readiness, cooldown, hero XP bounds and generic currency bounds are checked
first. The selected batch then checks all eligible siblings and total new research
capacity, deduplicates already-owned/repeated targets, and prepares its bounded
commit list. No projection or resource callback occurs between preparation and
commit. Existing quest completion, XP/currency and research IDs commit together;
matching active player research objectives are synchronized and the existing
non-fallible entitlement replacement runs afterward. This does not turn in those
other quests or deliver their rewards.

No save version or migration changes are introduced. Existing quest completion
and controller research IDs persist the transaction. Repeat turn-in cannot replay
it. An already-completed old save remains completed without retroactively receiving
new research; restoration only reconstructs entitlements for saved completion IDs.

## Tests

`QuestRewardTests` uses clearly synthetic supported-only batches for positive live
command tests. Generated definitions for both real mixed-reward quests are negative
controls. Tests cover unready/foreign/null/remote/stale-presence rejection, unknown
targets, capacity/XP/currency bounds, stage-qualified siblings, duplicate/already-owned
research, current-codec restoration, old completion no-replay, and an unaffected
existing generic turn-in. These are interpreted Wurst tests, not native acceptance.

A blocked physical turn-in does not suppress unrelated legitimate visit progress.
Its response explicitly reports that other progress occurred while the named quest
reward batch remained blocked, rather than displaying an unconditional success.
