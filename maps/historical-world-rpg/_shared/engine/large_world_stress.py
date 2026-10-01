"""Synthetic full-world strategic simulation and Phase 5 stress measurement.

Fixtures deliberately contain no historical scenario content.  Stable IDs and
integer arithmetic make generation, uninterrupted runs, and resumed runs exact.
"""
from __future__ import annotations

import copy
import hashlib
import json
import re
import time
from dataclasses import dataclass
from typing import Mapping

import performance_benchmark as benchmark

FORMAT = "warcraftmap_large_world_stress_v1"
CHECKPOINT_FORMAT = "warcraftmap_large_world_checkpoint_v1"
SUMMARY_FORMAT = "warcraftmap_large_world_summary_v1"
ENTITY_KINDS = ("polities", "provinces", "settlements", "markets", "obligations",
                "armies", "fleets", "characters", "relationships", "technologies",
                "institutions", "diplomacy", "wars", "quests", "events", "locations")
METRICS = ("simulation_step_ms", "long_jump_ms", "save_ms", "load_ms",
           "serialized_state_bytes", "state_growth_bytes", "active_warcraft_objects")
_ID = re.compile(r"^[a-z][a-z0-9_]*$")


class StressError(ValueError):
    pass


class InvariantFailure(RuntimeError):
    def __init__(self, invariant, entity_id, message):
        self.diagnostic = {"invariant": invariant, "entityId": entity_id, "message": message}
        super().__init__(f"{invariant}:{entity_id}: {message}")


@dataclass(frozen=True)
class StressProfile:
    id: str
    seed: int
    counts: Mapping[str, int]
    duration: int
    step_size: int
    checkpoint_at: int
    active_region: str
    representation_limit: int
    scheduled_per_step: int
    budgets: Mapping[str, float]


def _ident(kind, index):
    return f"{kind}_{index:06d}"


def _require_int(value, context, minimum=1):
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise StressError(f"{context}: expected integer >= {minimum}")
    return value


def load_profiles(path):
    data = benchmark.load_json(path)
    if data.get("format") != FORMAT:
        raise StressError("unsupported large-world stress configuration")
    profiles = {}
    for profile_id, raw in data.get("profiles", {}).items():
        counts = raw.get("counts", {})
        if set(counts) != set(ENTITY_KINDS):
            raise StressError(f"{profile_id}.counts: must specify every entity kind")
        for kind, count in counts.items():
            _require_int(count, f"{profile_id}.counts.{kind}")
        budgets = raw.get("budgets", {})
        if set(budgets) != set(METRICS) or any(isinstance(x, bool) or not isinstance(x, (int, float)) or x <= 0 for x in budgets.values()):
            raise StressError(f"{profile_id}.budgets: invalid metric budgets")
        profile = StressProfile(
            profile_id, _require_int(raw.get("seed"), f"{profile_id}.seed", 0), counts,
            _require_int(raw.get("duration"), f"{profile_id}.duration"),
            _require_int(raw.get("stepSize"), f"{profile_id}.stepSize"),
            _require_int(raw.get("checkpointAt"), f"{profile_id}.checkpointAt"),
            raw.get("activeRegion"), _require_int(raw.get("representationLimit"), f"{profile_id}.representationLimit"),
            _require_int(raw.get("scheduledPerStep"), f"{profile_id}.scheduledPerStep"),
            {key: float(value) for key, value in budgets.items()},
        )
        if profile.duration % profile.step_size or profile.checkpoint_at % profile.step_size or not 0 < profile.checkpoint_at < profile.duration:
            raise StressError(f"{profile_id}: duration and checkpoint must align to stepSize")
        profiles[profile_id] = profile
    if not profiles:
        raise StressError("at least one stress profile is required")
    return data, profiles


