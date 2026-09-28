"""Legal, atomic settlement capture and deterministic Warcraft reconstruction.

The coordinator is deliberately scenario-neutral.  Scenario data is passed verbatim to
the Warcraft adapter; object handles and invulnerability state never enter a save.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any, Mapping, Protocol


CAPTURE_STATE_SCHEMA_VERSION = 1
CAPTURE_WORLD_STATE_KEY = "cityCaptureState"
POST_CAPTURE_COOLDOWN_SECONDS = 5.0
CAPTURE_EVENT_CONSUMERS = ("province", "settlement", "economy", "quest", "ui")


class CityCaptureError(ValueError):
    pass


class CityCaptureAdapter(Protocol):
    """Warcraft boundary.  ``stage`` must not remove the current representation."""

    def stage(self, settlement_id: str, controller_polity_id: str,
              specification: Mapping[str, Any], protection_source: str) -> Any: ...
    def commit(self, settlement_id: str, staged: Any) -> Any: ...
    def rollback(self, staged: Any) -> None: ...
    def remove_protection(self, representation: Any, protection_source: str) -> None: ...


class RecordingCityCaptureAdapter:
    """Deterministic headless model of the Warcraft object adapter."""

    def __init__(self):
        self.operations: list[tuple[Any, ...]] = []
        self.current: dict[str, dict[str, Any]] = {}
        self._serial = 0
        self.fail_stage = False
        self.fail_commit = False

    def stage(self, settlement_id, controller_polity_id, specification, protection_source):
        if self.fail_stage:
            raise RuntimeError("injected reconstruction failure")
        self._serial += 1
        staged = {"handle": f"city_{self._serial}", "settlementId": settlement_id,
                  "controllerPolityId": controller_polity_id,
                  "specification": copy.deepcopy(dict(specification)),
                  "protectionSources": {protection_source}}
        self.operations.append(("stage", settlement_id, controller_polity_id,
                                copy.deepcopy(dict(specification)), staged["handle"]))
        return staged

    def commit(self, settlement_id, staged):
        if self.fail_commit:
            raise RuntimeError("injected adapter commit failure")
        old = self.current.get(settlement_id)
        self.current[settlement_id] = staged
        self.operations.append(("commit", settlement_id, staged["handle"],
                                old["handle"] if old else None))
        return staged

    def rollback(self, staged):
        self.operations.append(("rollback", staged["handle"]))

    def remove_protection(self, representation, protection_source):
        representation["protectionSources"].discard(protection_source)
        self.operations.append(("remove_protection", representation["handle"], protection_source))

    def add_protection(self, settlement_id, source):
        self.current[settlement_id]["protectionSources"].add(source)


@dataclass(frozen=True)
class CityCaptureEvent:
    sequence: int
    kind: str
    settlement_id: str
    province_id: str
    previous_controller_polity_id: str
    controller_polity_id: str
    conflict_id: str | None
    at_seconds: float

    def to_dict(self):
        return {"sequence": self.sequence, "kind": self.kind,
                "settlementId": self.settlement_id, "provinceId": self.province_id,
                "previousControllerPolityId": self.previous_controller_polity_id,
                "controllerPolityId": self.controller_polity_id,
                "conflictId": self.conflict_id, "atSeconds": self.at_seconds,
                "consumers": list(CAPTURE_EVENT_CONSUMERS)}


class CityCaptureRuntime:
    """Resolve adapter destruction notifications against stable settlement IDs."""

    def __init__(self, settlements, provinces, diplomacy, adapter: CityCaptureAdapter):
        self.settlements, self.provinces, self.diplomacy = settlements, provinces, diplomacy
        self.adapter = adapter
        self._representations: dict[str, Any] = {}
        self._generation = {sid: 0 for sid in settlements.ids()}
        self._cooldown_until: dict[str, float] = {}
        self._events: list[CityCaptureEvent] = []
        self._next_sequence = 1

    @property
    def events(self):
        return tuple(self._events)

    def _specification(self, settlement_id):
        # The settlement runtime owns the validated, scenario-defined core, layout,
        # templates and placements.  A deep copy prevents adapter mutation.
        return self.settlements.representation_specification(settlement_id)

    @staticmethod
    def _protection_source(settlement_id, generation):
        return f"city_capture:{settlement_id}:{generation}"

    def representation_token(self, settlement_id):
        self.settlements.require(settlement_id)
        return (settlement_id, self._generation[settlement_id])

    def reconstruct(self, settlement_id, now_seconds=0.0):
        """Recover a missing core/defense without changing authoritative state."""
        view = self.settlements.require(settlement_id)
        generation = self._generation[settlement_id]
        if settlement_id in self._representations:
            generation += 1
        source = self._protection_source(settlement_id, generation)
        staged = self.adapter.stage(settlement_id, view.controller_polity_id,
                                    self._specification(settlement_id), source)
        try:
            representation = self.adapter.commit(settlement_id, staged)
        except Exception:
            self.adapter.rollback(staged)
            raise
        self._representations[settlement_id] = representation
        self._generation[settlement_id] = generation
        if self._cooldown_until.get(settlement_id, 0.0) <= float(now_seconds):
            self.adapter.remove_protection(representation, source)
        return self.representation_token(settlement_id)

    def notify_object_loss(self, settlement_id, generation, object_kind, *,
                           attacker_polity_id=None, now_seconds=0.0):
        """The only entry point intended for Warcraft destruction callbacks."""
        if object_kind not in ("city_core", "defense"):
            raise CityCaptureError(f"unknown settlement object kind {object_kind!r}")
        self.settlements.require(settlement_id)
        if generation != self._generation[settlement_id]:
            return None                         # stale/duplicate Warcraft event
        if object_kind == "defense" or attacker_polity_id is None:
            return self.reconstruct(settlement_id, now_seconds)
        return self.capture(settlement_id, attacker_polity_id, now_seconds)

    def _legal_conflict(self, attacker, defender):
        if attacker == defender:
            return None
        matches = []
        for event in self.diplomacy.snapshot().get("conflicts", ()):
            sides = event.get("sides", {})
            if event.get("status") == "active" and (
                (attacker in sides.get("attacker", ()) and defender in sides.get("defender", ())) or
                (attacker in sides.get("defender", ()) and defender in sides.get("attacker", ()))
            ):
                matches.append(event["id"])
        return sorted(matches)[0] if matches else None

    def capture(self, settlement_id, attacker_polity_id, now_seconds):
        now = float(now_seconds)
        view = self.settlements.require(settlement_id)
        if not view.capturable:
            raise CityCaptureError("settlement is not capturable")
        if now < self._cooldown_until.get(settlement_id, 0.0):
            raise CityCaptureError("settlement capture cooldown is active")
        conflict_id = self._legal_conflict(attacker_polity_id, view.controller_polity_id)
        if conflict_id is None:
            raise CityCaptureError("capture requires opposing participants in an active conflict")
        province = self.provinces.require(view.province_id)
        generation = self._generation[settlement_id] + 1
        source = self._protection_source(settlement_id, generation)
        staged = self.adapter.stage(settlement_id, attacker_polity_id,
                                    self._specification(settlement_id), source)
        settlement_before = self.settlements.snapshot()
        province_before = self.provinces.snapshot()
        try:
            # Existing authoritative transition APIs retain legal ownership.
            self.settlements.update(settlement_id, controllerPolityId=attacker_polity_id)
            if province.controller_polity_id != attacker_polity_id:
                self.provinces.transition(view.province_id,
                    controller_polity_id=attacker_polity_id, reason="city_capture")
            representation = self.adapter.commit(settlement_id, staged)
        except Exception:
            self.settlements.restore(settlement_before, reconstruct=False)
            self.provinces.restore(province_before)
            self.adapter.rollback(staged)
            raise
        self._representations[settlement_id] = representation
        self._generation[settlement_id] = generation
        self._cooldown_until[settlement_id] = now + POST_CAPTURE_COOLDOWN_SECONDS
        event = CityCaptureEvent(self._next_sequence, "city_captured", settlement_id,
            view.province_id, view.controller_polity_id, attacker_polity_id, conflict_id, now)
        self._events.append(event); self._next_sequence += 1
        return event

    def advance(self, now_seconds):
        now = float(now_seconds)
        for settlement_id in sorted(tuple(self._cooldown_until)):
            if now < self._cooldown_until[settlement_id]:
                continue
            source = self._protection_source(settlement_id, self._generation[settlement_id])
            representation = self._representations.get(settlement_id)
            if representation is not None:
                self.adapter.remove_protection(representation, source)
            del self._cooldown_until[settlement_id]

    def snapshot(self):
        return {"schemaVersion": CAPTURE_STATE_SCHEMA_VERSION,
                "nextEventSequence": self._next_sequence,
                "generations": [{"settlementId": sid, "generation": self._generation[sid]}
                                for sid in self.settlements.ids()],
                "cooldowns": [{"settlementId": sid, "untilSeconds": until}
                              for sid, until in sorted(self._cooldown_until.items())],
                "events": [event.to_dict() for event in self._events]}

    def validate_snapshot(self, candidate):
        if not isinstance(candidate, Mapping) or candidate.get("schemaVersion") != 1:
            raise CityCaptureError("city capture state schemaVersion must be 1")
        if set(candidate) != {"schemaVersion", "nextEventSequence", "generations", "cooldowns", "events"}:
            raise CityCaptureError("city capture state contains unexpected or missing fields")
        generations = candidate["generations"]; cooldowns = candidate["cooldowns"]; events = candidate["events"]
        if not all(isinstance(x, list) for x in (generations, cooldowns, events)):
            raise CityCaptureError("city capture state collections must be arrays")
        parsed_generations = {}
        for item in generations:
            sid, value = item.get("settlementId"), item.get("generation")
            if sid in parsed_generations or self.settlements.lookup(sid) is None or isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise CityCaptureError("invalid city capture generation")
            parsed_generations[sid] = value
        if set(parsed_generations) != set(self.settlements.ids()):
            raise CityCaptureError("city capture generations do not match settlements")
        parsed_cooldowns = {}
        for item in cooldowns:
            sid, until = item.get("settlementId"), item.get("untilSeconds")
            if sid in parsed_cooldowns or sid not in parsed_generations or isinstance(until, bool) or not isinstance(until, (int, float)):
                raise CityCaptureError("invalid city capture cooldown")
            parsed_cooldowns[sid] = float(until)
        parsed_events = []
        for sequence, item in enumerate(events, 1):
            if item.get("sequence") != sequence or tuple(item.get("consumers", ())) != CAPTURE_EVENT_CONSUMERS:
                raise CityCaptureError("invalid deterministic capture event ordering")
            parsed_events.append(CityCaptureEvent(sequence, item.get("kind"), item.get("settlementId"),
                item.get("provinceId"), item.get("previousControllerPolityId"), item.get("controllerPolityId"),
                item.get("conflictId"), float(item.get("atSeconds"))))
        if candidate["nextEventSequence"] != len(parsed_events) + 1:
            raise CityCaptureError("invalid next capture event sequence")
        return parsed_generations, parsed_cooldowns, parsed_events

    def restore(self, candidate, now_seconds=0.0):
        generations, cooldowns, events = self.validate_snapshot(candidate)
        staged = {}
        try:
            for sid in self.settlements.ids():
                source = self._protection_source(sid, generations[sid])
                staged[sid] = self.adapter.stage(sid, self.settlements.require(sid).controller_polity_id,
                                                 self._specification(sid), source)
        except Exception:
            for sid in sorted(staged): self.adapter.rollback(staged[sid])
            raise
        rebuilt = {}
        try:
            for sid in self.settlements.ids(): rebuilt[sid] = self.adapter.commit(sid, staged[sid])
        except Exception:
            for sid in sorted(staged): self.adapter.rollback(staged[sid])
            raise
        self._generation, self._cooldown_until, self._events = generations, cooldowns, events
        self._next_sequence = len(events) + 1
        self._representations = rebuilt
        # Only pending cooldowns own immunity after loading. Removing our source by identity preserves unrelated protection.
        for sid in self.settlements.ids():
            if sid not in self._cooldown_until:
                self.adapter.remove_protection(rebuilt[sid], self._protection_source(sid, self._generation[sid]))
        self.advance(now_seconds)


class CityCaptureSaveAdapter:
    def __init__(self, runtime, world_state):
        self.runtime, self.world_state = runtime, copy.deepcopy(dict(world_state))

    def capture_world(self):
        result = copy.deepcopy(self.world_state); result[CAPTURE_WORLD_STATE_KEY] = self.runtime.snapshot(); return result

    def migrate_legacy_world(self, candidate):
        result = copy.deepcopy(dict(candidate)); result.setdefault(CAPTURE_WORLD_STATE_KEY, self.runtime.snapshot()); self.validate_world(result); return result

    def validate_world(self, candidate):
        if not isinstance(candidate, Mapping) or CAPTURE_WORLD_STATE_KEY not in candidate:
            raise CityCaptureError("world state is missing cityCaptureState")
        self.runtime.validate_snapshot(candidate[CAPTURE_WORLD_STATE_KEY])

    def reconstruct(self, candidate):
        self.validate_world(candidate); return copy.deepcopy(candidate[CAPTURE_WORLD_STATE_KEY])

    def activate(self, candidate, reconstructed, now_seconds=0.0):
        if reconstructed != candidate[CAPTURE_WORLD_STATE_KEY]:
            raise CityCaptureError("reconstructed city capture state mismatch")
        self.runtime.restore(reconstructed, now_seconds); self.world_state = copy.deepcopy(dict(candidate))
