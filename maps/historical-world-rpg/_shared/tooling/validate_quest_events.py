"""Reusable validation for declarative quest and event graphs."""

ENTITY_COLLECTIONS = {
    "polity": "polities",
    "province": "provinces",
    "settlement": "settlements",
    "character": "characters",
    "strategic_unit": "strategicUnits",
    "army": "armies",
    "fleet": "fleets",
    "technology": "technologies",
    "institution": "institutions",
    "navigation_zone": "navigationZones",
}


def validate(data, fail, require_id, unique_index):
    """Validate quest/event records and return their stable-ID indexes."""
    quests = unique_index(data.get("quests", []), "quests")
    events = unique_index(data.get("events", []), "events")
    world = {
        kind: unique_index(data.get(collection, []), collection)
        for kind, collection in ENTITY_COLLECTIONS.items()
    }

    def array(value, path, nonempty=False):
        if not isinstance(value, list) or (nonempty and not value):
            fail(f"{path}: must be a{' non-empty' if nonempty else 'n'} array")
        return value

    def entity_refs(values, path):
        seen = set()
        for index, reference in enumerate(array(values, path)):
            ref_path = f"{path}[{index}]"
            if not isinstance(reference, dict):
                fail(f"{ref_path}: must be an object")
            kind, ident = reference.get("kind"), reference.get("id")
            if kind not in world:
                fail(f"{ref_path}.kind: unsupported world entity kind {kind!r}")
            require_id(ident, f"{ref_path}.id")
            if ident not in world[kind]:
                fail(f"{ref_path}.id: unresolved {kind} reference {ident!r}")
            key = (kind, ident)
            if key in seen:
                fail(f"{ref_path}: duplicate world entity reference {kind}:{ident}")
            seen.add(key)

    stages_by_quest = {}
    transitions_by_quest = {}
    for quest_id, quest in quests.items():
        base = f"quest {quest_id}"
        stages = unique_index(quest.get("stages", []), f"{base}.stages")
        objectives = unique_index(quest.get("objectives", []), f"{base}.objectives")
        stages_by_quest[quest_id] = stages
        initial = quest.get("initialStageId")
        if initial not in stages:
            fail(f"{base}.initialStageId: missing stage reference {initial!r}")
        assigned = set()
        transitions = set()
        for stage_id, stage in stages.items():
            path = f"{base}.stages[{stage_id}]"
            objective_ids = array(stage.get("objectiveIds"), f"{path}.objectiveIds")
            for objective_id in objective_ids:
                require_id(objective_id, f"{path}.objectiveIds")
                if objective_id not in objectives:
                    fail(f"{path}.objectiveIds: missing objective reference {objective_id!r}")
                if objective_id in assigned:
                    fail(f"{path}.objectiveIds: objective {objective_id!r} is assigned more than once")
                assigned.add(objective_id)
            next_ids = array(stage.get("nextStageIds"), f"{path}.nextStageIds")
            for next_id in next_ids:
                require_id(next_id, f"{path}.nextStageIds")
                if next_id not in stages:
                    fail(f"{path}.nextStageIds: missing stage reference {next_id!r}")
                if next_id == stage_id:
                    fail(f"{path}.nextStageIds: invalid self transition {stage_id!r}")
                transitions.add((stage_id, next_id))
        missing_objectives = set(objectives) - assigned
        if missing_objectives:
            ident = sorted(missing_objectives)[0]
            fail(f"{base}.objectives[{ident}]: objective is not assigned to a stage")

        visiting, visited = set(), set()
        def visit_stage(stage_id):
            if stage_id in visiting:
                fail(f"{base}.stages[{stage_id}].nextStageIds: transition cycle detected")
            if stage_id in visited:
                return
            visiting.add(stage_id)
            for source, target in transitions:
                if source == stage_id:
                    visit_stage(target)
            visiting.remove(stage_id)
            visited.add(stage_id)
        visit_stage(initial)
        unreachable = set(stages) - visited
        if unreachable:
            ident = sorted(unreachable)[0]
            fail(f"{base}.stages[{ident}]: stage is unreachable from initialStageId")
        transitions_by_quest[quest_id] = transitions

        for objective_id, objective in objectives.items():
            path = f"{base}.objectives[{objective_id}]"
            require_id(objective.get("conditionId"), f"{path}.conditionId")
            entity_refs(objective.get("entityRefs"), f"{path}.entityRefs")

    dependency_edges = {f"quest:{ident}": [] for ident in quests}
    dependency_edges.update({f"event:{ident}": [] for ident in events})

    def prerequisites(values, path, owner_key):
        seen = set()
        for index, prerequisite in enumerate(array(values, path)):
            item_path = f"{path}[{index}]"
            if not isinstance(prerequisite, dict):
                fail(f"{item_path}: must be an object")
            kind = prerequisite.get("kind")
            ident = prerequisite.get("id")
            require_id(ident, f"{item_path}.id")
            if kind == "quest_completed":
                if ident not in quests:
                    fail(f"{item_path}.id: missing quest reference {ident!r}")
                target = f"quest:{ident}"
            elif kind == "event_occurred":
                if ident not in events:
                    fail(f"{item_path}.id: missing event reference {ident!r}")
                target = f"event:{ident}"
            elif kind == "quest_stage_reached":
                if ident not in quests:
                    fail(f"{item_path}.id: missing quest reference {ident!r}")
                stage_id = prerequisite.get("stageId")
                if stage_id not in stages_by_quest[ident]:
                    fail(f"{item_path}.stageId: missing stage reference {stage_id!r} in quest {ident!r}")
                target = f"quest:{ident}"
            elif kind == "scenario_condition":
                require_id(prerequisite.get("conditionId"), f"{item_path}.conditionId")
                entity_refs(prerequisite.get("entityRefs"), f"{item_path}.entityRefs")
                continue
            else:
                fail(f"{item_path}.kind: unsupported prerequisite kind {kind!r}")
            key = (kind, ident, prerequisite.get("stageId"))
            if key in seen:
                fail(f"{item_path}: duplicate prerequisite {ident!r}")
            seen.add(key)
            dependency_edges[owner_key].append((target, item_path))

    def outcomes(values, path, repeatable_owner=False):
        outcome_ids = set()
        for index, outcome in enumerate(array(values, path)):
            item_path = f"{path}[{index}]"
            if not isinstance(outcome, dict):
                fail(f"{item_path}: must be an object")
            ident = outcome.get("id")
            require_id(ident, f"{item_path}.id")
            if ident in outcome_ids:
                fail(f"{item_path}.id: duplicate outcome ID {ident!r}")
            outcome_ids.add(ident)
            kind = outcome.get("kind")
            if kind == "advance_quest":
                quest_id = outcome.get("questId")
                source, target = outcome.get("fromStageId"), outcome.get("toStageId")
                if quest_id not in quests:
                    fail(f"{item_path}.questId: missing quest reference {quest_id!r}")
                if source not in stages_by_quest[quest_id]:
                    fail(f"{item_path}.fromStageId: missing stage reference {source!r} in quest {quest_id!r}")
                if target not in stages_by_quest[quest_id]:
                    fail(f"{item_path}.toStageId: missing stage reference {target!r} in quest {quest_id!r}")
                if (source, target) not in transitions_by_quest[quest_id]:
                    fail(f"{item_path}: invalid stage transition {source!r} -> {target!r} for quest {quest_id!r}")
            elif kind == "start_quest":
                if outcome.get("questId") not in quests:
                    fail(f"{item_path}.questId: missing quest reference {outcome.get('questId')!r}")
            elif kind == "emit_event":
                event_id = outcome.get("eventId")
                if event_id not in events:
                    fail(f"{item_path}.eventId: missing event reference {event_id!r}")
                if outcome.get("repeat") is True and not events[event_id].get("repeatable"):
                    fail(f"{item_path}.repeat: event {event_id!r} is not repeatable")
            elif kind == "scenario_outcome":
                require_id(outcome.get("outcomeId"), f"{item_path}.outcomeId")
                entity_refs(outcome.get("entityRefs"), f"{item_path}.entityRefs")
            else:
                fail(f"{item_path}.kind: unsupported outcome kind {kind!r}")

    for quest_id, quest in quests.items():
        prerequisites(quest.get("prerequisites"), f"quest {quest_id}.prerequisites", f"quest:{quest_id}")
        outcomes(quest.get("outcomes"), f"quest {quest_id}.outcomes")

    for event_id, event in events.items():
        base = f"event {event_id}"
        if not isinstance(event.get("repeatable"), bool):
            fail(f"{base}.repeatable: must be a boolean")
        triggers = unique_index(event.get("triggers", []), f"{base}.triggers")
        if not triggers:
            fail(f"{base}.triggers: at least one trigger is required")
        for trigger_id, trigger in triggers.items():
            path = f"{base}.triggers[{trigger_id}]"
            require_id(trigger.get("conditionId"), f"{path}.conditionId")
            entity_refs(trigger.get("entityRefs"), f"{path}.entityRefs")
        prerequisites(event.get("prerequisites"), f"{base}.prerequisites", f"event:{event_id}")
        outcomes(event.get("outcomes"), f"{base}.outcomes", event["repeatable"])

    visiting, visited = set(), set()
    def visit_dependency(node, via_path=None):
        if node in visiting:
            fail(f"{via_path}: cyclic prerequisite relationship requires {node!r}")
        if node in visited:
            return
        visiting.add(node)
        for target, path in dependency_edges[node]:
            visit_dependency(target, path)
        visiting.remove(node)
        visited.add(node)
    for node in dependency_edges:
        visit_dependency(node)
    return quests, events
