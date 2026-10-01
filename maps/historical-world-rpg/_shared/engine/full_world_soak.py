"""Scenario-neutral deterministic soak runner for authored campaign datasets.

Scenario configuration selects sources and workload; this module contains no
historical IDs or dates.  State is deliberately abstract and JSON-only so the
same authoritative state can be advanced while most regions have no Warcraft
objects instantiated.
"""
from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path

FORMAT = "warcraftmap_full_world_soak_config_v1"
CHECKPOINT_FORMAT = "warcraftmap_full_world_soak_checkpoint_v1"
SUMMARY_FORMAT = "warcraftmap_full_world_soak_summary_v1"
STATE_VERSION = 1


class SoakError(ValueError):
    pass


class InvariantFailure(RuntimeError):
    def __init__(self, day, subsystem, invariant, entity_id, message):
        self.diagnostic = {"date": date.fromordinal(day).isoformat(), "subsystem": subsystem,
                           "invariant": invariant, "entityId": entity_id, "message": message}
        super().__init__(message)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


@dataclass(frozen=True)
class Profile:
    id: str
    seeds: tuple[int, ...]
    step_days: int
    jump_days: int
    checkpoint_date: str
    representation_limit: int
    expected_hashes: tuple[tuple[int, str], ...]


def load_config(path):
    path = Path(path).resolve()
    try:
        raw = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise SoakError(f"cannot load soak configuration {path}") from exc
    if raw.get("format") != FORMAT or not isinstance(raw.get("fixtureVersion"), int):
        raise SoakError("unsupported full-world soak configuration")
    sources = raw.get("sources")
    if not isinstance(sources, dict) or "world" not in sources:
        raise SoakError("sources must name an authored world")
    loaded = {}
    for name, relative in sorted(sources.items()):
        if not isinstance(name, str) or not name or not isinstance(relative, str):
            raise SoakError("source names and paths must be non-empty strings")
        source = (path.parent / relative).resolve()
        try:
            source.relative_to(path.parent.parent)
        except ValueError as exc:
            raise SoakError(f"source {name} escapes scenario directory") from exc
        try:
            loaded[name] = json.loads(source.read_text())
        except (OSError, json.JSONDecodeError) as exc:
            raise SoakError(f"cannot load authored source {name}") from exc
    workload = raw.get("workload")
    required = {"economy", "research", "events", "quests", "treasures", "wars",
                "captures", "regionalActivations", "crossMapTransitions", "remoteCommands",
                "reconstruction"}
    if not isinstance(workload, dict) or set(workload) != required:
        raise SoakError("workload must configure every soak subsystem")
    if any(isinstance(value, bool) or not isinstance(value, int) or value <= 0
           for value in workload.values()):
        raise SoakError("workload values must be positive integers")
    logical_tick_days = raw.get("logicalTickDays")
    if isinstance(logical_tick_days, bool) or not isinstance(logical_tick_days, int) or logical_tick_days <= 0:
        raise SoakError("logicalTickDays must be a positive integer")
    raw_profiles = raw.get("profiles")
    if not isinstance(raw_profiles, dict) or not raw_profiles:
        raise SoakError("at least one soak profile is required")
    profiles = {}
    for ident, value in raw_profiles.items():
        if not isinstance(ident, str) or not ident or not isinstance(value, dict):
            raise SoakError("profile names must be non-empty strings and values must be objects")
        seeds = value.get("seeds")
        if not seeds or any(isinstance(x, bool) or not isinstance(x, int) for x in seeds):
            raise SoakError(f"profile {ident} requires integer seeds")
        expected = value.get("expectedNormalizedStateHashes")
        if not isinstance(expected, dict) or set(expected) != {str(seed) for seed in seeds}:
            raise SoakError(f"profile {ident} requires an expected hash for every seed")
        if any(not isinstance(value, str) or len(value) != 64 or
               any(char not in "0123456789abcdef" for char in value)
               for value in expected.values()):
            raise SoakError(f"profile {ident} has an invalid expected normalized state hash")
        p = Profile(ident, tuple(seeds), value.get("stepDays"), value.get("jumpDays"),
                    value.get("checkpointDate"), value.get("representationLimit"),
                    tuple((seed, expected[str(seed)]) for seed in seeds))
        if any(isinstance(x, bool) or not isinstance(x, int) or x <= 0
               for x in (p.step_days, p.jump_days, p.representation_limit)):
            raise SoakError(f"profile {ident} has invalid positive limits")
        try:
            checkpoint_day = date.fromisoformat(p.checkpoint_date)
            start = date.fromisoformat(loaded["world"]["timeline"]["startDate"])
            end = date.fromisoformat(loaded["world"]["timeline"]["endDate"])
        except (KeyError, TypeError, ValueError) as exc:
            raise SoakError(f"profile {ident} has an invalid checkpoint or campaign date") from exc
        if not start < checkpoint_day < end:
            raise SoakError(f"profile {ident} checkpoint must be inside the campaign interval")
        profiles[ident] = p
    return raw, loaded, profiles


