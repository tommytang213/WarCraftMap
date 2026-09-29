"""Deterministic delivery of scenario-authored historical pressures.

The module is deliberately scenario neutral.  It bridges dated timeline occurrences to
the quest/event runtime, chooses an eligible authored alternative without consuming a
random stream, and commits the complete external-state replacement transactionally.
"""
from __future__ import annotations

import copy
import hashlib
from datetime import date
from typing import Mapping

import quest_event


class HistoricalEventError(quest_event.QuestEventError):
    pass


def _eligible(choice, state):
    """Evaluate the small, data-only condition language used by historical content."""
    for condition in choice.get("conditions", []):
        kind, entity = condition["kind"], condition.get("entityId")
        if kind == "entity_exists" and entity not in state.get("activeEntityIds", []):
            return False
        if kind == "entity_absent" and entity in state.get("activeEntityIds", []):
            return False
        if kind == "owner_is" and state.get("ownership", {}).get(entity) != condition.get("valueId"):
            return False
        if kind == "war_active" and condition.get("valueId") not in state.get("activeWars", []):
            return False
        if kind == "war_inactive" and condition.get("valueId") in state.get("activeWars", []):
            return False
        if kind == "research_completed" and entity not in state.get("completedResearchIds", []):
            return False
        if kind == "research_missing" and entity in state.get("completedResearchIds", []):
            return False
    return True


def choose_alternative(event, occurrence_key, state):
    """Return a stable weighted choice from the alternatives valid in current history."""
    choices = [x for x in event["historical"]["alternatives"] if _eligible(x, state)]
    if not choices:
        return None
    choices.sort(key=lambda x: x["id"])
    total = sum(x["weight"] for x in choices)
    digest = hashlib.sha256(f"{event['id']}:{occurrence_key}".encode()).digest()
    pick = int.from_bytes(digest[:8], "big") % total
    for choice in choices:
        if pick < choice["weight"]:
            return choice
        pick -= choice["weight"]
    raise AssertionError("unreachable weighted choice")


def apply_effects(state, effects):
    """Validate all effects against a copy, then return the all-or-nothing result."""
    result = copy.deepcopy(dict(state))
    for effect in effects:
        kind, target, value = effect["kind"], effect.get("targetId"), effect.get("value")
        if kind == "adjust_treasury":
            table = result.setdefault("treasury", {})
            if target not in table or not isinstance(table[target], (int, float)):
                raise HistoricalEventError(f"invalid treasury target {target!r}")
            table[target] += value
        elif kind == "adjust_relations":
            pair = effect.get("targetIds", [])
            if len(pair) != 2 or any(x not in result.get("activeEntityIds", []) for x in pair):
                raise HistoricalEventError("invalid diplomatic relation target")
            key = ":".join(sorted(pair)); table = result.setdefault("relations", {})
            table[key] = table.get(key, 0) + value
        elif kind == "set_controller":
            if target not in result.get("ownership", {}) or value not in result.get("activeEntityIds", []):
                raise HistoricalEventError(f"invalid control transfer {target!r}")
            # Legal ownership is intentionally untouched.
            result.setdefault("control", copy.deepcopy(result["ownership"]))[target] = value
        elif kind == "complete_research":
            if target not in result.get("knownResearchIds", []):
                raise HistoricalEventError(f"invalid research target {target!r}")
            completed = result.setdefault("completedResearchIds", [])
            if target not in completed: completed.append(target); completed.sort()
        elif kind == "set_flag":
            result.setdefault("flags", {})[target] = value
        elif kind == "adjust_prosperity":
            table = result.setdefault("prosperity", {})
            if target not in table: raise HistoricalEventError(f"invalid prosperity target {target!r}")
            table[target] = max(0, min(100, table[target] + value))
        else:
            raise HistoricalEventError(f"unsupported historical effect {kind!r}")
    return result


class HistoricalExtensions(quest_event.NullScenarioExtensions):
    """Quest/event extension used by scenario timelines and headless simulation."""
    def __init__(self, events):
        self.events = {x["id"]: copy.deepcopy(x) for x in events}

    def evaluate_condition(self, condition_id, entity_refs, snapshot, context):
        if condition_id != "historical_state_allows":
            raise HistoricalEventError(f"unknown historical condition {condition_id!r}")
        event = self.events.get(context.get("eventId"))
        return event is not None and choose_alternative(event, context.get("occurrenceKey", ""), snapshot["externalState"]) is not None

    def apply_outcomes(self, outcomes, snapshot, context):
        if any(x["outcomeId"] != "resolve_historical_pressure" for x in outcomes):
            raise HistoricalEventError("unknown historical outcome adapter")
        event = self.events.get(context.get("eventId"))
        if event is None: raise HistoricalEventError("missing historical event definition")
        choice = choose_alternative(event, context.get("occurrenceKey", ""), snapshot["externalState"])
        if choice is None: raise HistoricalEventError("historical outcome has no eligible alternative")
        result = copy.deepcopy(snapshot)
        result["externalState"] = apply_effects(snapshot["externalState"], choice["effects"])
        result["externalState"].setdefault("historicalLog", []).append({"eventId": event["id"], "alternativeId": choice["id"], "occurrenceKey": context.get("occurrenceKey")})
        return result


def enqueue_occurrences(runtime, occurrences):
    """Bridge canonical timeline order into idempotent quest/event triggers."""
    for item in occurrences:
        runtime.enqueue_trigger(item.event_id, "scheduled", due_time=date.fromisoformat(item.date).toordinal(), priority=item.priority,
            occurrence_key=f"{item.schedule_id}:{item.occurrence}:{item.date}",
            context={"eventId": item.event_id, "occurrenceKey": f"{item.schedule_id}:{item.occurrence}:{item.date}", "date": item.date})
