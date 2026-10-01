"""Scenario-neutral, deterministic territorial-war strategy.

This module deliberately knows no historical names or dates.  It selects a
limited objective from scenario data and submits actions to an authoritative
gateway; it never mutates diplomacy, territory, navigation, or military state.
"""
from __future__ import annotations

import copy
import hashlib
import re
from dataclasses import dataclass
from typing import Any, Mapping, Protocol, Sequence

AI_WORLD_STATE_KEY = "aiTerritorialWarfareState"
AI_STATE_SCHEMA_VERSION = 1
_ID = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")
GOAL_KINDS = frozenset({"press_claim", "recover_territory", "take_strategic_port",
    "take_province", "protect_ally", "protect_trade", "secure_access",
    "suppress_rebellion", "weaken_rival", "expansion"})


class StrategicAIError(ValueError):
    pass


class StrategicGateway(Protocol):
    """Adapter over authoritative subsystem APIs (headless or Warcraft)."""
    def validate_war(self, actor_id: str, target_id: str, goal: Mapping[str, Any]) -> bool: ...
    def declare_war(self, conflict_id: str, actor_id: str, target_id: str) -> None: ...
    def validate_join(self, actor_id: str, conflict_id: str, side: str) -> bool: ...
    def join_war(self, actor_id: str, conflict_id: str, side: str) -> None: ...
    def validate_operation(self, actor_id: str, goal: Mapping[str, Any]) -> bool: ...
    def validate_peace(self, conflict_id: str, outcomes: Sequence[Mapping[str, Any]]) -> bool: ...
    def conclude_peace(self, conflict_id: str, outcomes: Sequence[Mapping[str, Any]]) -> None: ...


@dataclass(frozen=True)
class Decision:
    kind: str
    actor_id: str
    target_id: str | None
    score: int
    goal: Mapping[str, Any] | None = None
    conflict_id: str | None = None


def _sid(value: Any, context: str) -> str:
    if not isinstance(value, str) or not _ID.fullmatch(value):
        raise StrategicAIError(f"{context}: invalid stable ID {value!r}")
    return value


def _integer(value: Any, context: str, low: int = -100000, high: int = 100000) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
        raise StrategicAIError(f"{context}: expected integer in [{low}, {high}]")
    return value