def _ids(rows):
    return [x["id"] for x in rows if isinstance(x, dict) and isinstance(x.get("id"), str)]


def _collection_count(value):
    """Count authored records recursively for compact fixture-coverage reporting."""
    if isinstance(value, list):
        return len(value) + sum(_collection_count(item) for item in value)
    if isinstance(value, dict):
        return sum(_collection_count(item) for item in value.values())
    return 0


def build_fixture(config, sources, seed):
    world = sources["world"]
    timeline = world["timeline"]
    start, end = date.fromisoformat(timeline["startDate"]), date.fromisoformat(timeline["endDate"])
    domains = {key: _ids(value) for key, value in world.items() if isinstance(value, list)}
    for value in sources.values():
        if isinstance(value, dict):
            for key, rows in value.items():
                if isinstance(rows, list) and _ids(rows):
                    domains[key] = sorted(set(domains.get(key, ())) | set(_ids(rows)))
                elif isinstance(rows, dict):
                    for nested_key, nested_rows in rows.items():
                        if isinstance(nested_rows, list) and _ids(nested_rows):
                            domains[nested_key] = sorted(set(domains.get(nested_key, ())) | set(_ids(nested_rows)))
    # Supplementary authored inputs are retained by hash and their ID-bearing
    # collections are counted, proving the complete configured fixture loaded.
    source_counts = {name: _collection_count(value) for name, value in sources.items()}
    polities, provinces = world.get("polities", []), world.get("provinces", [])
    settlements = world.get("settlements", [])
    # Activatable regions are physical regional instances with authored
    # settlements. Broader semantic quest-region IDs remain in domains but do
    # not create empty Warcraft-facing maps.
    regions = sorted({x.get("regionalInstanceId") for x in settlements if x.get("regionalInstanceId")})
    if not regions:
        regions = ["world"]
    ownership = {x["id"]: {"ownerId": x.get("legalOwnerPolityId"),
                             "controllerId": x.get("controllerPolityId")} for x in provinces}
    settlement_regions = {x["id"]: x.get("regionalInstanceId", regions[0]) for x in settlements}
    state = {
        "stateVersion": STATE_VERSION, "seed": seed, "date": start.isoformat(),
        "endDate": end.isoformat(), "fixtureHash": digest(sources), "domains": domains,
        "sourceCounts": source_counts, "polityIds": _ids(polities),
        "provinceOwnership": ownership, "settlementRegions": settlement_regions,
        "regions": regions, "activeRegionId": regions[0], "activeRepresentations": [],
        "treasuries": {x["id"]: 100000 for x in polities},
        "research": {x["id"]: 0 for x in polities}, "resolvedEvents": [],
        "resolvedQuests": [], "resolvedTreasures": [], "wars": {}, "commandLog": [],
        "transitionLog": [], "reconstructionCount": 0, "ticks": 0,
        "logicalTickDays": config.get("logicalTickDays", 30),
        "campaignStartDay": start.toordinal(),
        "nextTickDay": start.toordinal() + config.get("logicalTickDays", 30),
    }
    reconstruct(state, config["profiles"][next(iter(config["profiles"]))]["representationLimit"])
    validate(state, start.toordinal(), "fixture", config["workload"])
    return state


def reconstruct(state, limit):
    active = state["activeRegionId"]
    candidates = sorted(k for k, v in state["settlementRegions"].items() if v == active)
    state["activeRepresentations"] = [{"entityId": x, "kind": "settlement"} for x in candidates[:limit]]
    state["reconstructionCount"] += 1


