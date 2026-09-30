"""Deterministic oracle for Warcraft native save/load reconstruction.

This module deliberately models handles separately from authoritative state.  A
developer Warcraft runner emits the same snapshots, allowing its native-load
result to be compared with this headless oracle.
"""

from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass, field


UNSAFE_TRANSACTIONS = ("map_transition", "city_capture", "campaign_commit")


def canonical(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def digest(value: object) -> str:
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def fixture_state() -> dict:
    """Stable IDs and values only; never Warcraft handles."""
    return {
        "schemaVersion": 1,
        "campaign": {"slot": "autosave_07", "payloadDigest": "campaign-fixture-v1"},
        "autosave": {"metadataVersion": 1, "nextSlot": 8, "remainingSeconds": 37.5},
        "physicalMapId": "world-map",
        "modalPause": {"paused": True, "ownerCount": 1, "pausedBeforeModal": False},
        "clock": {"campaignSeconds": 1450.0, "tickSeconds": 1.0},
        "entities": {
            "settlement:lisbon": {"kind": "settlement", "owner": "portugal", "represented": True},
            "fleet:vasco": {"kind": "fleet", "owner": "portugal", "represented": True},
            "official:governor": {"kind": "character", "owner": "portugal", "represented": False},
        },
        "deliveredEvents": ["event:fixture:before-save"],
    }


@dataclass
class Runtime:
    generation: int = 0
    representations: dict[str, str] = field(default_factory=dict)
    timers: dict[str, str] = field(default_factory=dict)
    ui: list[str] = field(default_factory=list)
    effects: list[str] = field(default_factory=list)
    audio: list[str] = field(default_factory=list)
    event_subscriptions: set[str] = field(default_factory=set)


def reconstruct(state: dict, previous: Runtime | None = None) -> Runtime:
    generation = 1 if previous is None else previous.generation + 1
    runtime = Runtime(generation=generation)
    runtime.representations = {
        stable_id: f"unit:g{generation}:{stable_id}"
        for stable_id, entity in state["entities"].items()
        if entity["represented"]
    }
    runtime.timers = {
        "campaign-clock": f"timer:g{generation}:campaign-clock",
        "autosave": f"timer:g{generation}:autosave",
    }
    if state["modalPause"]["ownerCount"]:
        runtime.ui = [f"frame:g{generation}:management-modal"]
    runtime.audio = [f"sound:g{generation}:ambient"]
    runtime.event_subscriptions = {"campaign-tick", "entity-representation-lost"}
    return runtime


def authoritative_projection(state: dict) -> dict:
    return copy.deepcopy(state)


def runtime_index_projection(runtime: Runtime) -> dict:
    return {
        "representedIds": sorted(runtime.representations),
        "timerIds": sorted(runtime.timers),
        "modalFrameCount": len(runtime.ui),
        "eventSubscriptions": sorted(runtime.event_subscriptions),
    }


def run_headless_cycle(loads: int = 2, missing_representation: str | None = None) -> dict:
    state = fixture_state()
    before = authoritative_projection(state)
    runtime = reconstruct(state)
    old_handles: set[str] = set(runtime.representations.values()) | set(runtime.timers.values()) | set(runtime.ui) | set(runtime.audio)
    if missing_representation:
        runtime.representations.pop(missing_representation, None)
    generations = []
    for _ in range(loads):
        runtime = reconstruct(state, runtime)
        generations.append(runtime.generation)
    new_handles = set(runtime.representations.values()) | set(runtime.timers.values()) | set(runtime.ui) | set(runtime.audio)
    after = authoritative_projection(state)
    failures = []
    if before != after:
        failures.append("authoritative state changed across native load")
    if old_handles & new_handles:
        failures.append("transient runtime handles survived reconstruction")
    if set(runtime.representations) != {key for key, value in state["entities"].items() if value["represented"]}:
        failures.append("runtime representation index was not reconstructed")
    if len(runtime.event_subscriptions) != 2:
        failures.append("event subscriptions were duplicated")
    return {
        "fixtureVersion": 1,
        "loads": loads,
        "authoritativeDigestBefore": digest(before),
        "authoritativeDigestAfter": digest(after),
        "authoritativeState": after,
        "runtimeIndex": runtime_index_projection(runtime),
        "runtimeGenerations": generations,
        "transientHandlesRecreated": not bool(old_handles & new_handles),
        "passed": not failures,
        "failures": failures,
    }


def save_decision(transaction: str | None) -> str:
    return "deferred" if transaction in UNSAFE_TRANSACTIONS else "created"
