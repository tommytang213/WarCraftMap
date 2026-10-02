#!/usr/bin/env python3
"""Validate and deterministically project the first Age of Sail quest campaign."""
from __future__ import annotations

import argparse
import copy
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "scenario" / "campaign-quests.json"
WORLD = ROOT / "scenario" / "world" / "world.json"
ID = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")
COLLECTIONS = {
    "polity": "polities", "province": "provinces", "settlement": "settlements",
    "character": "characters", "technology": "technologies", "institution": "institutions",
    "navigation_zone": "navigationZones",
}
ADAPTERS = {"economy", "character", "title", "diplomacy", "discovery", "technology", "settlement"}
PRECISIONS = {"exact", "approximate", "region", "hidden"}


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def refs(values):
    return [{"kind": kind, "id": ident} for kind, ident in values]


def validate(source, world):
    assert source.get("schemaVersion") == 1
    coverage = source["coverageTargets"]
    regions = {x["id"] for x in world["regionalGeography"]["regions"]}
    assert set(coverage["majorRegions"]) == regions
    indexes = {kind: {x["id"] for x in world[name]} for kind, name in COLLECTIONS.items()}
    events = {x["id"] for x in world["events"]}
    quests = source["quests"]
    story = source.get("releaseStoryQuests", [])
    quest_ids = {q["id"] for q in quests}
    assert len(quest_ids) == len(quests) and all(ID.fullmatch(x) for x in quest_ids)
    story_ids = {q["id"] for q in story}
    assert len(story_ids) == len(story) and not story_ids & quest_ids and all(ID.fullmatch(x) for x in story_ids)
    assert len(quests) + len(story) + len(world.get("personalQuests", [])) >= coverage["minimumAuthoredStoryQuests"]
    assert {"regional", "personal", "polity", "event_linked", "administration"} <= {q["category"] for q in story}
    for quest in story:
        assert quest["region"] in regions and quest["giverSettlementId"] in indexes["settlement"]
        assert quest["title"].strip() and quest["summary"].strip() and len(quest["objectives"]) >= 3
        assert all(str(x).strip() for x in quest["objectives"])
        assert quest["alternateOutcome"].strip() and quest["failureRecovery"].strip()
        assert {"region", "approximate", "return_to_giver"} <= set(quest["guidance"])
    regional = [q for q in quests if q["chainKind"] == "regional"]
    long_chains = [q for q in quests if q["chainKind"] == "long"]
    personal = [q for q in quests if q["chainKind"] == "personal"]
    cross_region = [q for q in quests if q["chainKind"] == "cross_region"]
    repeatable = [q for q in quests if q["chainKind"] == "repeatable"]
    assert len(regional) >= coverage["minimumRegionalChains"]
    assert {q["region"] for q in regional} == regions and len(long_chains) >= coverage["minimumLongChains"]
    assert len(personal) >= coverage.get("minimumPersonalChains", 0)
    assert len(cross_region) >= coverage.get("minimumCrossRegionChains", 0)
    assert len(repeatable) >= coverage.get("minimumRepeatableChains", 0)
    objective_kinds, guidance_kinds, used_regions = set(), set(), set()
    reward_adapters = set()
    for quest in quests:
        assert quest["title"].strip() and quest["summary"].strip() and quest["divergences"]
        assert quest["region"] in regions | {"global"}
        for prerequisite in quest.get("prerequisiteQuestIds", []):
            assert prerequisite in quest_ids and prerequisite != quest["id"]
        stage_ids = {x["id"] for x in quest["stages"]}
        assert len(stage_ids) == len(quest["stages"])
        reachable, pending = set(), [quest["stages"][0]["id"]]
        objective_ids = set()
        terminal = 0
        for stage in quest["stages"]:
            assert stage["title"].strip() and all(x in stage_ids and x != stage["id"] for x in stage["next"])
            terminal += not stage["next"]
            assert stage["objectives"]
            for objective in stage["objectives"]:
                assert ID.fullmatch(objective["id"]) and objective["id"] not in objective_ids
                objective_ids.add(objective["id"]); objective_kinds.add(objective["kind"])
                assert objective["text"].strip() and objective["refs"]
                for kind, ident in objective["refs"]:
                    assert kind in indexes and ident in indexes[kind]
                if "eventId" in objective:
                    assert objective["kind"] == "historical_event" and objective["eventId"] in events
                guidance = objective.get("guidance")
                if guidance:
                    precision = guidance["precision"]; guidance_kinds.add(precision); used_regions.add(guidance["regionId"])
                    assert precision in PRECISIONS and guidance["regionId"] in regions
                    if precision == "approximate":
                        assert guidance.get("searchAreas") and all(a["radius"] > 0 for a in guidance["searchAreas"])
                    if guidance.get("purpose") in {"return_to_giver", "turn_in"}:
                        guidance_kinds.add(guidance["purpose"])
        while pending:
            current = pending.pop()
            if current in reachable: continue
            reachable.add(current)
            pending.extend(next(x["next"] for x in quest["stages"] if x["id"] == current))
        assert reachable == stage_ids and terminal
        for reward in quest["rewards"]:
            assert reward["adapter"] in ADAPTERS and ID.fullmatch(reward["id"])
            reward_adapters.add(reward["adapter"])
            for kind, ident in reward["refs"]: assert kind in indexes and ident in indexes[kind]
    assert set(coverage["requiredObjectiveKinds"]) <= objective_kinds
    assert set(coverage["requiredGuidance"]) <= guidance_kinds
    assert regions <= used_regions
    assert {"economy", "character", "title", "diplomacy", "discovery", "technology"} <= reward_adapters