def validate(state, day, subsystem, workload, representation_limit=None):
    polity_ids = set(state["polityIds"])
    if len(polity_ids) != len(state["polityIds"]):
        raise InvariantFailure(day, subsystem, "uniqueness", "polities", "duplicate stable ID")
    for collection in ("treasuries", "research"):
        keys = set(state[collection])
        if keys != polity_ids:
            entity_id = sorted(keys ^ polity_ids)[0]
            raise InvariantFailure(day, subsystem, "reference", entity_id,
                                   f"{collection} polity references are incomplete or unknown")
    provinces = set(state["domains"].get("provinces", []))
    for ident, holding in state["provinceOwnership"].items():
        if ident not in provinces or holding["ownerId"] not in polity_ids or holding["controllerId"] not in polity_ids:
            raise InvariantFailure(day, subsystem, "ownership_control", ident, "invalid owner or controller reference")
    if state["activeRegionId"] not in state["regions"]:
        raise InvariantFailure(day, subsystem, "navigation", state["activeRegionId"], "unknown active region")
    represented = state["activeRepresentations"]
    if representation_limit is not None and len(represented) > representation_limit:
        raise InvariantFailure(day, subsystem, "bounded_representation", state["activeRegionId"], "active representation limit exceeded")
    if len({x["entityId"] for x in represented}) != len(represented):
        raise InvariantFailure(day, subsystem, "uniqueness", "active_representations", "duplicate active representation")
    settlements = set(state["settlementRegions"])
    for row in represented:
        if row.get("entityId") not in settlements:
            raise InvariantFailure(day, subsystem, "reference", row.get("entityId", "active_representations"),
                                   "represented settlement is unknown")
        if state["settlementRegions"][row["entityId"]] != state["activeRegionId"]:
            raise InvariantFailure(day, subsystem, "navigation", row["entityId"],
                                   "represented settlement is outside the active region")
    if sum(state["treasuries"].values()) != 100000 * len(polity_ids):
        raise InvariantFailure(day, subsystem, "conservation", "treasuries", "currency was not conserved")
    for target, domain in (("resolvedEvents", "events"), ("resolvedQuests", "quests"),
                           ("resolvedTreasures", "treasures")):
        unknown = next((x for x in state[target] if x not in state["domains"].get(domain, [])), None)
        if unknown is not None:
            raise InvariantFailure(day, subsystem, "reference", unknown, f"resolved {domain} entry is unknown")
        if len(state[target]) != len(set(state[target])):
            raise InvariantFailure(day, subsystem, "uniqueness", target, f"duplicate resolved {domain} entry")
    for war_id, participants in state["wars"].items():
        if len(participants) != 2 or any(x not in polity_ids for x in participants):
            raise InvariantFailure(day, subsystem, "reference", war_id, "war has an unknown participant")
    for entry in state["commandLog"]:
        if entry.get("targetId") not in polity_ids:
            raise InvariantFailure(day, subsystem, "reference", str(entry.get("targetId")),
                                   "remote command target is unknown")
    for entry in state["transitionLog"]:
        if entry.get("regionId") not in state["regions"]:
            raise InvariantFailure(day, subsystem, "navigation", str(entry.get("regionId")),
                                   "cross-map transition target is unknown")
    expected_next = state["campaignStartDay"] + (state["ticks"] + 1) * state["logicalTickDays"]
    if state["logicalTickDays"] <= 0 or state["nextTickDay"] != expected_next or state["nextTickDay"] <= day:
        raise InvariantFailure(day, subsystem, "scheduling", "logical_tick", "logical tick schedule is inconsistent")
    return True


def _pick(values, seed, tick, salt):
    if not values:
        return None
    raw = hashlib.sha256(f"{seed}|{tick}|{salt}".encode()).digest()
    return values[int.from_bytes(raw[:8], "big") % len(values)]


def _tick(state, day, workload, limit):
    state["ticks"] += 1
    tick, seed = state["ticks"], state["seed"]
    polities = state["polityIds"]
    if len(polities) > 1:
        payer = _pick(polities, seed, tick, "economy")
        payee = polities[(polities.index(payer) + 1) % len(polities)]
        state["treasuries"][payer] -= workload["economy"]
        state["treasuries"][payee] += workload["economy"]
    researcher = _pick(polities, seed, tick, "research")
    if researcher:
        state["research"][researcher] += workload["research"]
    for domain, target, key in (("events", "resolvedEvents", "events"),
                                ("quests", "resolvedQuests", "quests")):
        values = state["domains"].get(domain, [])
        chosen = _pick(values, seed, tick, key)
        if chosen and chosen not in state[target]: state[target].append(chosen)
    treasures = state["domains"].get("treasures", [])
    chosen = _pick(treasures, seed, tick, "treasures")
    if chosen and chosen not in state["resolvedTreasures"]: state["resolvedTreasures"].append(chosen)
    if tick % workload["wars"] == 0 and len(polities) > 1:
        attacker = _pick(polities, seed, tick, "war")
        defender = polities[(polities.index(attacker) + 1) % len(polities)]
        state["wars"][f"war_{tick:06d}"] = [attacker, defender]
    if tick % workload["captures"] == 0 and state["provinceOwnership"]:
        province = _pick(sorted(state["provinceOwnership"]), seed, tick, "capture")
        current = state["provinceOwnership"][province]["controllerId"]
        state["provinceOwnership"][province]["controllerId"] = polities[(polities.index(current) + 1) % len(polities)]
    if tick % workload["regionalActivations"] == 0:
        idx = (state["regions"].index(state["activeRegionId"]) + 1) % len(state["regions"])
        state["activeRegionId"] = state["regions"][idx]
        reconstruct(state, limit)
    if tick % workload["crossMapTransitions"] == 0:
        state["transitionLog"] = (state["transitionLog"] + [{"tick": tick, "regionId": state["activeRegionId"]}])[-64:]
    if tick % workload["remoteCommands"] == 0:
        target = _pick(polities, seed, tick, "command")
        state["commandLog"] = (state["commandLog"] + [{"tick": tick, "targetId": target}])[-64:]
    if tick % workload["reconstruction"] == 0:
        reconstruct(state, limit)
    state["date"] = date.fromordinal(day).isoformat()
    validate(state, day, "world", workload, limit)