def validate_definitions(source: Mapping[str, Any]) -> dict[str, Any]:
    """Validate portable profiles, coefficients, goals, and historical pressure."""
    if not isinstance(source, Mapping) or source.get("schemaVersion") != 1:
        raise StrategicAIError("AI definitions schemaVersion must be 1")
    result = copy.deepcopy(dict(source))
    rules = result.get("rules")
    if not isinstance(rules, Mapping):
        raise StrategicAIError("rules must be an object")
    for key in ("decisionIntervalDays", "warCooldownDays", "peaceCooldownDays",
                "minimumWarDurationDays", "maximumAttackersPerTarget", "tieBreakRange"):
        _integer(rules.get(key), f"rules.{key}", 1, 100000)
    thresholds = rules.get("thresholds")
    if not isinstance(thresholds, Mapping):
        raise StrategicAIError("rules.thresholds must be an object")
    for key in ("prepare", "declare", "join", "offerPeace", "suicidalStrengthRatio"):
        _integer(thresholds.get(key), f"rules.thresholds.{key}", 0, 10000)
    coefficients = result.get("coefficients")
    required = {"claim", "ownership", "control", "access", "settlementValue", "routeValue",
        "landStrength", "navalStrength", "manpower", "supply", "treasury", "economy",
        "exhaustion", "diplomacy", "alliance", "threat", "terrain", "technology",
        "institutions", "historicalPressure", "goalCompletion", "casualties",
        "economicCost", "continuingThreat", "strategicRisk"}
    if not isinstance(coefficients, Mapping) or not required <= set(coefficients):
        raise StrategicAIError("coefficients are incomplete")
    for key, value in coefficients.items():
        _integer(value, f"coefficients.{key}", -1000, 1000)
    profiles = result.get("profiles")
    if not isinstance(profiles, list) or not profiles:
        raise StrategicAIError("profiles must be a non-empty array")
    profile_ids = set()
    for profile in profiles:
        if not isinstance(profile, Mapping): raise StrategicAIError("profile must be an object")
        ident = _sid(profile.get("id"), "profile.id")
        if ident in profile_ids: raise StrategicAIError("duplicate profile")
        profile_ids.add(ident)
        for key in ("aggression", "riskTolerance", "navalPreference", "allianceReliability", "expansionLimit"):
            _integer(profile.get(key), f"profile.{key}", 0, 100)
    assignments = result.get("assignments")
    if not isinstance(assignments, Mapping): raise StrategicAIError("assignments must be an object")
    for polity, profile in assignments.items():
        _sid(polity, "assignment polity"); _sid(profile, "assignment profile")
        if profile not in profile_ids: raise StrategicAIError("assignment references unknown profile")
    pressures = result.get("historicalPressures", [])
    if not isinstance(pressures, list): raise StrategicAIError("historicalPressures must be an array")
    pressure_ids = set()
    for pressure in pressures:
        if not isinstance(pressure, Mapping): raise StrategicAIError("pressure must be an object")
        ident = _sid(pressure.get("id"), "pressure.id")
        if ident in pressure_ids: raise StrategicAIError("duplicate pressure")
        pressure_ids.add(ident)
        _sid(pressure.get("actorPolityId"), "pressure actor")
        _sid(pressure.get("targetPolityId"), "pressure target")
        if pressure.get("goalKind") not in GOAL_KINDS: raise StrategicAIError("unknown pressure goalKind")
        _integer(pressure.get("weight"), "pressure.weight", -1000, 1000)
        if not isinstance(pressure.get("basis"), list) or not pressure["basis"]:
            raise StrategicAIError("historical pressure needs an explicit divergence basis")
        for condition in pressure["basis"]:
            if not isinstance(condition, Mapping) or condition.get("kind") not in {
                "owner", "controller", "claim", "rivalry", "alliance", "route", "access", "government", "threat"}:
                raise StrategicAIError("invalid historical pressure basis")
    return result