def generate_fixture(profile):
    """Generate a deterministic, scenario-neutral, cross-linked strategic world."""
    c, seed = profile.counts, profile.seed
    regions = max(2, min(c["locations"], max(2, c["provinces"] // 4)))
    region_ids = [_ident("region", i) for i in range(regions)]
    records = {kind: [] for kind in ENTITY_KINDS}
    for i in range(c["polities"]):
        records["polities"].append({"id": _ident("polity", i), "treasury": 100000 + (seed + i * 7919) % 100000})
    for i in range(c["provinces"]):
        records["provinces"].append({"id": _ident("province", i), "ownerId": _ident("polity", i % c["polities"]), "controllerId": _ident("polity", i % c["polities"]), "regionId": region_ids[i % regions], "parentProvinceId": None})
    for i in range(c["settlements"]):
        records["settlements"].append({"id": _ident("settlement", i), "provinceId": _ident("province", i % c["provinces"]), "ownerId": _ident("polity", i % c["polities"]), "stock": 1000})
    for i in range(c["markets"]):
        records["markets"].append({"id": _ident("market", i), "settlementId": _ident("settlement", i % c["settlements"]), "stock": 500, "currency": 500})
    for i in range(c["obligations"]):
        payer = i % c["markets"]
        records["obligations"].append({"id": _ident("obligation", i), "payerMarketId": _ident("market", payer), "payeeMarketId": _ident("market", (payer + 1) % c["markets"]), "amount": 1 + i % 5, "interval": 4, "nextDue": 4})
    for kind in ("armies", "fleets"):
        for i in range(c[kind]):
            records[kind].append({"id": _ident("army" if kind == "armies" else "fleet", i), "ownerId": _ident("polity", i % c["polities"]), "locationId": _ident("location", i % c["locations"]), "strength": 100 + i % 100, "regionId": region_ids[i % regions]})
    for i in range(c["characters"]):
        records["characters"].append({"id": _ident("character", i), "polityId": _ident("polity", i % c["polities"]), "locationId": _ident("location", i % c["locations"]), "loyalty": (seed + i * 17) % 201 - 100, "regionId": region_ids[i % regions]})
    for i in range(c["relationships"]):
        records["relationships"].append({"id": _ident("relationship", i), "fromId": _ident("character", i % c["characters"]), "toId": _ident("character", (i * 31 + 1) % c["characters"]), "score": (seed + i * 13) % 201 - 100})
    for kind in ("technologies", "institutions"):
        prefix = "technology" if kind == "technologies" else "institution"
        for i in range(c[kind]):
            records[kind].append({"id": _ident(prefix, i), "prerequisiteId": None if i == 0 else _ident(prefix, i - 1), "progress": 0})
    for i in range(c["diplomacy"]):
        records["diplomacy"].append({"id": _ident("diplomacy", i), "firstPolityId": _ident("polity", i % c["polities"]), "secondPolityId": _ident("polity", (i + 1) % c["polities"]), "opinion": 0})
    for i in range(c["wars"]):
        records["wars"].append({"id": _ident("war", i), "attackerId": _ident("polity", i % c["polities"]), "defenderId": _ident("polity", (i + 1) % c["polities"]), "score": 0})
    for kind in ("quests", "events"):
        prefix = "quest" if kind == "quests" else "event"
        for i in range(c[kind]):
            records[kind].append({"id": _ident(prefix, i), "locationId": _ident("location", i % c["locations"]), "due": 1 + i % max(1, profile.duration), "occurrences": 0})
    for i in range(c["locations"]):
        records["locations"].append({"id": _ident("location", i), "regionId": region_ids[i % regions], "parentLocationId": None})
    scheduled = []
    for i in range(profile.duration // profile.step_size * profile.scheduled_per_step):
        scheduled.append({"id": _ident("scheduled", i), "due": (i // profile.scheduled_per_step + 1) * profile.step_size, "kind": ("economy", "military", "event")[i % 3], "targetId": _ident("polity", i % c["polities"]), "processed": False})
    traditions = [{"controllerId": _ident("polity", i), "categoryId": category, "experience": 0}
                  for i in range(c["polities"]) for category in ("land", "naval")]
    fixture = {"format": FORMAT, "seed": seed, "time": 0, "regions": region_ids, "activeRegionId": profile.active_region if profile.active_region in region_ids else region_ids[0], "entities": records, "traditionTracks": traditions, "scheduledWork": scheduled, "processedWork": 0}
    validate_fixture(fixture)
    return fixture


def _indexes(fixture):
    result = {}
    for kind in ENTITY_KINDS:
        values = fixture["entities"].get(kind)
        if not isinstance(values, list):
            raise InvariantFailure("collection", kind, "entity collection must be an array")
        index = {}
        for value in values:
            ident = value.get("id") if isinstance(value, dict) else None
            if not isinstance(ident, str) or not _ID.fullmatch(ident):
                raise InvariantFailure("stable_id", str(ident), "invalid stable ID")
            if ident in index:
                raise InvariantFailure("stable_id", ident, "duplicate stable ID")
            index[ident] = value
        result[kind] = index
    return result


def validate_fixture(fixture):
    """Validate references, hierarchy, ownership/control and conservation."""
    benchmark.validate_snapshot(fixture)
    idx = _indexes(fixture)
    tracks = fixture.get("traditionTracks")
    if not isinstance(tracks, list) or len(tracks) != 2 * len(idx["polities"]):
        raise InvariantFailure("tradition", "tracks", "controller/category coverage differs")
    keys = set()
    for track in tracks:
        key = (track.get("controllerId"), track.get("categoryId"))
        if key[0] not in idx["polities"] or key[1] not in {"land", "naval"} or key in keys or not isinstance(track.get("experience"), int) or track["experience"] < 0:
            raise InvariantFailure("tradition", str(key), "invalid controller/category experience")
        keys.add(key)
    references = (
        ("provinces", "ownerId", "polities"), ("provinces", "controllerId", "polities"),
        ("settlements", "provinceId", "provinces"), ("settlements", "ownerId", "polities"),
        ("markets", "settlementId", "settlements"), ("obligations", "payerMarketId", "markets"),
        ("obligations", "payeeMarketId", "markets"), ("armies", "ownerId", "polities"),
        ("fleets", "ownerId", "polities"), ("characters", "polityId", "polities"),
        ("relationships", "fromId", "characters"), ("relationships", "toId", "characters"),
        ("diplomacy", "firstPolityId", "polities"), ("diplomacy", "secondPolityId", "polities"),
        ("wars", "attackerId", "polities"), ("wars", "defenderId", "polities"),
        ("quests", "locationId", "locations"), ("events", "locationId", "locations"),
    )
    for source, field, target in references:
        for entity in fixture["entities"][source]:
            if entity.get(field) not in idx[target]:
                raise InvariantFailure("reference", entity["id"], f"{field} missing stable ID {entity.get(field)!r}")
    regions = set(fixture.get("regions", []))
    if fixture.get("activeRegionId") not in regions:
        raise InvariantFailure("reference", str(fixture.get("activeRegionId")), "active region does not exist")
    for kind in ("provinces", "armies", "fleets", "characters", "locations"):
        for entity in fixture["entities"][kind]:
            if entity["regionId"] not in regions:
                raise InvariantFailure("reference", entity["id"], "region does not exist")
    for kind, prefix in (("technologies", "technology"), ("institutions", "institution")):
        for i, entity in enumerate(fixture["entities"][kind]):
            expected = None if i == 0 else _ident(prefix, i - 1)
            if entity["prerequisiteId"] != expected:
                raise InvariantFailure("hierarchy", entity["id"], "research prerequisites must be acyclic ordered chains")
    for work in fixture["scheduledWork"]:
        if work["targetId"] not in idx["polities"] or work["due"] <= 0:
            raise InvariantFailure("scheduling", work["id"], "invalid scheduled work")
        if work["processed"] and work["due"] > fixture["time"]:
            raise InvariantFailure("scheduling", work["id"], "future work marked processed")
    total = sum(x["stock"] for x in fixture["entities"]["markets"])
    expected_total = 500 * len(fixture["entities"]["markets"])
    if total != expected_total:
        raise InvariantFailure("conservation", "markets", f"stock total {total} != {expected_total}")
    return idx


def active_representations(fixture, limit):
    """Return bounded descriptors only for the active region; never WC3 handles."""
    active = fixture["activeRegionId"]
    candidates = []
    for kind in ("settlements", "armies", "fleets", "characters"):
        for entity in fixture["entities"][kind]:
            region = entity.get("regionId")
            if kind == "settlements":
                # Settlement region is authoritative through its province.
                province = fixture["entities"]["provinces"][int(entity["provinceId"].rsplit("_", 1)[1])]
                region = province["regionId"]
            if region == active:
                candidates.append({"entityId": entity["id"], "kind": kind[:-1]})
    return sorted(candidates, key=lambda x: x["entityId"])[:limit]


def advance(fixture, target_time, step_size, representation_limit):
    if target_time < fixture["time"] or step_size <= 0:
        raise StressError("invalid simulation interval")
    timings = []
    while fixture["time"] < target_time:
        started = time.perf_counter_ns()
        fixture["time"] = min(target_time, fixture["time"] + step_size)
        due = [x for x in fixture["scheduledWork"] if not x["processed"] and x["due"] <= fixture["time"]]
        for work in due:
            work["processed"] = True
            polity = fixture["entities"]["polities"][int(work["targetId"].rsplit("_", 1)[1])]
            polity["treasury"] += 1
            fixture["processedWork"] += 1
            if work["kind"] == "military":
                ordinal = int(work["id"].rsplit("_", 1)[1])
                category = "land" if ordinal % 2 == 0 else "naval"
                track = next(x for x in fixture["traditionTracks"] if x["controllerId"] == work["targetId"] and x["categoryId"] == category)
                track["experience"] += 1 + ordinal % 7
        for obligation in fixture["entities"]["obligations"]:
            while obligation["nextDue"] <= fixture["time"]:
                payer = fixture["entities"]["markets"][int(obligation["payerMarketId"].rsplit("_", 1)[1])]
                payee = fixture["entities"]["markets"][int(obligation["payeeMarketId"].rsplit("_", 1)[1])]
                amount = min(obligation["amount"], payer["currency"])
                payer["currency"] -= amount
                payee["currency"] += amount
                obligation["nextDue"] += obligation["interval"]
        for kind in ("quests", "events"):
            for entity in fixture["entities"][kind]:
                if entity["due"] <= fixture["time"] and entity["occurrences"] == 0:
                    entity["occurrences"] = 1
        validate_fixture(fixture)
        representations = active_representations(fixture, representation_limit)
        if len(representations) > representation_limit:
            raise InvariantFailure("representation_bound", fixture["activeRegionId"], "active object budget exceeded")
        timings.append((time.perf_counter_ns() - started) / 1e6)
    return timings


def checkpoint(fixture):
    validate_fixture(fixture)
    return {"format": CHECKPOINT_FORMAT, "fixtureHash": fixture_hash(fixture, logical=False), "state": copy.deepcopy(fixture)}


def resume(value):
    if value.get("format") != CHECKPOINT_FORMAT or not isinstance(value.get("state"), dict):
        raise StressError("unsupported stress checkpoint")
    result = copy.deepcopy(value["state"])
    if value.get("fixtureHash") != fixture_hash(result, logical=False):
        raise StressError("stress checkpoint hash mismatch")
    validate_fixture(result)
    return result


def fixture_hash(fixture, logical=True):
    value = copy.deepcopy(fixture)
    if logical:
        value.pop("format", None)
    return hashlib.sha256(benchmark.canonical(value)).hexdigest()


def run_profile(profile, max_diagnostics=3):
    """Run uninterrupted and checkpoint/resumed paths and emit a compact summary."""
    failures = []
    metrics = {name: 0.0 for name in METRICS}
    try:
        original = generate_fixture(profile)
        initial_size = len(benchmark.canonical(original))
        uninterrupted = copy.deepcopy(original)
        step_times = advance(uninterrupted, profile.duration, profile.step_size, profile.representation_limit)
        split = copy.deepcopy(original)
        advance(split, profile.checkpoint_at, profile.step_size, profile.representation_limit)
        save_started = time.perf_counter_ns()
        encoded = benchmark.canonical(checkpoint(split))
        metrics["save_ms"] = (time.perf_counter_ns() - save_started) / 1e6
        load_started = time.perf_counter_ns()
        resumed = resume(json.loads(encoded))
        metrics["load_ms"] = (time.perf_counter_ns() - load_started) / 1e6
        long_started = time.perf_counter_ns()
        resumed_times = advance(resumed, profile.duration, profile.duration - profile.checkpoint_at, profile.representation_limit)
        metrics["long_jump_ms"] = (time.perf_counter_ns() - long_started) / 1e6
        if fixture_hash(uninterrupted) != fixture_hash(resumed):
            raise InvariantFailure("checkpoint_equivalence", "world", "resumed logical state differs from uninterrupted state")
        final_bytes = len(benchmark.canonical(uninterrupted))
        metrics.update(simulation_step_ms=max(step_times or [0]), serialized_state_bytes=float(final_bytes),
                       state_growth_bytes=float(max(0, final_bytes - initial_size)),
                       active_warcraft_objects=float(len(active_representations(uninterrupted, profile.representation_limit))))
        # Keep the long-jump list live for correctness and measurement coverage.
        if not resumed_times:
            raise InvariantFailure("scheduling", "world", "long jump performed no work")
        for metric, observed in metrics.items():
            if observed > profile.budgets[metric]:
                failures.append({"invariant": "budget", "entityId": metric, "message": f"{observed:.3f} exceeds {profile.budgets[metric]:.3f}"})
    except (StressError, benchmark.CorrectnessError, InvariantFailure) as exc:
        failures.append(exc.diagnostic if isinstance(exc, InvariantFailure) else {"invariant": "fixture", "entityId": "world", "message": str(exc)})
    counts = dict(profile.counts)
    return {"format": SUMMARY_FORMAT, "profile": profile.id, "seed": profile.seed,
            "counts": counts, "duration": profile.duration, "metrics": metrics,
            "budgets": dict(profile.budgets), "status": "pass" if not failures else "failure",
            "passed": not failures, "failures": failures[:max(1, max_diagnostics)]}
