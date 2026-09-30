"""Scenario-neutral deterministic treasure and secret campaign state.

The engine deliberately knows nothing about Age of Sail content or Warcraft
objects.  A resolved placement is authoritative JSON; map objects are merely a
representation reconstructed from it.
"""
from __future__ import annotations

import copy
import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Sequence

ID_RE = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")
KNOWLEDGE = ("hidden", "region", "approximate", "narrowed", "exact", "collected")


class TreasureError(ValueError):
    pass


class ResolutionError(TreasureError):
    pass


class CollectionError(TreasureError):
    pass


@dataclass(frozen=True)
class CollectionResult:
    treasure_state: dict[str, Any]
    outcome_state: dict[str, Any]
    overflow: tuple[dict[str, Any], ...]


def _index(values: Any, name: str) -> dict[str, Mapping[str, Any]]:
    if not isinstance(values, list):
        raise TreasureError(f"{name}: must be an array")
    result = {}
    for value in values:
        if not isinstance(value, Mapping) or not isinstance(value.get("id"), str) or not ID_RE.fullmatch(value["id"]):
            raise TreasureError(f"{name}: invalid stable ID")
        if value["id"] in result:
            raise TreasureError(f"{name}: duplicate ID {value['id']!r}")
        result[value["id"]] = value
    return result


def validate_catalog(catalog: Mapping[str, Any], references: Mapping[str, Sequence[str]] | None = None) -> None:
    """Validate contracts and, when supplied, repository reference indexes."""
    if not isinstance(catalog, Mapping) or catalog.get("schemaVersion") != 1:
        raise TreasureError("treasure catalog schemaVersion must be 1")
    candidates = _index(catalog.get("candidateLocations"), "candidateLocations")
    pools = _index(catalog.get("rewardPools"), "rewardPools")
    guards = _index(catalog.get("guards", []), "guards")
    hazards = _index(catalog.get("hazards", []), "hazards")
    encounters = _index(catalog.get("encounters", []), "encounters")
    clues = _index(catalog.get("clues"), "clues")
    treasures = _index(catalog.get("treasures"), "treasures")
    if not treasures:
        raise TreasureError("treasures: at least one definition is required")
    refs = {key: set(value) for key, value in (references or {}).items()}
    for cid, candidate in candidates.items():
        for field in ("regionId", "regionalInstanceId", "physicalMapId", "terrainId", "navigationZoneId"):
            if not isinstance(candidate.get(field), str):
                raise TreasureError(f"candidate {cid}: missing {field}")
        position = candidate.get("position")
        if not isinstance(position, Mapping) or not all(isinstance(position.get(k), (int, float)) and not isinstance(position.get(k), bool) for k in ("x", "y")):
            raise TreasureError(f"candidate {cid}: invalid position")
        if candidate.get("accessible") is not True or not isinstance(candidate.get("clearance"), (int, float)) or candidate["clearance"] <= 0:
            raise TreasureError(f"candidate {cid}: inaccessible or lacks placement clearance")
        if candidate.get("inactiveRegionPolicy") not in {"resolve_and_defer_spawn", "abstract_encounter"}:
            raise TreasureError(f"candidate {cid}: unsupported inactive-region behavior")
        for field, domain in (("regionId", "regions"), ("regionalInstanceId", "regionalInstances"), ("physicalMapId", "physicalMaps"), ("terrainId", "terrain"), ("navigationZoneId", "navigationZones")):
            if domain in refs and candidate[field] not in refs[domain]:
                raise TreasureError(f"candidate {cid}: unknown {field} {candidate[field]!r}")
    for pid, pool in pools.items():
        entries = pool.get("entries")
        if not isinstance(entries, list) or not entries:
            raise TreasureError(f"reward pool {pid}: entries must be non-empty")
        for entry in entries:
            if not isinstance(entry, Mapping) or not isinstance(entry.get("weight"), int) or entry["weight"] < 1 or not isinstance(entry.get("outcomes"), list):
                raise TreasureError(f"reward pool {pid}: invalid weighted entry")
    for clue_id, clue in clues.items():
        if clue.get("precision") not in KNOWLEDGE[1:5]:
            raise TreasureError(f"clue {clue_id}: invalid precision")
        if not isinstance(clue.get("template"), str) or "{location}" not in clue["template"]:
            raise TreasureError(f"clue {clue_id}: template must refer to the resolved location")
    for tid, treasure in treasures.items():
        if treasure.get("kind") not in {"unique", "generic"}:
            raise TreasureError(f"treasure {tid}: invalid kind")
        candidate_ids = treasure.get("candidateLocationIds")
        if not isinstance(candidate_ids, list) or not candidate_ids or len(candidate_ids) != len(set(candidate_ids)):
            raise TreasureError(f"treasure {tid}: candidate IDs must be unique and non-empty")
        for cid in candidate_ids:
            if cid not in candidates:
                raise TreasureError(f"treasure {tid}: unknown candidate {cid!r}")
        if treasure.get("rewardPoolId") not in pools:
            raise TreasureError(f"treasure {tid}: unknown reward pool")
        for field, index in (("guardIds", guards), ("hazardIds", hazards), ("encounterIds", encounters), ("clueIds", clues)):
            values = treasure.get(field, [])
            if not isinstance(values, list) or len(values) != len(set(values)) or any(x not in index for x in values):
                raise TreasureError(f"treasure {tid}: invalid {field}")
        policy = treasure.get("collectionPolicy")
        if policy not in {"deplete", "repeatable"}:
            raise TreasureError(f"treasure {tid}: invalid collection policy")
        if policy == "repeatable" and (not isinstance(treasure.get("repeatLimit"), int) or treasure["repeatLimit"] < 2):
            raise TreasureError(f"treasure {tid}: repeatable content needs repeatLimit >= 2")
        if treasure["kind"] == "unique":
            if policy != "deplete" or not treasure.get("historicalEvidence") or not treasure.get("historicalContext"):
                raise TreasureError(f"unique treasure {tid}: requires evidence/context and must deplete")
            anchors = set(treasure.get("anchorRegionIds", []))
            families = set(treasure.get("locationFamilies", []))
            if not anchors or not families:
                raise TreasureError(f"unique treasure {tid}: missing historical anchors")
            for cid in candidate_ids:
                c = candidates[cid]
                if c["regionId"] not in anchors or c.get("locationFamily") not in families:
                    raise TreasureError(f"unique treasure {tid}: candidate {cid!r} violates historical anchor")