class TerritorialWarfareAI:
    """Bounded strategic evaluator whose input is authoritative campaign state."""
    def __init__(self, definitions: Mapping[str, Any], gateway: StrategicGateway, campaign_seed: str):
        self.definitions = validate_definitions(definitions)
        self.gateway = gateway
        self.seed = str(campaign_seed)
        self.state = {"schemaVersion": 1, "randomCounter": 0, "polities": {},
                      "activeObjectives": [], "history": [], "diagnostics": []}

    def _profile(self, polity: str) -> Mapping[str, Any]:
        ident = self.definitions["assignments"].get(polity, self.definitions["profiles"][0]["id"])
        return next(p for p in self.definitions["profiles"] if p["id"] == ident)

    def _tie(self, *parts: str) -> int:
        bound = self.definitions["rules"]["tieBreakRange"]
        digest = hashlib.sha256("|".join((self.seed, *parts)).encode()).digest()
        return int.from_bytes(digest[:8], "big") % (bound * 2 + 1) - bound

    @staticmethod
    def _basis_holds(condition: Mapping[str, Any], world: Mapping[str, Any]) -> bool:
        kind, ident = condition.get("kind"), condition.get("id")
        table = world.get({"owner":"owners", "controller":"controllers", "claim":"claims",
            "rivalry":"rivalries", "alliance":"alliances", "route":"routes", "access":"access",
            "government":"governments", "threat":"threats"}[kind], {})
        actual = table.get(ident) if isinstance(table, Mapping) else ident in table
        return actual == condition.get("equals", True)

    def _pressure(self, actor: str, target: str, goal_kind: str, day: int, world: Mapping[str, Any]) -> tuple[int, list[str]]:
        total, used = 0, []
        for p in self.definitions["historicalPressures"]:
            if (p["actorPolityId"], p["targetPolityId"], p["goalKind"]) != (actor, target, goal_kind): continue
            if not p.get("startDay", 0) <= day <= p.get("endDay", 10**9): continue
            holds = sum(self._basis_holds(c, world) for c in p["basis"])
            if not holds: continue
            # Partial divergence decays rather than forcing the historical path.
            total += p["weight"] * holds // len(p["basis"]); used.append(p["id"])
        return total, used

    def _war_score(self, actor: str, target: str, goal: Mapping[str, Any], world: Mapping[str, Any], day: int) -> tuple[int, dict[str, int], list[str]]:
        c = self.definitions["coefficients"]; p = self._profile(actor)
        metrics = world["pairMetrics"].get(f"{actor}:{target}", {})
        own = world["polityMetrics"].get(actor, {}); enemy = world["polityMetrics"].get(target, {})
        strength = (own.get("landStrength", 0) + own.get("navalStrength", 0) -
                    enemy.get("landStrength", 0) - enemy.get("navalStrength", 0))
        values = {"claim": metrics.get("claim", 0), "ownership": metrics.get("ownership", 0),
            "control": metrics.get("control", 0), "access": metrics.get("access", 0),
            "settlementValue": goal.get("settlementValue", 0), "routeValue": goal.get("routeValue", 0),
            "landStrength": strength, "navalStrength": own.get("navalStrength", 0)-enemy.get("navalStrength", 0),
            "manpower": own.get("manpower", 0), "supply": own.get("supply", 0),
            "treasury": own.get("treasury", 0), "economy": own.get("economy", 0),
            "exhaustion": -own.get("warExhaustion", 0), "diplomacy": metrics.get("diplomacy", 0),
            "alliance": metrics.get("alliance", 0), "threat": metrics.get("threat", 0),
            "terrain": metrics.get("terrain", 0), "technology": own.get("technology",0)-enemy.get("technology",0),
            "institutions": own.get("institutions",0)-enemy.get("institutions",0)}
        pressure, used = self._pressure(actor, target, goal["kind"], day, world)
        values["historicalPressure"] = pressure
        components = {key: values[key] * c[key] // 100 for key in values}
        components["profile"] = p["aggression"] + p["riskTolerance"] - 100
        components["tieBreak"] = self._tie(actor, target, goal["id"], str(day))
        return sum(components.values()), components, used

    def evaluate(self, day: int, world: Mapping[str, Any]) -> tuple[Decision, ...]:
        """Evaluate due polities. Expected world records contain stable IDs only."""
        decisions = []
        active_attackers = world.get("activeAttackersByTarget", {})
        for actor in sorted(world.get("aiPolityIds", ())):
            local = self.state["polities"].setdefault(actor, {"nextEvaluationDay":0,"warCooldownUntil":0,"peaceCooldownUntil":0})
            if day < local["nextEvaluationDay"]: continue
            local["nextEvaluationDay"] = day + self.definitions["rules"]["decisionIntervalDays"]
            best = None
            for goal in sorted(world.get("candidateGoals", {}).get(actor, ()), key=lambda x:x["id"]):
                target = goal.get("targetPolityId")
                if goal.get("kind") not in GOAL_KINDS or not target or target == actor: continue
                score, components, pressure_ids = self._war_score(actor, target, goal, world, day)
                valid = day >= local["warCooldownUntil"] and self.gateway.validate_operation(actor, goal) and self.gateway.validate_war(actor,target,goal)
                own=world["polityMetrics"].get(actor,{}); enemy=world["polityMetrics"].get(target,{})
                ratio=100*(own.get("landStrength",0)+own.get("navalStrength",0))//max(1,enemy.get("landStrength",0)+enemy.get("navalStrength",0))
                valid &= ratio >= self.definitions["rules"]["thresholds"]["suicidalStrengthRatio"]
                valid &= active_attackers.get(target,0) < self.definitions["rules"]["maximumAttackersPerTarget"]
                self._diagnose(day,actor,"war_candidate",goal["id"],score,valid,components,pressure_ids)
                candidate=(score,goal["id"],goal)
                if valid and (best is None or candidate[:2] > best[:2]): best=candidate
            if best and best[0] >= self.definitions["rules"]["thresholds"]["declare"]:
                goal=copy.deepcopy(best[2]); cid=f"aiwar_{actor}_{goal['targetPolityId']}_{day}"
                self.gateway.declare_war(cid,actor,goal["targetPolityId"])
                objective={"id":f"objective_{actor}_{day}","actorPolityId":actor,"targetPolityId":goal["targetPolityId"],
                    "conflictId":cid,"goal":goal,"startedDay":day,"lastEvaluatedDay":day,"status":"active"}
                self.state["activeObjectives"].append(objective)
                local["warCooldownUntil"]=day+self.definitions["rules"]["warCooldownDays"]
                self._record(day,"declare",actor,cid,goal["id"]); decisions.append(Decision("declare",actor,goal["targetPolityId"],best[0],goal,cid))
            elif best and best[0] >= self.definitions["rules"]["thresholds"]["prepare"]:
                decisions.append(Decision("prepare",actor,best[2]["targetPolityId"],best[0],best[2]))
            # Alliance/threat evaluation is supplied by authoritative diplomacy;
            # the gateway performs the final participant/side validation.
            if day >= local["warCooldownUntil"]:
                joins=sorted(world.get("candidateJoins",{}).get(actor,()), key=lambda x:x["conflictId"])
                for join in joins:
                    score=_integer(join.get("score",0),"candidate join score") + self._tie(actor,join["conflictId"],str(day))
                    valid=self.gateway.validate_join(actor,join["conflictId"],join["side"])
                    self._diagnose(day,actor,"join_candidate",join["conflictId"],score,valid,{"state":score},[])
                    if valid and score >= self.definitions["rules"]["thresholds"]["join"]:
                        self.gateway.join_war(actor,join["conflictId"],join["side"])
                        local["warCooldownUntil"]=day+self.definitions["rules"]["warCooldownDays"]
                        self._record(day,"join",actor,join["conflictId"],join.get("allyPolityId",actor))
                        decisions.append(Decision("join",actor,join.get("opponentPolityId"),score,conflict_id=join["conflictId"]));break
        decisions.extend(self._evaluate_peace(day,world))
        self.state["randomCounter"] += 1
        return tuple(decisions)

    def _evaluate_peace(self, day: int, world: Mapping[str, Any]) -> list[Decision]:
        result=[]; c=self.definitions["coefficients"]
        for obj in sorted(self.state["activeObjectives"],key=lambda x:x["id"]):
            if obj["status"]!="active": continue
            actor=obj["actorPolityId"]; local=self.state["polities"][actor]
            war=world.get("wars",{}).get(obj["conflictId"])
            # A declaration made in this evaluation is not present in the immutable
            # input snapshot until the next campaign tick.
            if not war and day == obj["startedDay"]: continue
            if not war: obj["status"]="obsolete"; continue
            if not self.gateway.validate_operation(actor,obj["goal"]): obj["status"]="obsolete"; continue
            m=war.get("metricsByPolity",{}).get(actor,{})
            components={k:m.get(k,0)*c[k]//100 for k in ("goalCompletion","casualties","exhaustion","economicCost","alliance","continuingThreat","strategicRisk")}
            score=sum(components.values()); obj["lastEvaluatedDay"]=day
            mature=day-obj["startedDay"]>=self.definitions["rules"]["minimumWarDurationDays"]
            outcomes=self._proportionate_outcomes(obj,war)
            valid=mature and day>=local["peaceCooldownUntil"] and self.gateway.validate_peace(obj["conflictId"],outcomes)
            self._diagnose(day,actor,"peace_candidate",obj["id"],score,valid,components,[])
            if valid and score>=self.definitions["rules"]["thresholds"]["offerPeace"]:
                self.gateway.conclude_peace(obj["conflictId"],outcomes);obj["status"]="completed"
                local["peaceCooldownUntil"]=day+self.definitions["rules"]["peaceCooldownDays"]
                self._record(day,"peace",actor,obj["conflictId"],obj["id"])
                result.append(Decision("peace",actor,obj["targetPolityId"],score,obj["goal"],obj["conflictId"]))
        return result

    @staticmethod
    def _proportionate_outcomes(obj: Mapping[str,Any], war: Mapping[str,Any]) -> list[Mapping[str,Any]]:
        occupied=sorted(war.get("occupations",()),key=lambda x:(x["entityKind"],x["entityId"]))
        allowed=set(obj["goal"].get("territoryIds",()))
        result=[]
        for o in occupied:
            transfer=o["entityId"] in allowed and o["controllerPolityId"]==obj["actorPolityId"]
            result.append({"entityKind":o["entityKind"],"entityId":o["entityId"],
                "legalOwnerPolityId":o["controllerPolityId"] if transfer else o["legalOwnerPolityId"],
                "controllerPolityId":o["controllerPolityId"] if transfer else o["legalOwnerPolityId"]})
        return result

    def _diagnose(self,day,actor,kind,candidate,score,accepted,components,pressures):
        self.state["diagnostics"].append({"id":f"diag_{day}_{actor}_{len(self.state['diagnostics'])}","day":day,
            "actorPolityId":actor,"kind":kind,"candidateId":candidate,"score":score,"accepted":bool(accepted),
            "components":dict(sorted(components.items())),"historicalPressureIds":sorted(pressures)})
        limit=self.definitions["rules"].get("diagnosticLimit",256)
        self.state["diagnostics"]=self.state["diagnostics"][-limit:]

    def _record(self,day,kind,actor,conflict,subject):
        self.state["history"].append({"day":day,"kind":kind,"actorPolityId":actor,"conflictId":conflict,"subjectId":subject})
        self.state["history"]=self.state["history"][-self.definitions["rules"].get("historyLimit",256):]

    def snapshot(self) -> dict[str,Any]: return copy.deepcopy(self.state)

    def restore(self, state: Mapping[str,Any]) -> None:
        if not isinstance(state,Mapping) or state.get("schemaVersion") != 1: raise StrategicAIError("AI state schemaVersion must be 1")
        required={"schemaVersion","randomCounter","polities","activeObjectives","history","diagnostics"}
        if set(state)!=required: raise StrategicAIError("AI state has unexpected or missing fields")
        _integer(state["randomCounter"],"randomCounter",0,10**9)
        self.state=copy.deepcopy(dict(state))


class StrategicAISaveAdapter:
    def __init__(self,runtime:TerritorialWarfareAI,world_state:Mapping[str,Any]): self.runtime,self.world_state=runtime,copy.deepcopy(dict(world_state))
    def capture_world(self):
        value=copy.deepcopy(self.world_state);value[AI_WORLD_STATE_KEY]=self.runtime.snapshot();return value
    def migrate_legacy_world(self,value):
        result=copy.deepcopy(dict(value));result.setdefault(AI_WORLD_STATE_KEY,self.runtime.snapshot());return result
    def reconstruct(self,value):
        if AI_WORLD_STATE_KEY not in value: raise StrategicAIError("world state is missing AI territorial warfare state")
        probe=copy.deepcopy(value[AI_WORLD_STATE_KEY]);self.runtime.restore(probe);return probe
    def activate(self,value,reconstructed): self.runtime.restore(reconstructed);self.world_state=copy.deepcopy(dict(value))