def project(source, world):
    result = copy.deepcopy(world)
    settlements = {x["id"]: x for x in world["settlements"]}
    locations = {}
    projected = []
    for quest in source["quests"]:
        stages, objectives, destinations = [], [], {}
        for stage in quest["stages"]:
            stages.append({"id": stage["id"], "title": stage["title"],
                           "objectiveIds": [x["id"] for x in stage["objectives"]], "nextStageIds": stage["next"]})
            for objective in stage["objectives"]:
                objectives.append({"id": objective["id"], "description": objective["text"],
                                   "conditionId": f"quest_{objective['kind']}_satisfied", "entityRefs": refs(objective["refs"])})
                if "guidance" in objective:
                    guide = copy.deepcopy(objective["guidance"])
                    settlement_id = guide.get("settlementId")
                    if settlement_id:
                        location_id = f"quest_location_{settlement_id}"
                        settlement = settlements[settlement_id]
                        locations[location_id] = {"id": location_id, "regionId": guide["regionId"],
                          "settlementId": settlement_id, "position": copy.deepcopy(settlement.get("localPosition", {"x": 50, "y": 50}))}
                        guide["locationId"] = location_id
                    destinations[objective["id"]] = guide
        giver_kind, giver_id = quest["giver"]
        turn_kind, turn_id = quest["turnIn"]
        turn_region = quest["region"] if quest["region"] != "global" else next(
            g["regionId"] for s in quest["stages"] for o in s["objectives"]
            for g in [o.get("guidance", {})] if g.get("settlementId") == turn_id)
        turn_location = f"quest_location_{turn_id}"
        if turn_location not in locations:
            settlement = settlements[turn_id]
            locations[turn_location] = {"id": turn_location, "regionId": turn_region, "settlementId": turn_id,
                                       "position": copy.deepcopy(settlement.get("localPosition", {"x": 50, "y": 50}))}
        campaign = {"region": quest["region"], "chainKind": quest["chainKind"],
                    "objectiveKinds": sorted({o["kind"] for s in quest["stages"] for o in s["objectives"]}),
                    "historicalEventIds": sorted({o["eventId"] for s in quest["stages"] for o in s["objectives"] if "eventId" in o}),
                    "divergences": copy.deepcopy(quest["divergences"]), "rewards": copy.deepcopy(quest["rewards"])}
        outcomes = [{"id": r["id"], "kind": "scenario_outcome", "outcomeId": f"quest_{r['adapter']}_{r['effect']}",
                     "entityRefs": refs(r["refs"])} for r in quest["rewards"]]
        projected.append({"id": quest["id"], "title": quest["title"], "summary": quest["summary"],
          "initialStageId": stages[0]["id"], "stages": stages, "objectives": objectives,
          "prerequisites": [{"kind": "quest_completed", "id": x} for x in quest.get("prerequisiteQuestIds", [])],
          "outcomes": outcomes, "journal": {"giver": {"kind": giver_kind, "id": giver_id},
            "turnIn": {"kind": turn_kind, "id": turn_id}, "destinations": destinations,
            "turnInDestination": {"precision": "exact", "regionId": turn_region, "settlementId": turn_id, "locationId": turn_location}},
          "campaign": campaign})
    # Release-story records deliberately use the same proven quest runtime while
    # retaining their own category. Their prose, objectives and recovery behavior
    # remain scenario data rather than engine conditionals.
    for quest in source.get("releaseStoryQuests", []):
        settlement_id=quest["giverSettlementId"]; region=quest["region"]
        location_id=f"quest_location_{settlement_id}"
        if location_id not in locations:
            settlement=settlements[settlement_id]
            locations[location_id]={"id":location_id,"regionId":region,"settlementId":settlement_id,
                                    "position":copy.deepcopy(settlement.get("localPosition",{"x":50,"y":50}))}
        objective_ids=[f"task_{n+1}" for n in range(len(quest["objectives"]))]
        stages=[]; objectives=[]; destinations={}
        for n,(objective_id,text) in enumerate(zip(objective_ids,quest["objectives"])):
            stage_id=f"stage_{n+1}"; next_ids=[f"stage_{n+2}"] if n+1<len(objective_ids) else []
            stages.append({"id":stage_id,"title":text,"objectiveIds":[objective_id],"nextStageIds":next_ids})
            objectives.append({"id":objective_id,"description":text,"conditionId":"quest_story_objective_satisfied",
                               "entityRefs":[{"kind":"settlement","id":settlement_id}]})
            if n == 0:
                destinations[objective_id]={"precision":"region","regionId":region}
            elif n == len(objective_ids)-1:
                destinations[objective_id]={"precision":"exact","regionId":region,"settlementId":settlement_id,"locationId":location_id,
                                               "purpose":"return_to_giver"}
            else:
                destinations[objective_id]={"precision":"approximate","regionId":region,
                                             "searchAreas":[{"x":50,"y":50,"radius":20}]}
        projected.append({"id":quest["id"],"title":quest["title"],"summary":quest["summary"],"initialStageId":"stage_1",
          "stages":stages,"objectives":objectives,"prerequisites":[],
          "outcomes":[{"id":"bounded_service_reward","kind":"scenario_outcome","outcomeId":"quest_bounded_story_service",
                       "entityRefs":[{"kind":"settlement","id":settlement_id}]}],
          "journal":{"giver":{"kind":"settlement","id":settlement_id},"turnIn":{"kind":"settlement","id":settlement_id},
                     "destinations":destinations,"turnInDestination":{"precision":"exact","regionId":region,"settlementId":settlement_id,"locationId":location_id}},
          "campaign":{"region":region,"chainKind":quest["category"],"objectiveKinds":["story_service"],"historicalEventIds":[],
                      "divergences":[quest["alternateOutcome"],quest["failureRecovery"]],"rewards":[{"profile":quest["rewardProfile"]}]}})
    result["quests"] = sorted(projected, key=lambda x: x["id"])
    result["questLocations"] = sorted(locations.values(), key=lambda x: x["id"])
    return result


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--write", action="store_true"); args = parser.parse_args()
    source, world = load(SOURCE), load(WORLD); validate(source, world); expected = project(source, world)
    if args.write:
        WORLD.write_text(json.dumps(expected, indent=2) + "\n", encoding="utf-8")
    elif expected != world:
        raise SystemExit("campaign quest projection is stale; run tooling/campaign_quests.py --write")
    print(f"validated {len(source['quests'])} quest chains and explicit coverage targets")


if __name__ == "__main__": main()
