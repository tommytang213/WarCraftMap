"""Deterministic, scenario-neutral performance measurement primitives."""
from __future__ import annotations

import json
import math
import statistics
from dataclasses import dataclass
from pathlib import Path

METRICS = ("simulation_step_ms", "save_ms", "load_ms", "serialized_state_bytes",
           "active_warcraft_objects", "visible_operation_hitch_ms")


class ConfigurationError(ValueError):
    pass


class CorrectnessError(RuntimeError):
    pass


@dataclass(frozen=True)
class Profile:
    id: str
    seed: int
    warmups: int
    repeats: int
    workload: dict
    thresholds: dict
    max_cv: float


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def validate_snapshot(value, path="fixture"):
    if isinstance(value, dict):
        for key, child in value.items():
            if not isinstance(key, str) or "handle" in key.lower() or "widget" in key.lower():
                raise CorrectnessError(f"{path}.{key}: transient Warcraft handle or unstable key")
            validate_snapshot(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            validate_snapshot(child, f"{path}[{index}]")
    elif value is not None and not isinstance(value, (str, int, float, bool)):
        raise CorrectnessError(f"{path}: non-JSON value")


def aggregate(samples):
    result = {}
    for metric, values in samples.items():
        mean = statistics.fmean(values)
        result[metric] = {
            "median": statistics.median(values),
            "p95": sorted(values)[math.ceil(.95 * len(values)) - 1],
            "minimum": min(values),
            "maximum": max(values),
            "coefficientOfVariation": statistics.pstdev(values) / mean if mean else 0,
            "sampleCount": len(values),
        }
    return result


def load_json(path):
    return json.loads(Path(path).read_text())
