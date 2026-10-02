"""Scenario-neutral persistent settlement-local quest offer runtime."""
from __future__ import annotations

import copy
import hashlib
import json
import re
from collections.abc import Mapping

STATE_VERSION = 1
WORLD_STATE_KEY = "localQuestState"
_ID = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")
_TERMINAL = frozenset({"completed", "failed", "cancelled", "expired"})


class LocalQuestError(ValueError):
    pass


def _index(rows, label):
    if not isinstance(rows, list):
        raise LocalQuestError(f"{label} must be an array")
    result = {}
    for row in rows:
        if not isinstance(row, Mapping) or not _ID.fullmatch(str(row.get("id", ""))):
            raise LocalQuestError(f"{label} contains an invalid stable ID")
        if row["id"] in result:
            raise LocalQuestError(f"duplicate {label} ID {row['id']!r}")
        result[row["id"]] = copy.deepcopy(dict(row))
    return result


def _rank(seed, *parts):
    payload = "\0".join((str(seed), *map(str, parts))).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


class LocalQuestRuntime:
    """Owns offers independently of story quests and physical board objects.

    Definitions and settlement contexts are immutable inputs. Every selected offer
    is materialized in the snapshot, so reopening a board or crossing maps cannot
    reroll it. Refill is possible only after a terminal result and its authored
    cooldown has elapsed.
    """

    def __init__(self, definitions, settlements, *, campaign_seed, reward_adapter=None, state=None):
        self.families = _index(definitions.get("families", []), "family")
        self.settlements = _index(settlements, "settlement")
        self.seed = str(campaign_seed)
        self.reward_adapter = reward_adapter
        self._validate_definitions()
        self.state = self.validate_snapshot(state) if state is not None else self._initial_state()

    def _validate_definitions(self):
        if len(self.families) < 15:
            raise LocalQuestError("local catalogue must contain at least fifteen authored families")
        categories = set()
        for family_id, family in self.families.items():
            categories.add(family.get("category"))
            variants = _index(family.get("variants", []), f"family {family_id} variant")
            if len(variants) < 3:
                raise LocalQuestError(f"family {family_id} needs at least three authored variants")
            family["_variants"] = variants
            cooldown = family.get("cooldownDays")
            if isinstance(cooldown, bool) or not isinstance(cooldown, int) or cooldown < 1:
                raise LocalQuestError(f"family {family_id} has invalid cooldown")
            cap = family.get("campaignCompletionCap")
            if isinstance(cap, bool) or not isinstance(cap, int) or cap < 1:
                raise LocalQuestError(f"family {family_id} has invalid anti-farming cap")
            for variant_id, variant in variants.items():
                for key in ("title", "summary", "failure", "alternate"):
                    if not str(variant.get(key, "")).strip():
                        raise LocalQuestError(f"{family_id}/{variant_id} lacks authored {key}")
                objectives = variant.get("objectives", [])
                if len(objectives) < 2 or any(not str(x).strip() for x in objectives):
                    raise LocalQuestError(f"{family_id}/{variant_id} needs meaningful objectives")
                rewards = variant.get("rewards", [])
                if not rewards or any(r.get("kind") in {"unique_item", "major_title", "permanent_polity_modifier"} for r in rewards):
                    raise LocalQuestError(f"{family_id}/{variant_id} has missing or exceptional generic rewards")
                if any(r.get("scope") == "polity" for r in rewards) and not variant.get("strategicAccomplishment"):
                    raise LocalQuestError(f"{family_id}/{variant_id} grants an unjustified polity effect")
        if len(categories) < 15:
            raise LocalQuestError("local catalogue category breadth is insufficient")

    @staticmethod
    def settlement_context(settlement):
        kind = settlement.get("kind", "settlement")
        services = set(settlement.get("serviceIds", []))
        tags = {"civilian", kind}
        if "market" in services: tags.update(("trade", "delivery", "shortage", "profession"))
        if any(x in kind for x in ("port", "anchorage", "harbor")): tags.update(("port", "maritime", "escort", "recovery"))
        if kind in {"capital", "metropolis"}: tags.update(("administration", "military", "investigation", "security"))
        if kind in {"fort", "fortress", "outpost", "frontier"}: tags.update(("frontier", "military", "security", "exploration"))
        if "quest_hub" in services: tags.update(("dispute", "investigation"))
        return tags

    @staticmethod
    def slot_count(settlement):
        kind = settlement.get("kind", "settlement")
        services = set(settlement.get("serviceIds", []))
        if kind in {"metropolis"}: base = 8
        elif kind == "capital": base = 7
        elif any(x in kind for x in ("major_port", "city")): base = 5
        elif kind in {"port", "town"}: base = 3
        elif any(x in kind for x in ("outpost", "anchorage", "camp")): base = 1
        else: base = 2
        if "market" not in services: base = max(1, base - 1)
        return min(10, base)

    def _eligible(self, settlement, family):
        tags = self.settlement_context(settlement)
        required = set(family.get("requiredAnyTags", []))
        excluded = set(family.get("excludedTags", []))
        return (not required or bool(tags & required)) and not bool(tags & excluded)

    def _make_offer(self, settlement, slot, cycle, excluded_families=()):
        eligible = [f for f in self.families.values() if f["id"] not in excluded_families and self._eligible(settlement, f)]
        if not eligible:
            raise LocalQuestError(f"settlement {settlement['id']} has no context-valid local family")
        family = min(eligible, key=lambda x: (_rank(self.seed, settlement["id"], slot, cycle, x["id"]), x["id"]))
        variants = list(family["_variants"].values())
        variant = min(variants, key=lambda x: (_rank(self.seed, settlement["id"], slot, cycle, family["id"], x["id"]), x["id"]))
        instance_id = f"local_{settlement['id']}_{slot}_{cycle}"
        return {"id": instance_id, "settlementId": settlement["id"], "slot": slot, "cycle": cycle,
                "familyId": family["id"], "variantId": variant["id"], "category": family["category"],
                "status": "offered", "acceptedDay": None, "resolvedDay": None, "refillDay": None,
                "rewardClaimed": False, "controllerAtCreation": settlement.get("controllerPolityId")}

    def _initial_state(self):
        offers = []
        for settlement in sorted(self.settlements.values(), key=lambda x: x["id"]):
            used = set()
            for slot in range(self.slot_count(settlement)):
                offer = self._make_offer(settlement, slot, 0, used)
                offers.append(offer); used.add(offer["familyId"])
        return {"schemaVersion": STATE_VERSION, "campaignSeed": self.seed, "day": 0,
                "offers": offers, "familyCompletions": [], "deliveredRewardKeys": []}

    def validate_snapshot(self, state):
        required = {"schemaVersion", "campaignSeed", "day", "offers", "familyCompletions", "deliveredRewardKeys"}
        if not isinstance(state, Mapping) or set(state) != required or state.get("schemaVersion") != STATE_VERSION:
            raise LocalQuestError("local quest state schema or fields are invalid")
        result = copy.deepcopy(dict(state))
        if result["campaignSeed"] != self.seed or not isinstance(result["day"], int) or result["day"] < 0:
            raise LocalQuestError("local quest seed/day is incompatible")
        offers = _index(result["offers"], "offer")
        occupied = set()
        for offer in offers.values():
            settlement = self.settlements.get(offer.get("settlementId")); family = self.families.get(offer.get("familyId"))
            if settlement is None or family is None or offer.get("variantId") not in family["_variants"]:
                raise LocalQuestError("offer has a missing definition reference")
            if offer.get("status") not in {"offered", "active", *_TERMINAL}:
                raise LocalQuestError("offer has invalid status")
            key = (settlement["id"], offer.get("slot"), offer.get("cycle"))
            if key in occupied: raise LocalQuestError("duplicate local quest slot cycle")
            occupied.add(key)
        if len(result["deliveredRewardKeys"]) != len(set(result["deliveredRewardKeys"])):
            raise LocalQuestError("duplicate delivered reward key")
        return result

    def snapshot(self): return copy.deepcopy(self.state)
    def board(self, settlement_id):
        if settlement_id not in self.settlements: raise LocalQuestError("unknown settlement")
        return [copy.deepcopy(x) for x in self.state["offers"] if x["settlementId"] == settlement_id and x["status"] in {"offered", "active"}]
    def _offer(self, instance_id):
        for offer in self.state["offers"]:
            if offer["id"] == instance_id: return offer
        raise LocalQuestError("unknown local quest instance")
    def accept(self, instance_id):
        offer = self._offer(instance_id)
        if offer["status"] != "offered": raise LocalQuestError("local quest is not offered")
        offer["status"], offer["acceptedDay"] = "active", self.state["day"]
    def resolve(self, instance_id, outcome, *, context=None):
        if outcome not in _TERMINAL: raise LocalQuestError("invalid local quest outcome")
        before = copy.deepcopy(self.state); offer = self._offer(instance_id)
        if offer["status"] != "active": raise LocalQuestError("local quest is not active")
        family = self.families[offer["familyId"]]; variant = family["_variants"][offer["variantId"]]
        try:
            if outcome == "completed":
                count = sum(x["familyId"] == family["id"] and x["settlementId"] == offer["settlementId"]
                            for x in self.state["familyCompletions"])
                if count >= family["campaignCompletionCap"]: raise LocalQuestError("family anti-farming cap reached")
                key = f"{instance_id}:completion"
                if key in self.state["deliveredRewardKeys"]: raise LocalQuestError("local rewards already delivered")
                if self.reward_adapter is not None:
                    self.reward_adapter(tuple(copy.deepcopy(variant["rewards"])), copy.deepcopy(dict(context or {})))
                self.state["deliveredRewardKeys"].append(key)
                self.state["familyCompletions"].append({"instanceId": instance_id, "familyId": family["id"],
                                                         "settlementId": offer["settlementId"]})
            offer["status"], offer["resolvedDay"] = outcome, self.state["day"]
            offer["rewardClaimed"] = outcome == "completed"
            offer["refillDay"] = self.state["day"] + family["cooldownDays"]
        except Exception:
            self.state = before
            raise
    def advance_day(self, day):
        if not isinstance(day, int) or day < self.state["day"]: raise LocalQuestError("day cannot move backwards")
        self.state["day"] = day
        terminal = sorted((x for x in self.state["offers"] if x["status"] in _TERMINAL and
                           x["refillDay"] is not None and x["refillDay"] <= day), key=lambda x:x["id"])
        for old in terminal:
            occupied = {x["familyId"] for x in self.board(old["settlementId"]) if x["slot"] != old["slot"]}
            new = self._make_offer(self.settlements[old["settlementId"]], old["slot"], old["cycle"] + 1, occupied)
            self.state["offers"].append(new); old["refillDay"] = None

    def journal_entries(self):
        entries=[]
        for offer in self.state["offers"]:
            if offer["status"] not in {"offered", "active"}: continue
            family=self.families[offer["familyId"]]; variant=family["_variants"][offer["variantId"]]
            entries.append({"id":offer["id"],"category":"settlement_local_random","family":family["category"],
              "title":variant["title"],"summary":variant["summary"],"status":offer["status"],
              "settlementId":offer["settlementId"],"guidance":copy.deepcopy(variant["guidance"])})
        return entries


class LocalQuestSaveAdapter:
    def __init__(self, runtime): self.runtime = runtime
    def capture_world(self, world):
        result=copy.deepcopy(dict(world)); result[WORLD_STATE_KEY]=self.runtime.snapshot(); return result
    def migrate_legacy_world(self, world):
        result=copy.deepcopy(dict(world)); result.setdefault(WORLD_STATE_KEY, self.runtime.snapshot()); return result
    def restore(self, world):
        if WORLD_STATE_KEY not in world: raise LocalQuestError(f"world state is missing {WORLD_STATE_KEY}")
        self.runtime.state=self.runtime.validate_snapshot(world[WORLD_STATE_KEY])
