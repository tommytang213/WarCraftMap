"""Country-specific, campaign-state-driven government contribution rewards.

The runtime deliberately does not own economy, territory, or allegiance state.  A
caller supplies an authoritative state view for each evaluation and applies the
returned transaction to those authorities atomically.  This keeps the reusable
policy engine independent of any one scenario's currencies, titles, or units.
"""
from __future__ import annotations

import copy
import re
from dataclasses import dataclass
from typing import Any, Mapping


REWARD_WORLD_STATE_KEY = "contributionRewardState"
REWARD_KINDS = frozenset({
    "money", "equipment", "office", "privilege", "access", "title", "land",
    "favor", "reputation", "promise", "military_support", "naval_support",
})
_ID = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")


class ContributionRewardError(ValueError):
    pass


def _id(value: Any, context: str) -> str:
    if not isinstance(value, str) or not _ID.fullmatch(value):
        raise ContributionRewardError(f"{context}: invalid stable ID {value!r}")
    return value


def _integer(value: Any, context: str, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ContributionRewardError(f"{context}: must be an integer >= {minimum}")
    return value


def _index(rows: Any, context: str) -> dict[str, dict[str, Any]]:
    if not isinstance(rows, list):
        raise ContributionRewardError(f"{context}: must be an array")
    result = {}
    for raw in rows:
        if not isinstance(raw, Mapping):
            raise ContributionRewardError(f"{context}: entries must be objects")
        ident = _id(raw.get("id"), f"{context}.id")
        if ident in result:
            raise ContributionRewardError(f"{context}: duplicate ID {ident!r}")
        result[ident] = copy.deepcopy(dict(raw))
    return result


@dataclass(frozen=True)
class RewardOffer:
    polity_id: str
    reward_id: str
    kind: str
    available: bool
    reason: str | None
    value: int
    contribution_cost: int

    def to_dict(self) -> dict[str, Any]:
        return {"polityId": self.polity_id, "rewardId": self.reward_id,
                "kind": self.kind, "available": self.available,
                "reason": self.reason, "value": self.value,
                "contributionCost": self.contribution_cost}


class ContributionRewardRuntime:
    """Evaluates and records rewards without caching mutable campaign means."""

    def __init__(self, definitions: Mapping[str, Any], *, polity_ids=()):
        if not isinstance(definitions, Mapping) or definitions.get("schemaVersion") != 1:
            raise ContributionRewardError("reward definitions schemaVersion must be 1")
        self.profiles = _index(definitions.get("polityProfiles"), "polityProfiles")
        expected = set(polity_ids)
        if expected and set(self.profiles) != expected:
            missing = sorted(expected - set(self.profiles))
            extra = sorted(set(self.profiles) - expected)
            raise ContributionRewardError(
                f"profiles must cover active polities exactly (missing={missing}, extra={extra})")
        self._validate_profiles()
        self.progress = {polity_id: {} for polity_id in self.profiles}
        self.claimed_keys: set[str] = set()
        self.grants: list[dict[str, Any]] = []
        self.next_sequence = 1

    def _validate_profiles(self) -> None:
        for polity_id, profile in self.profiles.items():
            if profile.get("polityId") != polity_id:
                raise ContributionRewardError(f"profile {polity_id}: id and polityId must match")
            means = profile.get("startingMeans")
            if not isinstance(means, Mapping):
                raise ContributionRewardError(f"profile {polity_id}: missing startingMeans")
            for key in ("liquidity", "economic", "territorial", "military", "naval", "institutional"):
                value = means.get(key)
                if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 100:
                    raise ContributionRewardError(f"profile {polity_id}: invalid {key} means")
            rewards = _index(profile.get("rewards"), f"profile {polity_id}.rewards")
            for reward_id, reward in rewards.items():
                if reward.get("kind") not in REWARD_KINDS:
                    raise ContributionRewardError(f"reward {polity_id}/{reward_id}: invalid kind")
                _integer(reward.get("threshold"), f"reward {polity_id}/{reward_id}.threshold", 1)
                _integer(reward.get("baseValue", 0), f"reward {polity_id}/{reward_id}.baseValue")
                if not isinstance(reward.get("repeatable", False), bool):
                    raise ContributionRewardError(f"reward {polity_id}/{reward_id}: invalid repeatable")
                if reward["kind"] in {"title", "land", "office"} and reward.get("repeatable", False):
                    raise ContributionRewardError(f"reward {polity_id}/{reward_id}: authority grants cannot repeat")
                if reward.get("storyOverride", False) and not isinstance(reward.get("overrideJustification"), str):
                    raise ContributionRewardError(f"reward {polity_id}/{reward_id}: story override requires justification")
            profile["rewards"] = list(rewards.values())

    @staticmethod
    def _score(state: Mapping[str, Any], key: str, fallback: int) -> int:
        value = state.get(key, fallback)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ContributionRewardError(f"campaign state {key}: must be numeric")
        return max(0, min(100, int(value)))

    def _factor(self, profile: Mapping[str, Any], state: Mapping[str, Any], kind: str) -> int:
        """Return an integer percentage; fixed point keeps offers deterministic."""
        means = profile["startingMeans"]
        if kind == "money":
            capacity = (self._score(state, "liquidity", means["liquidity"]) * 2
                        + self._score(state, "economic", means["economic"])) // 3
        elif kind in {"equipment", "military_support"}:
            capacity = (self._score(state, "military", means["military"]) * 2
                        + self._score(state, "institutional", means["institutional"])) // 3
        elif kind == "naval_support":
            capacity = self._score(state, "naval", means["naval"])
        elif kind in {"land", "title", "office"}:
            capacity = (self._score(state, "territorial", means["territorial"])
                        + self._score(state, "institutional", means["institutional"])) // 2
        else:
            # Intangible and political rewards keep weak polities attractive.
            capacity = max(45, self._score(state, "institutional", means["institutional"]))
        war_exhaustion = self._score(state, "warExhaustion", 0)
        condition = self._score(state, "militaryCondition", 100)
        urgency = self._score(state, "strategicUrgency", 0)
        if kind in {"money", "equipment", "military_support", "naval_support"}:
            capacity = capacity * (100 - war_exhaustion // 2) // 100
            capacity = capacity * (50 + condition // 2) // 100
        # Urgency improves willingness, never creates resources that do not exist.
        return max(20, min(180, 40 + capacity + urgency // 4))

    @staticmethod
    def _controlled(state: Mapping[str, Any], reward: Mapping[str, Any]) -> bool:
        territory = reward.get("territoryId")
        return territory is None or territory in set(state.get("controlledTerritoryIds", ()))

    def offers(self, polity_id: str, contribution_type: str,
               magnitude: int, campaign_state: Mapping[str, Any], *,
               origin_polity_id: str, current_allegiance_polity_id: str,
               player_reputation: int = 0, prior_service: int = 0) -> tuple[RewardOffer, ...]:
        profile = self.profiles.get(polity_id)
        if profile is None:
            raise ContributionRewardError(f"unknown polity {polity_id!r}")
        _id(contribution_type, "contributionType")
        _integer(magnitude, "magnitude", 1)
        if not isinstance(campaign_state, Mapping):
            raise ContributionRewardError("campaign state must be an object")
        progress = self.progress[polity_id].get(contribution_type, 0) + magnitude
        standing = progress + max(-100, min(100, player_reputation)) + max(0, prior_service // 4)
        result = []
        for reward in profile["rewards"]:
            reason = None
            reward_id, kind = reward["id"], reward["kind"]
            claim_key = f"{polity_id}:{reward_id}"
            if contribution_type not in reward.get("contributionTypes", [contribution_type]):
                reason = "contribution_type"
            elif current_allegiance_polity_id != polity_id and not reward.get("foreignService", False):
                reason = "allegiance"
            elif standing < reward["threshold"]:
                reason = "standing"
            elif claim_key in self.claimed_keys and not reward.get("repeatable", False):
                reason = "already_granted"
            elif not self._controlled(campaign_state, reward):
                reason = "territory_not_controlled"
            elif reward.get("requiredTechnologyIds") and not set(reward["requiredTechnologyIds"]).issubset(campaign_state.get("technologyIds", ())):
                reason = "technology"
            elif reward.get("requiredInstitutionIds") and not set(reward["requiredInstitutionIds"]).issubset(campaign_state.get("institutionIds", ())):
                reason = "institution"
            elif reward.get("governmentStates") and campaign_state.get("governmentState") not in reward["governmentStates"]:
                reason = "government_state"
            elif reward.get("rulerStates") and campaign_state.get("rulerState") not in reward["rulerStates"]:
                reason = "ruler_state"
            elif reward.get("requiresTradeAccess", False) and not campaign_state.get("tradeAccess", False):
                reason = "trade_access"
            elif reward.get("scarcityKey") and campaign_state.get("scarcity", {}).get(reward["scarcityKey"], 0) <= 0:
                reason = "scarcity"
            factor = self._factor(profile, campaign_state, kind)
            value = reward.get("baseValue", 0) * factor // 100
            treasury_cost = reward.get("treasuryCost", value if kind == "money" else 0)
            if reason is None and treasury_cost > campaign_state.get("treasury", 0) and not reward.get("storyOverride", False):
                reason = "treasury"
            if reason is None and reward.get("stockCost", 0) > campaign_state.get("materialStock", 0) and not reward.get("storyOverride", False):
                reason = "stock"
            # Origin is intentionally only an authored history gate, never allegiance.
            origins = reward.get("originPolityIds")
            if reason is None and origins is not None and origin_polity_id not in origins:
                reason = "origin_history"
            result.append(RewardOffer(polity_id, reward_id, kind, reason is None,
                                      reason, value, reward["threshold"]))
        return tuple(result)

    def record_contribution(self, polity_id: str, contribution_type: str, magnitude: int,
                            source_key: str) -> int:
        if polity_id not in self.profiles:
            raise ContributionRewardError(f"unknown polity {polity_id!r}")
        _id(contribution_type, "contributionType"); _id(source_key, "sourceKey")
        _integer(magnitude, "magnitude", 1)
        key = f"contribution:{source_key}"
        if key in self.claimed_keys:
            raise ContributionRewardError("contribution source already recorded")
        self.claimed_keys.add(key)
        current = self.progress[polity_id].get(contribution_type, 0) + magnitude
        self.progress[polity_id][contribution_type] = current
        return current

    def grant(self, offer: RewardOffer, *, grant_key: str, campaign_state: Mapping[str, Any],
              origin_polity_id: str, current_allegiance_polity_id: str) -> dict[str, Any]:
        if not offer.available:
            raise ContributionRewardError(f"reward unavailable: {offer.reason}")
        _id(grant_key, "grantKey")
        unique_key = f"grant:{grant_key}"
        reward_key = f"{offer.polity_id}:{offer.reward_id}"
        if unique_key in self.claimed_keys or reward_key in self.claimed_keys:
            raise ContributionRewardError("reward already granted")
        profile_reward = next(x for x in self.profiles[offer.polity_id]["rewards"] if x["id"] == offer.reward_id)
        if current_allegiance_polity_id != offer.polity_id and not profile_reward.get("foreignService", False):
            raise ContributionRewardError("allegiance changed before reward grant")
        if not self._controlled(campaign_state, profile_reward):
            raise ContributionRewardError("reward territory is no longer controlled")
        treasury_cost = profile_reward.get("treasuryCost", offer.value if offer.kind == "money" else 0)
        stock_cost = profile_reward.get("stockCost", 0)
        if not profile_reward.get("storyOverride", False):
            if treasury_cost > campaign_state.get("treasury", 0):
                raise ContributionRewardError("treasury can no longer fund reward")
            if stock_cost > campaign_state.get("materialStock", 0):
                raise ContributionRewardError("material stock can no longer fund reward")
        self.claimed_keys.add(unique_key)
        if not profile_reward.get("repeatable", False):
            self.claimed_keys.add(reward_key)
        grant = {"sequence": self.next_sequence, "grantKey": grant_key,
                 "polityId": offer.polity_id, "rewardId": offer.reward_id,
                 "kind": offer.kind, "value": offer.value,
                 "treasuryDebit": treasury_cost, "materialStockDebit": stock_cost,
                 "originPolityId": origin_polity_id,
                 "allegiancePolityId": current_allegiance_polity_id}
        for key in ("territoryId", "titleStyleId", "officeId", "contentId"):
            if key in profile_reward:
                grant[key] = profile_reward[key]
        self.grants.append(grant); self.next_sequence += 1
        return copy.deepcopy(grant)

    def snapshot(self) -> dict[str, Any]:
        return {"schemaVersion": 1, "nextSequence": self.next_sequence,
                "progress": [{"polityId": p, "tracks": copy.deepcopy(self.progress[p])}
                             for p in sorted(self.progress)],
                "claimedKeys": sorted(self.claimed_keys),
                "grants": copy.deepcopy(self.grants)}

    def restore(self, candidate: Mapping[str, Any]) -> None:
        if not isinstance(candidate, Mapping) or candidate.get("schemaVersion") != 1:
            raise ContributionRewardError("reward state schemaVersion must be 1")
        rows = candidate.get("progress")
        if not isinstance(rows, list):
            raise ContributionRewardError("reward progress must be an array")
        progress = {}
        for row in rows:
            polity_id = row.get("polityId") if isinstance(row, Mapping) else None
            tracks = row.get("tracks") if isinstance(row, Mapping) else None
            if polity_id not in self.profiles or polity_id in progress or not isinstance(tracks, Mapping):
                raise ContributionRewardError("invalid reward progress record")
            progress[polity_id] = {}
            for key, value in tracks.items():
                progress[polity_id][_id(key, "track")] = _integer(value, "track progress")
        if set(progress) != set(self.profiles):
            raise ContributionRewardError("reward progress does not cover profiles")
        claimed = candidate.get("claimedKeys"); grants = candidate.get("grants")
        if not isinstance(claimed, list) or claimed != sorted(set(claimed)) or not all(isinstance(x, str) for x in claimed):
            raise ContributionRewardError("invalid claimed reward keys")
        if (not isinstance(grants, list) or any(not isinstance(x, Mapping) for x in grants)
                or any(x.get("sequence") != i + 1 for i, x in enumerate(grants))):
            raise ContributionRewardError("invalid reward grant history")
        for grant in grants:
            polity_id = grant.get("polityId")
            if polity_id not in self.profiles or grant.get("rewardId") not in {
                    x["id"] for x in self.profiles[polity_id]["rewards"]}:
                raise ContributionRewardError("reward grant history references missing content")
        next_sequence = _integer(candidate.get("nextSequence"), "nextSequence", 1)
        if next_sequence != len(grants) + 1:
            raise ContributionRewardError("reward sequence is inconsistent")
        self.progress, self.claimed_keys = progress, set(claimed)
        self.grants, self.next_sequence = copy.deepcopy(grants), next_sequence


class ContributionRewardSaveAdapter:
    def __init__(self, runtime: ContributionRewardRuntime, world_state: Mapping[str, Any]):
        self.runtime = runtime
        self.world_state = copy.deepcopy(dict(world_state))

    def capture_world(self):
        result = copy.deepcopy(self.world_state)
        result[REWARD_WORLD_STATE_KEY] = self.runtime.snapshot()
        return result

    def migrate_legacy_world(self, candidate):
        result = copy.deepcopy(dict(candidate))
        result.setdefault(REWARD_WORLD_STATE_KEY, self.runtime.snapshot())
        return result

    def validate_world(self, candidate):
        probe = ContributionRewardRuntime({"schemaVersion": 1,
            "polityProfiles": list(self.runtime.profiles.values())})
        probe.restore(candidate[REWARD_WORLD_STATE_KEY])

    def reconstruct(self, candidate):
        self.validate_world(candidate)
        return copy.deepcopy(candidate[REWARD_WORLD_STATE_KEY])

    def activate(self, candidate, reconstructed):
        self.runtime.restore(reconstructed)
        self.world_state = copy.deepcopy(dict(candidate))