def empty_state(campaign_seed: str | int) -> dict[str, Any]:
    seed = str(campaign_seed)
    return {"version": 1, "campaignSeed": seed, "seedFingerprint": hashlib.sha256(seed.encode()).hexdigest(), "resolved": {}, "knowledge": {}, "collectionCounts": {}}


def _choice(seed: str, namespace: str, values: Sequence[Mapping[str, Any]], weight_key: str = "weight") -> Mapping[str, Any]:
    total = sum(int(value.get(weight_key, 1)) for value in values)
    pick = int.from_bytes(hashlib.sha256(f"{seed}\0{namespace}".encode()).digest()[:8], "big") % total
    for value in values:
        weight = int(value.get(weight_key, 1))
        if pick < weight:
            return value
        pick -= weight
    raise AssertionError("weighted choice exhausted")


class TreasureCampaign:
    """Authoritative resolve-once state, safe across maps and reconstruction."""
    def __init__(self, catalog: Mapping[str, Any], campaign_seed: str | int, state: Mapping[str, Any] | None = None):
        validate_catalog(catalog)
        self.catalog = copy.deepcopy(dict(catalog))
        self.treasures = _index(self.catalog["treasures"], "treasures")
        self.candidates = _index(self.catalog["candidateLocations"], "candidateLocations")
        self.pools = _index(self.catalog["rewardPools"], "rewardPools")
        self.state = copy.deepcopy(dict(state)) if state is not None else empty_state(campaign_seed)
        # v3 -> v4 migration cannot invent a scenario's campaign seed. Bootstrap
        # binds it on first use, before any treasure has been resolved.
        if (self.state.get("campaignSeed"), self.state.get("seedFingerprint"), self.state.get("resolved")) == ("", "", {}):
            self.state = empty_state(campaign_seed)
        if self.state.get("version") != 1 or self.state.get("seedFingerprint") != empty_state(campaign_seed)["seedFingerprint"]:
            raise TreasureError("treasure state version or campaign seed does not match")
        for key in ("resolved", "knowledge", "collectionCounts"):
            if not isinstance(self.state.get(key), dict):
                raise TreasureError(f"treasure state {key} must be an object")
        if set(self.state["resolved"]) - set(self.treasures):
            raise TreasureError("treasure state references an unknown treasure")

    def resolve(self, treasure_id: str, *, unavailable_candidate_ids: Sequence[str] = ()) -> dict[str, Any]:
        if treasure_id in self.state["resolved"]:
            return copy.deepcopy(self.state["resolved"][treasure_id])
        treasure = self.treasures.get(treasure_id)
        if treasure is None:
            raise ResolutionError(f"unknown treasure {treasure_id!r}")
        unavailable = set(unavailable_candidate_ids)
        occupied = {value["candidateLocationId"] for value in self.state["resolved"].values()}
        valid = [self.candidates[x] for x in treasure["candidateLocationIds"] if x not in unavailable and (x not in occupied or self.candidates[x].get("allowSharedPlacement") is True)]
        if not valid:
            fallback = treasure.get("fallbackCandidateId")
            if fallback not in self.candidates or fallback in unavailable:
                raise ResolutionError(f"treasure {treasure_id}: no valid candidate and no valid fallback")
            valid = [self.candidates[fallback]]
        seed = self.state["campaignSeed"]
        candidate = _choice(seed, f"{treasure_id}:location", valid)
        reward = _choice(seed, f"{treasure_id}:reward", self.pools[treasure["rewardPoolId"]]["entries"])
        result = {
            "candidateLocationId": candidate["id"], "regionId": candidate["regionId"],
            "regionalInstanceId": candidate["regionalInstanceId"], "physicalMapId": candidate["physicalMapId"],
            "rewardVariantId": reward["id"], "outcomes": copy.deepcopy(treasure.get("fixedOutcomes", [])) + copy.deepcopy(reward["outcomes"]),
            "guardId": self._optional(treasure_id, "guard", treasure.get("guardIds", [])),
            "hazardId": self._optional(treasure_id, "hazard", treasure.get("hazardIds", [])),
            "encounterId": self._optional(treasure_id, "encounter", treasure.get("encounterIds", [])),
        }
        self.state["resolved"][treasure_id] = result
        self.state["knowledge"].setdefault(treasure_id, "hidden")
        self.state["collectionCounts"].setdefault(treasure_id, 0)
        return copy.deepcopy(result)

    def _optional(self, tid: str, kind: str, ids: Sequence[str]) -> str | None:
        if not ids:
            return None
        return _choice(self.state["campaignSeed"], f"{tid}:{kind}", [{"id": x} for x in ids])["id"]

    def apply_clue(self, treasure_id: str, clue_id: str) -> dict[str, Any]:
        resolved = self.resolve(treasure_id)
        treasure = self.treasures[treasure_id]
        if clue_id not in treasure.get("clueIds", []):
            raise TreasureError(f"clue {clue_id!r} does not belong to treasure {treasure_id!r}")
        clue = _index(self.catalog["clues"], "clues")[clue_id]
        old = self.state["knowledge"].get(treasure_id, "hidden")
        if KNOWLEDGE.index(clue["precision"]) > KNOWLEDGE.index(old):
            self.state["knowledge"][treasure_id] = clue["precision"]
        return self.guidance(treasure_id)

    def guidance(self, treasure_id: str) -> dict[str, Any]:
        resolved = self.resolve(treasure_id)
        precision = self.state["knowledge"].get(treasure_id, "hidden")
        if precision == "hidden":
            return {"precision": "hidden"}
        candidate = self.candidates[resolved["candidateLocationId"]]
        result = {"precision": precision, "regionId": candidate["regionId"]}
        if precision in {"approximate", "narrowed"}:
            result["searchArea"] = copy.deepcopy(candidate["searchAreas"][precision])
        if precision in {"exact", "collected"}:
            result.update({"candidateLocationId": candidate["id"], "position": copy.deepcopy(candidate["position"]), "physicalMapId": candidate["physicalMapId"]})
        return result

    def collect(self, treasure_id: str, outcome_state: Mapping[str, Any], apply_outcomes: Callable[[dict[str, Any], Sequence[Mapping[str, Any]]], tuple[dict[str, Any], Sequence[Mapping[str, Any]]]]) -> CollectionResult:
        resolved = self.resolve(treasure_id)
        treasure = self.treasures[treasure_id]
        count = self.state["collectionCounts"].get(treasure_id, 0)
        limit = 1 if treasure["collectionPolicy"] == "deplete" else treasure["repeatLimit"]
        if count >= limit:
            raise CollectionError(f"treasure {treasure_id!r} is depleted")
        staged_treasure = copy.deepcopy(self.state)
        staged_outcomes = copy.deepcopy(dict(outcome_state))
        try:
            applied, overflow = apply_outcomes(staged_outcomes, copy.deepcopy(resolved["outcomes"]))
            if not isinstance(applied, dict) or not isinstance(overflow, (list, tuple)):
                raise CollectionError("outcome adapter returned an invalid transaction")
        except Exception as exc:
            raise CollectionError(f"treasure collection rolled back: {exc}") from exc
        staged_treasure["collectionCounts"][treasure_id] = count + 1
        if count + 1 >= limit:
            staged_treasure["knowledge"][treasure_id] = "collected"
        self.state = staged_treasure
        return CollectionResult(self.export_state(), copy.deepcopy(applied), tuple(copy.deepcopy(overflow)))

    def runtime_records(self, physical_map_id: str, *, active: bool = True) -> tuple[dict[str, Any], ...]:
        if not active:
            return ()
        records = []
        for tid in sorted(self.treasures):
            resolved = self.resolve(tid)
            if resolved["physicalMapId"] == physical_map_id and self.state["knowledge"].get(tid) != "collected":
                records.append({"treasureId": tid, **copy.deepcopy(resolved)})
        return tuple(records)

    def export_state(self) -> dict[str, Any]:
        return copy.deepcopy(self.state)


def deterministic_json(value: Mapping[str, Any]) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