def advance(state, target_date, step_days, workload, limit):
    """Advance through invariant daily logical ticks, grouped by caller steps.

    Grouping cannot affect state, which makes accelerated large jumps exactly
    equivalent to normal progression without skipping scheduled work.
    """
    target = date.fromisoformat(target_date).toordinal()
    current = date.fromisoformat(state["date"]).toordinal()
    end = date.fromisoformat(state["endDate"]).toordinal()
    if target < current or target > end or step_days <= 0:
        raise SoakError("invalid soak interval")
    while current < target:
        boundary = min(target, current + step_days)
        while state["nextTickDay"] <= boundary:
            tick_day = state["nextTickDay"]
            state["nextTickDay"] += state["logicalTickDays"]
            _tick(state, tick_day, workload, limit)
        current = boundary
        state["date"] = date.fromordinal(current).isoformat()
    validate(state, target, "timeline", workload, limit)
    return state


def checkpoint(state):
    return {"format": CHECKPOINT_FORMAT, "stateVersion": STATE_VERSION,
            "stateHash": digest(state), "state": copy.deepcopy(state)}


def resume(value):
    if not isinstance(value, dict) or value.get("format") != CHECKPOINT_FORMAT or value.get("stateVersion") != STATE_VERSION:
        raise SoakError("unsupported full-world checkpoint")
    state = copy.deepcopy(value.get("state"))
    if not isinstance(state, dict) or value.get("stateHash") != digest(state):
        raise SoakError("checkpoint hash mismatch")
    return state


def normalized_state_hash(state):
    value = copy.deepcopy(state)
    value.pop("activeRepresentations", None)  # derived, bounded Warcraft-facing projection
    return digest(value)


def run_profile(config, sources, profile, max_diagnostics=4):
    runs, failures = [], []
    expected_hashes = dict(profile.expected_hashes)
    for seed in profile.seeds:
        try:
            initial = build_fixture(config, sources, seed)
            start_bytes = len(canonical(initial))
            normal = copy.deepcopy(initial)
            advance(normal, normal["endDate"], profile.step_days, config["workload"], profile.representation_limit)
            accelerated = copy.deepcopy(initial)
            advance(accelerated, accelerated["endDate"], profile.jump_days, config["workload"], profile.representation_limit)
            split = copy.deepcopy(initial)
            advance(split, profile.checkpoint_date, profile.step_days, config["workload"], profile.representation_limit)
            resumed = resume(json.loads(canonical(checkpoint(split))))
            advance(resumed, resumed["endDate"], profile.jump_days, config["workload"], profile.representation_limit)
            hashes = [normalized_state_hash(x) for x in (normal, accelerated, resumed)]
            if len(set(hashes)) != 1:
                raise InvariantFailure(date.fromisoformat(normal["endDate"]).toordinal(), "persistence",
                                       "execution_equivalence", "world", "normal, accelerated, and resumed states differ")
            if hashes[0] != expected_hashes[seed]:
                raise InvariantFailure(date.fromisoformat(normal["endDate"]).toordinal(), "persistence",
                                       "normalized_state_hash", f"seed:{seed}",
                                       "normalized final state does not match the configured fixture hash")
            runs.append({"seed": seed, "workload": dict(config["workload"]),
                         "initialStateBytes": start_bytes, "finalStateBytes": len(canonical(normal)),
                         "stateGrowthBytes": len(canonical(normal)) - start_bytes,
                         "ticks": normal["ticks"], "activeRepresentations": len(normal["activeRepresentations"]),
                         "normalizedStateHash": hashes[0]})
        except InvariantFailure as exc:
            failures.append(exc.diagnostic)
    return {"format": SUMMARY_FORMAT, "fixtureVersion": config["fixtureVersion"],
            "profile": profile.id, "fixtureHash": digest(sources), "runs": runs,
            "failures": failures[:max_diagnostics], "status": "pass" if not failures else "failure",
            "passed": not failures}
