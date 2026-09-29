"""Deterministic maximum-reasonable local-battle performance gate.

The scenario-neutral fixture models formations, ships, diplomacy, and supply as
stable authoritative data. Warcraft handles and effects exist only behind the
runtime adapter and are always reconstructible.
"""
from __future__ import annotations

import copy
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Protocol

METRICS = (
    "peak_active_objects", "handles_created", "handles_retired",
    "effects_created", "effects_retired", "orders_issued",
    "pathing_queries", "update_duration_ms", "runtime_proxy_units",
)
STAGES = (
    "setup", "command", "casualties", "morale_supply", "reinforcement",
    "reconciliation", "retirement",
)


class BattleConfigurationError(ValueError):
    pass


class BattleCorrectnessError(RuntimeError):
    pass


@dataclass(frozen=True)
class BattleProfile:
    id: str
    kind: str
    seed: int
    repeats: int
    units: int
    formations: int
    effects: int
    orders: int
    reinforcements: int
    represented_strength_per_unit: int
    budgets: dict[str, float]


class BattleRuntimeAdapter(Protocol):
    """Boundary for patch-specific object, order, pathing, and clock work."""

    def begin_stage(self, stage: str) -> None: ...
    def create_unit(self, entity_id: str, kind: str) -> Any: ...
    def retire_unit(self, handle: Any) -> None: ...
    def create_effect(self, effect_id: str, handle: Any) -> Any: ...
    def retire_effect(self, effect: Any) -> None: ...
    def issue_order(self, handle: Any, order: str, x: float, y: float) -> None: ...
    def pathable(self, kind: str, x: float, y: float) -> bool: ...
    def now_ns(self) -> int: ...
    def live_counts(self) -> tuple[int, int]: ...
    def metrics(self) -> Mapping[str, float]: ...


class RecordingBattleAdapter:
    """Deterministic headless adapter with a runtime-compatible timing proxy."""

    def __init__(self) -> None:
        self.operations: list[tuple[Any, ...]] = []
        self.stage = "unstarted"
        self.serial = self.effect_serial = self.clock = 0
        self.live_units: set[str] = set()
        self.live_effects: set[str] = set()
        self.counts = {metric: 0.0 for metric in METRICS}

    def begin_stage(self, stage: str) -> None:
        self.stage = stage
        self.operations.append(("stage", stage))

    def _tick(self, units: int = 1) -> None:
        self.clock += units * 1_000
        self.counts["runtime_proxy_units"] += units

    def _peak(self) -> None:
        active = len(self.live_units) + len(self.live_effects)
        self.counts["peak_active_objects"] = max(self.counts["peak_active_objects"], active)

    def create_unit(self, entity_id: str, kind: str) -> str:
        self.serial += 1
        handle = f"unit_{self.serial}"
        self.live_units.add(handle)
        self.counts["handles_created"] += 1
        self._tick(4)
        self._peak()
        self.operations.append((self.stage, "create", entity_id, kind, handle))
        return handle

    def retire_unit(self, handle: str) -> None:
        if handle not in self.live_units:
            raise BattleCorrectnessError(f"{self.stage}: retiring unknown unit {handle}")
        self.live_units.remove(handle)
        self.counts["handles_retired"] += 1
        self._tick(2)
        self.operations.append((self.stage, "retire", handle))

    def create_effect(self, effect_id: str, handle: str) -> str:
        if handle not in self.live_units:
            raise BattleCorrectnessError(f"{self.stage}: effect target is not live")
        self.effect_serial += 1
        effect = f"effect_{self.effect_serial}"
        self.live_effects.add(effect)
        self.counts["effects_created"] += 1
        self._tick(2)
        self._peak()
        self.operations.append((self.stage, "effect", effect_id, handle, effect))
        return effect

    def retire_effect(self, effect: str) -> None:
        if effect not in self.live_effects:
            raise BattleCorrectnessError(f"{self.stage}: retiring unknown effect {effect}")
        self.live_effects.remove(effect)
        self.counts["effects_retired"] += 1
        self._tick()
        self.operations.append((self.stage, "retire_effect", effect))

    def issue_order(self, handle: str, order: str, x: float, y: float) -> None:
        if handle not in self.live_units:
            raise BattleCorrectnessError(f"{self.stage}: order for retired unit")
        self.counts["orders_issued"] += 1
        self._tick(2)
        self.operations.append((self.stage, "order", handle, order, x, y))

    def pathable(self, kind: str, x: float, y: float) -> bool:
        self.counts["pathing_queries"] += 1
        self._tick()
        return (int(x) + int(y) + len(kind)) % 17 != 0

    def now_ns(self) -> int:
        self.clock += 1_000
        return self.clock

    def live_counts(self) -> tuple[int, int]:
        return len(self.live_units), len(self.live_effects)

    def metrics(self) -> Mapping[str, float]:
        return copy.deepcopy(self.counts)


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def load_profiles(path: str | Path) -> dict[str, BattleProfile]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if raw.get("format") != "warcraftmap_local_battle_benchmark_v1" or raw.get("fixtureVersion") != 1:
        raise BattleConfigurationError("unsupported local battle benchmark configuration")
    result: dict[str, BattleProfile] = {}
    required = {"units", "formations", "effects", "orders", "reinforcements", "representedStrengthPerUnit"}
    for ident, item in raw.get("profiles", {}).items():
        workload, budgets = item.get("workload", {}), item.get("budgets", {})
        if set(workload) != required or set(budgets) != set(METRICS):
            raise BattleConfigurationError(f"{ident}: incorrect workload or budget fields")
        if item.get("kind") not in {"land", "naval", "mixed"}:
            raise BattleConfigurationError(f"{ident}: invalid battle kind")
        integers = [item.get("seed"), item.get("repeatedRuns"), *workload.values()]
        if any(isinstance(value, bool) or not isinstance(value, int) or value < 1 for value in integers):
            raise BattleConfigurationError(f"{ident}: seed, repeats, and workload values must be positive integers")
        if workload["formations"] > workload["units"] or workload["reinforcements"] >= workload["units"]:
            raise BattleConfigurationError(f"{ident}: invalid formation or reinforcement count")
        if any(isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0 or not math.isfinite(value) for value in budgets.values()):
            raise BattleConfigurationError(f"{ident}: invalid budgets")
        result[ident] = BattleProfile(
            ident, item["kind"], item["seed"], item["repeatedRuns"],
            workload["units"], workload["formations"], workload["effects"],
            workload["orders"], workload["reinforcements"], workload["representedStrengthPerUnit"],
            {key: float(value) for key, value in budgets.items()},
        )
    if set(result) != {"maximum_land", "maximum_naval", "maximum_mixed"}:
        raise BattleConfigurationError("land, naval, and mixed profiles are required")
    return result


