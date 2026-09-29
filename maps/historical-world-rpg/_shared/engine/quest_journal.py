"""Deterministic, scenario-neutral quest journal and map-guidance projection."""
from __future__ import annotations

import copy
import heapq
import re
from collections.abc import Mapping

STATE_VERSION = 1
QUEST_JOURNAL_WORLD_STATE_KEY = "questJournalState"
_ID = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")
_PRECISIONS = frozenset({"exact", "approximate", "region", "hidden"})
_GROUP_ORDER = ("active", "awaiting_turn_in", "completed", "failed", "cancelled")


class QuestJournalError(ValueError):
    pass


def _stable_id(value, context):
    if not isinstance(value, str) or not _ID.fullmatch(value):
        raise QuestJournalError(f"{context}: invalid stable ID {value!r}")
    return value


def _index(records, context):
    if not isinstance(records, list):
        raise QuestJournalError(f"{context} must be an array")
    result = {}
    for record in records:
        if not isinstance(record, Mapping):
            raise QuestJournalError(f"{context} entries must be objects")
        ident = _stable_id(record.get("id"), context)
        if ident in result:
            raise QuestJournalError(f"{context}: duplicate ID {ident!r}")
        result[ident] = copy.deepcopy(dict(record))
    return result


class QuestJournal:
    """Read-only projection over authoritative quest, knowledge, and geography state.

    UI handles are intentionally absent. Rebuilding the journal after load or frame
    loss means calling ``reconstruct`` again with current authoritative snapshots.
    """

    def __init__(self, definitions, geography, locations, *, state=None):
        self.quests = _index(definitions.get("quests", []), "quests")
        self.regions = _index(geography.get("regions", []), "regions")
        self.transitions = {
            **_index(geography.get("boundaries", []), "boundaries"),
            **_index(geography.get("routes", []), "routes"),
        }
        self.locations = _index(locations, "locations")
        self._validate_definitions()
        self.state = self.validate_state(state or {
            "schemaVersion": STATE_VERSION,
            "trackedQuestId": None,
            "discoveredLocationIds": [],
            "discoveredTransitionIds": [],
            "clueIds": [],
        })

    def _validate_ref(self, ref, context):
        if not isinstance(ref, Mapping):
            raise QuestJournalError(f"{context} must be an object")
        kind = _stable_id(ref.get("kind"), context)
        ident = _stable_id(ref.get("id"), context)
        return {"kind": kind, "id": ident}

    def _validate_definitions(self):
        for location_id, location in self.locations.items():
            region_id = location.get("regionId")
            if region_id not in self.regions:
                raise QuestJournalError(f"location {location_id}: missing region")
            if "settlementId" in location:
                _stable_id(location["settlementId"], f"location {location_id}.settlementId")
            position = location.get("position")
            if not isinstance(position, Mapping) or not all(
                isinstance(position.get(axis), (int, float)) and not isinstance(position.get(axis), bool)
                for axis in ("x", "y")
            ):
                raise QuestJournalError(f"location {location_id}: invalid position")
        for transition_id, transition in self.transitions.items():
            for endpoint in ("from", "to"):
                if transition.get(endpoint, {}).get("regionId") not in self.regions:
                    raise QuestJournalError(f"transition {transition_id}: missing region")
        for quest_id, quest in self.quests.items():
            stages = _index(quest.get("stages", []), f"quest {quest_id}.stages")
            objectives = _index(quest.get("objectives", []), f"quest {quest_id}.objectives")
            journal = quest.get("journal", {})
            if not isinstance(journal, Mapping):
                raise QuestJournalError(f"quest {quest_id}.journal must be an object")
            for field in ("giver", "turnIn"):
                if field in journal:
                    self._validate_ref(journal[field], f"quest {quest_id}.{field}")
            destinations = journal.get("destinations", {})
            if not isinstance(destinations, Mapping):
                raise QuestJournalError(f"quest {quest_id}.destinations must be an object")
            for objective_id, destination in destinations.items():
                if objective_id not in objectives:
                    raise QuestJournalError(f"quest {quest_id}: destination has missing objective")
                self._validate_destination(destination, f"quest {quest_id}.{objective_id}")
            if "turnInDestination" in journal:
                self._validate_destination(journal["turnInDestination"], f"quest {quest_id}.turnInDestination")
            quest["_stages"], quest["_objectives"] = stages, objectives

    def _validate_destination(self, destination, context):
        if not isinstance(destination, Mapping):
            raise QuestJournalError(f"{context} must be an object")
        precision = destination.get("precision")
        if precision not in _PRECISIONS:
            raise QuestJournalError(f"{context}: invalid precision")
        region_id = destination.get("regionId")
        if region_id not in self.regions:
            raise QuestJournalError(f"{context}: missing region")
        location_id = destination.get("locationId")
        if location_id is not None:
            if location_id not in self.locations or self.locations[location_id]["regionId"] != region_id:
                raise QuestJournalError(f"{context}: missing or mismatched location")
        if precision == "exact" and location_id is None:
            raise QuestJournalError(f"{context}: exact guidance requires a location")
        areas = destination.get("searchAreas", [])
        if precision == "approximate" and not areas:
            raise QuestJournalError(f"{context}: approximate guidance requires search areas")
        for area in areas:
            if not isinstance(area, Mapping) or not all(
                isinstance(area.get(key), (int, float)) and not isinstance(area.get(key), bool)
                for key in ("x", "y", "radius")
            ) or area["radius"] <= 0:
                raise QuestJournalError(f"{context}: invalid bounded search area")
        for clue_id in destination.get("requiredClueIds", []):
            _stable_id(clue_id, f"{context}.requiredClueIds")

    def validate_state(self, state):
        required = {"schemaVersion", "trackedQuestId", "discoveredLocationIds", "discoveredTransitionIds", "clueIds"}
        if not isinstance(state, Mapping) or set(state) != required or state.get("schemaVersion") != STATE_VERSION:
            raise QuestJournalError("journal state schema or fields are invalid")
        result = copy.deepcopy(dict(state))
        tracked = result["trackedQuestId"]
        if tracked is not None and tracked not in self.quests:
            raise QuestJournalError("tracked quest is missing")
        for field, known in (("discoveredLocationIds", self.locations), ("discoveredTransitionIds", self.transitions)):
            values = result[field]
            if not isinstance(values, list) or len(values) != len(set(values)) or any(x not in known for x in values):
                raise QuestJournalError(f"invalid {field}")
            values.sort()
        clues = result["clueIds"]
        if not isinstance(clues, list) or len(clues) != len(set(clues)):
            raise QuestJournalError("invalid clueIds")
        for clue_id in clues:
            _stable_id(clue_id, "clueIds")
        clues.sort()
        return result

    def snapshot(self):
        return copy.deepcopy(self.state)

    def restore(self, state):
        candidate = self.validate_state(state)
        self.state = candidate

    def discover_location(self, location_id):
        if location_id not in self.locations:
            raise QuestJournalError("unknown location")
        if location_id not in self.state["discoveredLocationIds"]:
            self.state["discoveredLocationIds"].append(location_id)
            self.state["discoveredLocationIds"].sort()

    def discover_transition(self, transition_id):
        if transition_id not in self.transitions:
            raise QuestJournalError("unknown transition")
        if transition_id not in self.state["discoveredTransitionIds"]:
            self.state["discoveredTransitionIds"].append(transition_id)
            self.state["discoveredTransitionIds"].sort()

    def learn_clue(self, clue_id):
        _stable_id(clue_id, "clueId")
        if clue_id not in self.state["clueIds"]:
            self.state["clueIds"].append(clue_id)
            self.state["clueIds"].sort()

    def track(self, quest_id, quest_state, *, physical_region_id):
        view = self._entry(quest_id, quest_state, physical_region_id)
        if not view["actions"]["track"]:
            raise QuestJournalError("quest has no useful known guidance")
        self.state["trackedQuestId"] = quest_id
        return copy.deepcopy(view["guidance"])

    def clear_tracking(self):
        self.state["trackedQuestId"] = None

    def show_on_map(self, quest_id, quest_state, *, physical_region_id, campaign_map):
        """Focus the map from derived guidance without changing quest or travel state."""
        view = self._entry(quest_id, quest_state, physical_region_id)
        if not view["actions"]["showOnMap"]:
            raise QuestJournalError("quest has no useful known guidance")
        return campaign_map.focus_guidance(view["guidance"])

    def reconstruct(self, quest_snapshot, *, physical_region_id, command_region_id=None):
        """Build an entirely derived UI model; command region never affects routes."""
        if physical_region_id not in self.regions:
            raise QuestJournalError("physical region is missing")
        runtime_states = _index(quest_snapshot.get("quests", []), "quest state")
        if set(runtime_states) != set(self.quests):
            raise QuestJournalError("quest state is incompatible with journal definitions")
        groups = {group: [] for group in _GROUP_ORDER}
        by_id = {}
        for quest_id in sorted(self.quests, key=lambda ident: (self.quests[ident].get("title", ident).casefold(), ident)):
            state = runtime_states[quest_id]
            if state.get("status") == "inactive":
                continue
            entry = self._entry(quest_id, state, physical_region_id)
            groups[entry["group"]].append(entry)
            by_id[quest_id] = entry
        tracked = self.state["trackedQuestId"]
        if tracked not in by_id or not by_id[tracked]["actions"]["track"]:
            tracked = None
        return {
            "groups": [{"id": group, "quests": groups[group]} for group in _GROUP_ORDER],
            "trackedQuestId": tracked,
            "trackedGuidance": copy.deepcopy(by_id[tracked]["guidance"]) if tracked else None,
            "physicalRegionId": physical_region_id,
            "commandRegionId": command_region_id,
        }

    def _entry(self, quest_id, state, physical_region_id):
        quest = self.quests.get(quest_id)
        if quest is None:
            raise QuestJournalError("unknown quest")
        status = state.get("status")
        stage = quest["_stages"].get(state.get("stageId")) if status == "active" else None
        completed = set(state.get("completedObjectiveIds", []))
        awaiting = bool(stage and not stage.get("nextStageIds") and set(stage.get("objectiveIds", [])).issubset(completed) and quest.get("journal", {}).get("turnInDestination"))
        group = "awaiting_turn_in" if awaiting else status
        if group not in _GROUP_ORDER:
            group = "cancelled"
        objectives = []
        for objective_id in (stage or {}).get("objectiveIds", []):
            definition = quest["_objectives"][objective_id]
            objectives.append({
                "id": objective_id,
                "description": definition.get("description", objective_id),
                "complete": objective_id in completed,
                "entityRefs": copy.deepcopy(definition.get("entityRefs", [])),
            })
        guidance = None
        if status == "active":
            journal = quest.get("journal", {})
            if awaiting:
                guidance = self._guidance(journal["turnInDestination"], physical_region_id, "turn_in")
            else:
                for objective_id in (stage or {}).get("objectiveIds", []):
                    if objective_id not in completed and objective_id in journal.get("destinations", {}):
                        candidate = self._guidance(journal["destinations"][objective_id], physical_region_id, "objective")
                        if candidate is not None:
                            guidance = candidate
                            break
        useful = guidance is not None and guidance["precision"] != "hidden"
        journal = quest.get("journal", {})
        return {
            "id": quest_id,
            "title": quest.get("title", quest_id),
            "summary": quest.get("summary", ""),
            "status": status,
            "group": group,
            "stageId": state.get("stageId"),
            "giver": copy.deepcopy(journal.get("giver")),
            "turnIn": copy.deepcopy(journal.get("turnIn")),
            "objectives": objectives,
            "guidance": guidance,
            "actions": {"track": useful, "showOnMap": useful},
        }

    def _guidance(self, destination, physical_region_id, purpose):
        if not set(destination.get("requiredClueIds", [])).issubset(self.state["clueIds"]):
            return None
        precision = destination["precision"]
        location_id = destination.get("locationId")
        # Explicit discovery of the point itself upgrades broad/hidden clues. Region
        # exploration is deliberately not consulted and cannot reveal hidden POIs.
        if location_id in self.state["discoveredLocationIds"]:
            precision = "exact"
        result = {
            "purpose": purpose,
            "precision": precision,
            "regionId": destination["regionId"],
            "settlementId": destination.get("settlementId"),
            "locationId": location_id if precision == "exact" else None,
            "marker": copy.deepcopy(self.locations[location_id]["position"]) if precision == "exact" else None,
            "searchAreas": copy.deepcopy(destination.get("searchAreas", [])) if precision == "approximate" else [],
            "breadcrumbs": self._breadcrumbs(physical_region_id, destination["regionId"]),
        }
        return result

    def _breadcrumbs(self, source, target):
        if source == target:
            return [{"regionId": source, "transitionId": None}]
        adjacency = {region_id: [] for region_id in self.regions}
        known = set(self.state["discoveredTransitionIds"])
        for transition_id in sorted(known):
            transition = self.transitions[transition_id]
            first, second = transition["from"]["regionId"], transition["to"]["regionId"]
            adjacency[first].append((second, transition_id))
            if not transition.get("directed", False):
                adjacency[second].append((first, transition_id))
        queue = [(0, (), source, [])]
        visited = set()
        while queue:
            distance, ordering, region_id, path = heapq.heappop(queue)
            if region_id in visited:
                continue
            visited.add(region_id)
            if region_id == target:
                result = [{"regionId": source, "transitionId": None}]
                for next_region, transition_id in path:
                    result.append({"regionId": next_region, "transitionId": transition_id})
                return result
            for next_region, transition_id in sorted(adjacency[region_id], key=lambda item: (item[1], item[0])):
                if next_region not in visited:
                    heapq.heappush(queue, (distance + 1, ordering + (transition_id, next_region), next_region, path + [(next_region, transition_id)]))
        return []


