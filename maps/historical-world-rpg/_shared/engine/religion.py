"""Scenario-neutral, deterministic religion authority and passive-benefit resolver.

Definitions describe identities and balance.  The snapshot contains only stable IDs
and integers; Warcraft objects and presentation are reconstructible projections.
"""
from __future__ import annotations

import copy
import re
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

STATE_VERSION = 1
WORLD_STATE_KEY = "religionState"
SCALE = 10_000
_ID = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")


class ReligionError(ValueError): pass


def _id(value: Any, where: str) -> str:
    if not isinstance(value, str) or not _ID.fullmatch(value):
        raise ReligionError(f"{where}: invalid stable ID {value!r}")
    return value


def _integer(value: Any, where: str, minimum: int = 0, maximum: int | None = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum or maximum is not None and value > maximum:
        raise ReligionError(f"{where}: invalid integer")
    return value


def _index(values: Any, where: str) -> dict[str, dict[str, Any]]:
    if not isinstance(values, list): raise ReligionError(f"{where} must be an array")
    result = {}
    for raw in values:
        if not isinstance(raw, Mapping): raise ReligionError(f"{where} entries must be objects")
        ident = _id(raw.get("id"), f"{where}.id")
        if ident in result: raise ReligionError(f"{where}: duplicate ID {ident}")
        result[ident] = copy.deepcopy(dict(raw))
    return result


@dataclass(frozen=True)
class PassiveBenefit:
    attribute_id: str
    amount_basis_points: int
    cap_basis_points: int


class ReligionRuntime:
    """Owns mutable faith state and derives bounded effects from current sources."""

    def __init__(self, definitions: Mapping[str, Any]) -> None:
        if definitions.get("format") != "warcraftmap_religion_v1" or definitions.get("schemaVersion") != 1:
            raise ReligionError("unsupported religion definitions")
        self.faiths = _index(definitions.get("faiths"), "faiths")
        self.policies = _index(definitions.get("policies"), "policies")
        self.characters = set(map(lambda x: _id(x, "characterIds"), definitions.get("characterIds", [])))
        self.polities = set(map(lambda x: _id(x, "polityIds"), definitions.get("polityIds", [])))
        self.regions = set(map(lambda x: _id(x, "regionIds"), definitions.get("regionIds", [])))
        self._validate_definitions()
        self._state = self.validate_snapshot(definitions.get("initialState"))

    def _validate_definitions(self) -> None:
        if not self.faiths or not self.characters: raise ReligionError("faiths and characterIds must not be empty")
        for fid, faith in self.faiths.items():
            if set(faith) != {"id", "name", "kind", "parentId", "benefits", "influenceCurve"}:
                raise ReligionError(f"faith {fid}: invalid fields")
            if faith["kind"] not in {"tradition", "denomination", "syncretic", "local"} or not isinstance(faith["name"], str) or not faith["name"].strip():
                raise ReligionError(f"faith {fid}: invalid identity")
            parent = faith["parentId"]
            if parent is not None and (_id(parent, "parentId") not in self.faiths or parent == fid): raise ReligionError(f"faith {fid}: invalid parent")
            curve = faith["influenceCurve"]
            if not isinstance(curve, Mapping) or set(curve) != {"personalHalfSaturation", "influenceHalfSaturation"}:
                raise ReligionError(f"faith {fid}: invalid curve")
            _integer(curve["personalHalfSaturation"], "personalHalfSaturation", 1)
            _integer(curve["influenceHalfSaturation"], "influenceHalfSaturation", 1)
            seen = set()
            for benefit in faith["benefits"]:
                if not isinstance(benefit, Mapping) or set(benefit) != {"attributeId", "capBasisPoints", "description"}: raise ReligionError(f"faith {fid}: malformed benefit")
                attr = _id(benefit["attributeId"], "attributeId")
                if attr in seen: raise ReligionError(f"faith {fid}: duplicate benefit")
                seen.add(attr); _integer(benefit["capBasisPoints"], "capBasisPoints", 1, SCALE)
                if not isinstance(benefit["description"], str) or not benefit["description"].strip(): raise ReligionError("benefit description is required")
        # Parent chains must be acyclic.
        for start in self.faiths:
            seen, current = set(), start
            while current is not None:
                if current in seen: raise ReligionError("faith parent cycle")
                seen.add(current); current = self.faiths[current]["parentId"]
        for pid, policy in self.policies.items():
            if set(policy) != {"id", "name", "toleranceBasisPoints", "supportedInfluenceBasisPoints", "minorityUnrestBasisPoints"}: raise ReligionError(f"policy {pid}: invalid fields")
            for key in ("toleranceBasisPoints", "supportedInfluenceBasisPoints", "minorityUnrestBasisPoints"):
                _integer(policy[key], f"policy {pid}.{key}", -SCALE, SCALE)

    def validate_snapshot(self, raw: Any) -> dict[str, Any]:
        required = {"schemaVersion", "characters", "polities", "regions", "institutions", "influence", "conversionHistory", "nextEventSequence"}
        if not isinstance(raw, Mapping) or set(raw) != required or raw.get("schemaVersion") != STATE_VERSION:
            raise ReligionError("religion state must be a complete schemaVersion 1 snapshot")
        state = copy.deepcopy(dict(raw))
        seen = set()
        for row in state["characters"]:
            cid = _id(row.get("characterId"), "characterId")
            if set(row) != {"characterId", "primaryFaithId", "affiliations", "personalInvestment"} or cid not in self.characters or cid in seen: raise ReligionError("unknown, duplicate, or malformed character faith")
            seen.add(cid); primary = row["primaryFaithId"]
            if primary is not None and primary not in self.faiths: raise ReligionError("unknown primary faith")
            _integer(row["personalInvestment"], "personalInvestment")
            total, affiliations = 0, set()
            for item in row["affiliations"]:
                if set(item) != {"faithId", "weightBasisPoints"} or item["faithId"] not in self.faiths or item["faithId"] in affiliations: raise ReligionError("invalid affiliation")
                affiliations.add(item["faithId"]); total += _integer(item["weightBasisPoints"], "weightBasisPoints", 1, SCALE)
            if total > SCALE or primary is not None and primary not in affiliations: raise ReligionError("invalid character affiliation weights")
        if seen != self.characters: raise ReligionError("character faith state is incomplete")
        seen = set()
        for row in state["polities"]:
            pid = row.get("polityId")
            if set(row) != {"polityId", "policyId", "supportedFaithIds", "institutionalState"} or pid not in self.polities or pid in seen or row["policyId"] not in self.policies: raise ReligionError("invalid polity religion state")
            seen.add(pid)
            if len(set(row["supportedFaithIds"])) != len(row["supportedFaithIds"]) or any(x not in self.faiths for x in row["supportedFaithIds"]): raise ReligionError("invalid supported faiths")
            if not isinstance(row["institutionalState"], str): raise ReligionError("invalid institutional state")
        if seen != self.polities: raise ReligionError("polity religion state is incomplete")
        seen = set()
        for row in state["regions"]:
            rid = row.get("regionId")
            if set(row) != {"regionId", "populationUnits", "composition"} or rid not in self.regions or rid in seen: raise ReligionError("invalid region religion state")
            seen.add(rid); _integer(row["populationUnits"], "populationUnits", 1)
            faith_seen, total = set(), 0
            for share in row["composition"]:
                if set(share) != {"faithId", "shareBasisPoints"} or share["faithId"] not in self.faiths or share["faithId"] in faith_seen: raise ReligionError("invalid region composition")
                faith_seen.add(share["faithId"]); total += _integer(share["shareBasisPoints"], "shareBasisPoints", 0, SCALE)
            if total != SCALE: raise ReligionError("region composition must total 10000 basis points")
        if seen != self.regions: raise ReligionError("region religion state is incomplete")
        institution_ids = set()
        for row in state["institutions"]:
            iid = _id(row.get("id"), "institution.id")
            if set(row) != {"id", "faithId", "kind", "influenceUnits", "active"} or iid in institution_ids or row["faithId"] not in self.faiths or not isinstance(row["active"], bool): raise ReligionError("invalid institution")
            institution_ids.add(iid); _integer(row["influenceUnits"], "influenceUnits")
        influence_seen = set()
        for row in state["influence"]:
            if set(row) != {"faithId", "prestigeUnits", "eventUnits"} or row["faithId"] not in self.faiths or row["faithId"] in influence_seen: raise ReligionError("invalid influence state")
            influence_seen.add(row["faithId"]); _integer(row["prestigeUnits"], "prestigeUnits"); _integer(row["eventUnits"], "eventUnits")
        if influence_seen != set(self.faiths): raise ReligionError("influence state must cover every faith")
        sequences = []
        for event in state["conversionHistory"]:
            if set(event) != {"sequence", "characterId", "fromFaithId", "toFaithId", "campaignTick", "costUnits", "reputationConsequences"}: raise ReligionError("invalid conversion event")
            sequences.append(_integer(event["sequence"], "sequence", 1)); _integer(event["campaignTick"], "campaignTick"); _integer(event["costUnits"], "costUnits")
            if event["characterId"] not in self.characters or event["toFaithId"] not in self.faiths or event["fromFaithId"] is not None and event["fromFaithId"] not in self.faiths or not isinstance(event["reputationConsequences"], list): raise ReligionError("invalid conversion history identity")
        next_seq = _integer(state["nextEventSequence"], "nextEventSequence", 1)
        if sequences != list(range(1, next_seq)): raise ReligionError("conversion sequence is not contiguous")
        return state

    def snapshot(self) -> dict[str, Any]: return copy.deepcopy(self._state)

    def _character(self, character_id: str) -> dict[str, Any]:
        return next((x for x in self._state["characters"] if x["characterId"] == character_id), None) or (_ for _ in ()).throw(ReligionError("unknown character"))

    def influence_units(self, faith_id: str) -> int:
        if faith_id not in self.faiths: raise ReligionError("unknown faith")
        population = sum(r["populationUnits"] * next((x["shareBasisPoints"] for x in r["composition"] if x["faithId"] == faith_id), 0) // SCALE for r in self._state["regions"])
        institutions = sum(x["influenceUnits"] for x in self._state["institutions"] if x["faithId"] == faith_id and x["active"])
        government = 0
        for polity in self._state["polities"]:
            if faith_id in polity["supportedFaithIds"]: government += self.policies[polity["policyId"]]["supportedInfluenceBasisPoints"]
        base = next(x for x in self._state["influence"] if x["faithId"] == faith_id)
        return max(0, population + institutions + government + base["prestigeUnits"] + base["eventUnits"])

    def benefits(self, character_id: str) -> tuple[PassiveBenefit, ...]:
        character = self._character(character_id); fid = character["primaryFaithId"]
        if fid is None: return ()
        faith, personal = self.faiths[fid], character["personalInvestment"]
        influence = self.influence_units(fid); curve = faith["influenceCurve"]
        personal_factor = SCALE * personal // (personal + curve["personalHalfSaturation"])
        influence_factor = SCALE * influence // (influence + curve["influenceHalfSaturation"])
        return tuple(PassiveBenefit(x["attributeId"], x["capBasisPoints"] * personal_factor * influence_factor // SCALE // SCALE, x["capBasisPoints"]) for x in faith["benefits"])

    def overview(self, character_id: str) -> dict[str, Any]:
        character = self._character(character_id); fid = character["primaryFaithId"]
        if fid is None: return {"characterId": character_id, "faithId": None, "faithName": "Non-aligned", "benefits": [], "explanation": "No personal faith is currently professed."}
        influence = self.influence_units(fid); faith = self.faiths[fid]
        benefits = self.benefits(character_id)
        descriptions = {x["attributeId"]: x["description"] for x in faith["benefits"]}
        return {"characterId": character_id, "faithId": fid, "faithName": faith["name"], "personalInvestment": character["personalInvestment"], "influenceUnits": influence,
                "benefits": [{"attributeId": x.attribute_id, "amountBasisPoints": x.amount_basis_points, "capBasisPoints": x.cap_basis_points, "description": descriptions[x.attribute_id]} for x in benefits],
                "explanation": f"Benefits use personal investment {character['personalInvestment']} and current campaign influence {influence}; both use bounded diminishing returns."}

    def set_influence(self, faith_id: str, *, prestige_units: int | None = None, event_units: int | None = None) -> None:
        row = next((x for x in self._state["influence"] if x["faithId"] == faith_id), None)
        if row is None: raise ReligionError("unknown faith")
        if prestige_units is not None: row["prestigeUnits"] = _integer(prestige_units, "prestigeUnits")
        if event_units is not None: row["eventUnits"] = _integer(event_units, "eventUnits")

    def set_region_composition(self, region_id: str, composition: Sequence[Mapping[str, Any]]) -> None:
        candidate = self.snapshot(); row = next((x for x in candidate["regions"] if x["regionId"] == region_id), None)
        if row is None: raise ReligionError("unknown region")
        row["composition"] = copy.deepcopy(list(composition)); self._state = self.validate_snapshot(candidate)

    def set_policy(self, polity_id: str, policy_id: str, supported_faith_ids: Sequence[str]) -> None:
        candidate = self.snapshot(); row = next((x for x in candidate["polities"] if x["polityId"] == polity_id), None)
        if row is None: raise ReligionError("unknown polity")
        row["policyId"], row["supportedFaithIds"] = policy_id, list(supported_faith_ids); self._state = self.validate_snapshot(candidate)

    def convert(self, character_id: str, to_faith_id: str, *, campaign_tick: int, cost_units: int, reputation_consequences: Sequence[str], new_investment: int = 0) -> dict[str, Any]:
        candidate = self.snapshot(); row = next((x for x in candidate["characters"] if x["characterId"] == character_id), None)
        if row is None or to_faith_id not in self.faiths or row["primaryFaithId"] == to_faith_id: raise ReligionError("invalid conversion")
        _integer(campaign_tick, "campaignTick"); _integer(cost_units, "costUnits", 1); _integer(new_investment, "newInvestment")
        if not isinstance(reputation_consequences, Sequence) or isinstance(reputation_consequences, (str, bytes)) or not reputation_consequences or any(not isinstance(x, str) or not x for x in reputation_consequences): raise ReligionError("invalid reputation consequences")
        event = {"sequence": candidate["nextEventSequence"], "characterId": character_id, "fromFaithId": row["primaryFaithId"], "toFaithId": to_faith_id, "campaignTick": campaign_tick, "costUnits": cost_units, "reputationConsequences": list(reputation_consequences)}
        row["primaryFaithId"], row["affiliations"], row["personalInvestment"] = to_faith_id, [{"faithId": to_faith_id, "weightBasisPoints": SCALE}], new_investment
        candidate["conversionHistory"].append(event); candidate["nextEventSequence"] += 1
        self._state = self.validate_snapshot(candidate); return copy.deepcopy(event)

    def interaction_context(self, character_id: str, polity_id: str, region_id: str) -> dict[str, Any]:
        character = self._character(character_id); polity = next(x for x in self._state["polities"] if x["polityId"] == polity_id); region = next(x for x in self._state["regions"] if x["regionId"] == region_id)
        fid = character["primaryFaithId"]; share = next((x["shareBasisPoints"] for x in region["composition"] if x["faithId"] == fid), 0)
        return {"faithId": fid, "coReligionistGovernment": fid is not None and fid in polity["supportedFaithIds"], "localShareBasisPoints": share, "policyId": polity["policyId"], "institutionalState": polity["institutionalState"]}

    def restore(self, candidate: Any) -> None: self._state = self.validate_snapshot(candidate)


class ReligionSaveAdapter:
    def __init__(self, runtime: ReligionRuntime, world_state: Mapping[str, Any]): self.runtime, self.world_state = runtime, copy.deepcopy(dict(world_state))
    def capture_world(self) -> dict[str, Any]:
        result = copy.deepcopy(self.world_state); result[WORLD_STATE_KEY] = self.runtime.snapshot(); return result
    def migrate_legacy_world(self, candidate: Mapping[str, Any]) -> dict[str, Any]:
        result = copy.deepcopy(dict(candidate)); result.setdefault(WORLD_STATE_KEY, self.runtime.snapshot()); self.validate_world(result); return result
    def validate_world(self, candidate: Mapping[str, Any]) -> None:
        if WORLD_STATE_KEY not in candidate: raise ReligionError(f"world state is missing {WORLD_STATE_KEY}")
        self.runtime.validate_snapshot(candidate[WORLD_STATE_KEY])
    def reconstruct(self, candidate: Mapping[str, Any]) -> dict[str, Any]: self.validate_world(candidate); return self.runtime.validate_snapshot(candidate[WORLD_STATE_KEY])
    def activate(self, candidate: Mapping[str, Any], reconstructed: Mapping[str, Any]) -> None:
        expected = self.runtime.validate_snapshot(candidate[WORLD_STATE_KEY])
        if dict(reconstructed) != expected: raise ReligionError("reconstructed religion state does not match candidate")
        self.runtime.restore(expected); self.world_state = copy.deepcopy(dict(candidate))