def generate_fixture(profile: BattleProfile) -> dict[str, Any]:
    units = []
    for index in range(profile.units):
        kind = "formation" if profile.kind == "land" or (profile.kind == "mixed" and index % 2 == 0) else "ship"
        units.append({
            "id": f"battle_unit_{index:04d}", "kind": kind,
            "side": "attacker" if index % 2 == 0 else "defender",
            "formationId": f"formation_{index % profile.formations:03d}",
            "representedStrength": profile.represented_strength_per_unit + index % 7,
            "morale": 80, "supply": 90, "casualties": 0,
            "active": index >= profile.reinforcements,
        })
    return {
        "format": "warcraftmap_local_battle_fixture_v1", "fixtureVersion": 1,
        "seed": profile.seed, "profile": profile.id,
        "conflict": {"id": "benchmark_conflict", "status": "active"},
        "authoritativeUnits": units,
    }


def run_once(profile: BattleProfile, adapter: BattleRuntimeAdapter) -> dict[str, Any]:
    fixture = generate_fixture(profile)
    state = copy.deepcopy(fixture["authoritativeUnits"])
    handles: dict[str, Any] = {}
    effects: list[Any] = []
    initial_strength = sum(unit["representedStrength"] for unit in state)
    stage_durations: dict[str, float] = {}
    stage_metrics: dict[str, dict[str, float]] = {}

    def stage(name: str, operation: Callable[[], None]) -> None:
        adapter.begin_stage(name)
        before = dict(adapter.metrics())
        start = adapter.now_ns()
        operation()
        duration = (adapter.now_ns() - start) / 1e6
        after = dict(adapter.metrics())
        stage_durations[name] = duration
        stage_metrics[name] = {metric: after[metric] - before[metric] for metric in METRICS if metric not in {"peak_active_objects", "update_duration_ms"}}
        stage_metrics[name]["peak_active_objects"] = after["peak_active_objects"]
        stage_metrics[name]["update_duration_ms"] = duration

    def setup() -> None:
        for unit in state:
            if unit["active"]:
                handles[unit["id"]] = adapter.create_unit(unit["id"], unit["kind"])

    def command() -> None:
        active = [unit for unit in state if unit["active"]]
        for index in range(profile.orders):
            unit = active[index % len(active)]
            x, y = float((profile.seed + index * 37) % 2048), float((profile.seed + index * 53) % 2048)
            adapter.pathable(unit["kind"], x, y)
            adapter.issue_order(handles[unit["id"]], "attack" if index % 3 else "move", x, y)
        for index in range(profile.effects):
            unit = active[index % len(active)]
            effects.append(adapter.create_effect(f"battle_effect_{index}", handles[unit["id"]]))

    def casualties() -> None:
        for index, unit in enumerate(unit for unit in state if unit["active"]):
            loss = 1 + ((profile.seed + index * 13) % max(1, unit["representedStrength"] // 5))
            unit["casualties"] += loss
            unit["representedStrength"] -= loss

    def morale_supply() -> None:
        for unit in state:
            if unit["active"]:
                unit["morale"] = max(0, unit["morale"] - 3 - unit["casualties"] % 5)
                unit["supply"] = max(0, unit["supply"] - 7)

    def reinforce() -> None:
        for unit in state[:profile.reinforcements]:
            unit["active"] = True
            handles[unit["id"]] = adapter.create_unit(unit["id"], unit["kind"])

    def reconcile() -> None:
        active_count = sum(unit["active"] for unit in state)
        strength = sum(unit["representedStrength"] for unit in state)
        if len(handles) != active_count:
            raise BattleCorrectnessError("reconciliation: representation count differs from locally active entities")
        if strength >= initial_strength:
            raise BattleCorrectnessError("reconciliation: casualties did not reduce authoritative strength")
        if strength == len(handles):
            raise BattleCorrectnessError("reconciliation: strategic strength collapsed to object count")

    def retire() -> None:
        for effect in effects:
            adapter.retire_effect(effect)
        for handle in handles.values():
            adapter.retire_unit(handle)

    for name, operation in zip(STAGES, (setup, command, casualties, morale_supply, reinforce, reconcile, retire)):
        stage(name, operation)
    if adapter.live_counts() != (0, 0):
        raise BattleCorrectnessError("retirement: runtime representation leak")
    measured = dict(adapter.metrics())
    measured["update_duration_ms"] = max(stage_durations.values())
    return {
        "profile": profile.id, "fixture": fixture, "authoritativeState": state,
        "stageDurationsMs": stage_durations, "stageMetrics": stage_metrics, "metrics": measured,
        "representedStrength": sum(unit["representedStrength"] for unit in state),
        "spawnedObjectCount": int(measured["handles_created"]),
    }


def run(profile: BattleProfile, adapter_factory: Callable[[], BattleRuntimeAdapter] = RecordingBattleAdapter) -> dict[str, Any]:
    results = []
    try:
        for repeat in range(profile.repeats):
            result = run_once(profile, adapter_factory())
            results.append(result)
            if repeat and canonical(result["authoritativeState"]) != canonical(results[0]["authoritativeState"]):
                raise BattleCorrectnessError("repeated_run: non-deterministic authoritative state")
        measured = {metric: max(float(result["metrics"][metric]) for result in results) for metric in METRICS}
        failures = []
        for metric in METRICS:
            if measured[metric] <= profile.budgets[metric]:
                continue
            stage = max(STAGES, key=lambda name: results[0]["stageMetrics"][name][metric])
            failures.append({
                "kind": "budget", "profile": profile.id, "stage": stage, "metric": metric,
                "observed": measured[metric], "limit": profile.budgets[metric],
                "message": f"{profile.id} {stage}: {metric} measured {measured[metric]:g}, limit {profile.budgets[metric]:g}",
            })
        return {
            "format": "warcraftmap_local_battle_result_v1", "fixtureVersion": 1,
            "profile": profile.id, "passed": not failures,
            "status": "pass" if not failures else "performance_budget_failure",
            "metrics": measured, "budgets": profile.budgets, "failures": failures,
            "runs": profile.repeats, "fixture": results[0]["fixture"],
        }
    except Exception as error:
        return {
            "format": "warcraftmap_local_battle_result_v1", "fixtureVersion": 1,
            "profile": profile.id, "passed": False, "status": "correctness_failure",
            "failures": [{"kind": "correctness", "profile": profile.id, "stage": "unknown", "message": str(error)}],
        }