class QuestJournalSaveAdapter:
    def __init__(self, journal):
        self.journal = journal

    def capture_world(self, world_state):
        result = copy.deepcopy(dict(world_state))
        result[QUEST_JOURNAL_WORLD_STATE_KEY] = self.journal.snapshot()
        return result

    def migrate_legacy_world(self, world_state):
        result = copy.deepcopy(dict(world_state))
        result.setdefault(QUEST_JOURNAL_WORLD_STATE_KEY, self.journal.snapshot())
        return result

    def reconstruct(self, world_state):
        if QUEST_JOURNAL_WORLD_STATE_KEY not in world_state:
            raise QuestJournalError(f"world state is missing {QUEST_JOURNAL_WORLD_STATE_KEY}")
        return self.journal.validate_state(world_state[QUEST_JOURNAL_WORLD_STATE_KEY])

    def activate(self, reconstructed):
        self.journal.restore(reconstructed)


class QuestJournalScreen:
    """Owns the journal modal pause token independently of disposable UI frames."""

    def __init__(self, journal, pause_controller):
        self.journal = journal
        self.pause_controller = pause_controller
        self._pause_owner = None
        self.model = None

    def open(self, quest_snapshot, *, physical_region_id, command_region_id=None):
        if self._pause_owner is None:
            self._pause_owner = self.pause_controller.open_modal_management_screen()
        self.model = self.journal.reconstruct(
            quest_snapshot,
            physical_region_id=physical_region_id,
            command_region_id=command_region_id,
        )
        return copy.deepcopy(self.model)

    def recover_ui(self, quest_snapshot, *, physical_region_id, command_region_id=None):
        """Rebuild lost frames without acquiring a second modal pause owner."""
        if self._pause_owner is None:
            raise QuestJournalError("journal screen is not open")
        return self.open(
            quest_snapshot,
            physical_region_id=physical_region_id,
            command_region_id=command_region_id,
        )

    def close(self):
        if self._pause_owner is not None:
            self._pause_owner.close()
            self._pause_owner = None
        self.model = None
