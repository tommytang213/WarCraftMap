"""Validate and emit the live quest_event stage contract, without scenario rules."""
import json
import re

ID = re.compile(r"^[a-z][a-z0-9_]{0,63}$")


def ids(values):
    if not isinstance(values, list) or len(values) != len(set(values)) or any(not isinstance(x, str) or not ID.fullmatch(x) for x in values):
        raise ValueError("invalid or duplicate stable quest IDs")
    return "".join(x + "~" for x in values)


def committed_trade_binding(quest, objective, binding):
    expected = {"adapter", "consumer", "stageId", "marketId", "commodityId"}
    if (set(binding) != expected or binding.get("consumer") != "committed_trade"
            or binding.get("adapter") != "domain_receipt"
            or objective["conditionId"] != "quest_trade_satisfied"
            or any(not isinstance(binding.get(k), str) or not ID.fullmatch(binding[k])
                   for k in ("stageId", "marketId", "commodityId"))
            or objective["entityRefs"] != [{"kind": "settlement", "id": binding["marketId"]}]
            or not any(s["id"] == binding["stageId"] and objective["id"] in s["objectiveIds"] for s in quest["stages"])):
        raise ValueError("committed trade requires an exact stage/objective, settlement and commodity binding")
    return {"questId": quest["id"], "stageId": binding["stageId"], "objectiveId": objective["id"],
            "marketId": binding["marketId"], "commodityId": binding["commodityId"]}


def objective_binding_rows(bindings):
    rows = bindings.get("objectives", {})
    if not isinstance(rows, dict):
        raise ValueError("quest objective bindings must be an object")
    for key, row in rows.items():
        if not isinstance(row, dict):
            raise ValueError(f"quest objective binding {key!r} must be an object")
    return rows.items()


def trade_quest_bindings(quests, bindings):
    objectives = {q["id"] + ":" + o["id"]: (q, o) for q in quests for o in q["objectives"]}
    result = []
    for key, binding in objective_binding_rows(bindings):
        if binding.get("consumer") == "local_consultation":
            continue
        if "consumer" in binding:
            if key not in objectives:
                raise ValueError("committed trade objective does not exist")
            result.append(committed_trade_binding(*objectives[key], binding))
    identities = [(row['questId'], row['stageId'], row['marketId'], row['commodityId']) for row in result]
    if len(identities) != len(set(identities)):
        raise ValueError("multiple objectives in one quest stage cannot share a committed trade binding")
    if len(result) > 64:
        raise ValueError("committed trade binding capacity exceeded")
    return result


def consultation_quest_bindings(quests, bindings):
    objectives = {q["id"] + ":" + o["id"]: (q, o) for q in quests for o in q["objectives"]}
    result = []
    expected = {"adapter", "consumer", "stageId", "providerId", "providerName", "locationId", "institutionId"}
    for key, binding in objective_binding_rows(bindings):
        if binding.get("consumer") != "local_consultation":
            continue
        if key not in objectives:
            raise ValueError("consultation objective does not exist")
        q, o = objectives[key]
        if (set(binding) != expected or binding["adapter"] != "domain_receipt"
                or o["conditionId"] != "quest_institution_satisfied"
                or any(not isinstance(binding.get(k), str) or not ID.fullmatch(binding[k])
                       for k in ("stageId", "providerId", "locationId", "institutionId"))
                or len(binding["providerId"]) > 56
                or not isinstance(binding["providerName"], str) or not 1 <= len(binding["providerName"]) <= 80
                or any(ord(c) < 32 for c in binding["providerName"])
                or o["entityRefs"] != [{"kind": "institution", "id": binding["institutionId"]}]
                or not any(s["id"] == binding["stageId"] and o["id"] in s["objectiveIds"] for s in q["stages"])):
            raise ValueError("consultation requires exact stage/objective, institution, provider and location binding")
        result.append({"questId": q["id"], "objectiveId": o["id"], **{k: binding[k] for k in
                       ("stageId", "providerId", "providerName", "locationId", "institutionId")}})
    if len(result) > 64 or len({row["providerId"] for row in result}) != len(result):
        raise ValueError("consultation providers must be unique and within capacity")
    return result


def validate_graphs(quests, bindings):
    trade_quest_bindings(quests, bindings)
    consultation_quest_bindings(quests, bindings)
    quest_ids = {q["id"] for q in quests}
    ids([q["id"] for q in quests])
    result, blockers = {}, []
    if quests and bindings.get("schemaVersion") != 1:
        raise ValueError("quest condition bindings schema is missing or unsupported")
    for q in quests:
        stages, objectives = q["stages"], q["objectives"]
        ids([s["id"] for s in stages]); ids([o["id"] for o in objectives])
        by_stage = {s["id"]: s for s in stages}
        if not 0 < len(stages) <= 16 or not 0 < len(objectives) <= 32 or q["initialStageId"] not in by_stage:
            raise ValueError(f"quest {q['id']}: missing initial stage or graph exceeds runtime bounds")
        used = []
        for s in stages:
            ids(s["objectiveIds"]); ids(s["nextStageIds"])
            if not s["objectiveIds"] or any(n not in by_stage for n in s["nextStageIds"]):
                raise ValueError(f"quest {q['id']}: omitted stage or empty objectives")
            used += s["objectiveIds"]
        if sorted(used) != sorted(o["id"] for o in objectives):
            raise ValueError(f"quest {q['id']}: objectives must belong to exactly one stage")
        reached = set()
        def visit(sid, path):
            if sid in path:
                raise ValueError(f"quest {q['id']}: cyclic stage graph")
            if sid in reached:
                return
            reached.add(sid)
            for nxt in by_stage[sid]["nextStageIds"]:
                visit(nxt, path | {sid})
        visit(q["initialStageId"], set())
        if reached != set(by_stage):
            raise ValueError(f"quest {q['id']}: unreachable stages")
        for p in q["prerequisites"]:
            if p.get("kind") != "quest_completed" or p.get("id") not in quest_ids or p["id"] == q["id"]:
                raise ValueError(f"quest {q['id']}: unsupported or missing prerequisite")
        ids([p["id"] for p in q["prerequisites"]])
        for o in objectives:
            binding = bindings.get("objectives", {}).get(q["id"] + ":" + o["id"], bindings.get("conditions", {}).get(o["conditionId"]))
            if not binding or binding.get("adapter") not in {"physical_visit", "domain_receipt", "research_unlocked"}:
                raise ValueError(f"quest {q['id']}/{o['id']}: unsupported condition binding {o['conditionId']}")
            refs = o["entityRefs"]
            if not refs or any(not ID.fullmatch(r["kind"]) or not ID.fullmatch(r["id"]) for r in refs):
                raise ValueError("invalid condition entity references")
            if binding["adapter"] == "physical_visit" and (len(refs) != 1 or refs[0]["kind"] != "settlement"):
                raise ValueError("physical_visit requires one settlement reference")
            if binding["adapter"] == "research_unlocked":
                if (o["conditionId"] != "quest_technology_satisfied" or len(refs) != 1
                        or refs[0]["kind"] != "technology" or binding.get("authority") != "player"):
                    raise ValueError("research unlock requires one player-owned technology objective")
            if binding["adapter"] == "domain_receipt":
                if "consumer" in binding:
                    if binding is not bindings.get("objectives", {}).get(q["id"] + ":" + o["id"]):
                        raise ValueError("committed trade consumer must be objective-specific")
                    if binding.get("consumer") != "local_consultation":
                        committed_trade_binding(q, o, binding)
                else:
                    if not binding.get("blocker"):
                        raise ValueError("uninstalled domain condition adapter requires an explicit integration blocker")
                    blockers.append({"questId": q["id"], "objectiveId": o["id"], "conditionId": o["conditionId"], "reason": binding["blocker"]})
            result[q["id"] + ":" + o["id"]] = binding["adapter"]
    return result, blockers


def emit_quests(quests, bindings, ws, reward_batches=None):
    lines = []
    def guidance(name, d):
        precision = d.get("precision", "hidden")
        # Preserve the authored stable point for earned-knowledge comparison.
        # The navigation/journal projection enforces precision before disclosure;
        # never infer a destination from objective condition entity references.
        destination = d.get("locationId", d.get("settlementId", ""))
        areas = json.dumps(d.get("searchAreas", []), separators=(",", ":")) if d.get("searchAreas") else ""
        return f'{name}=new QuestGuidance("{ws(precision)}","{ws(d.get("regionId", ""))}","{ws(destination)}","{ws(areas)}","{ids(d.get("requiredClueIds", []))}")'
    for n, q in enumerate(quests):
        name = f"quest{n}"
        j = q.get("journal", {})
        lines += [f'\tlet {name}=new RuntimeQuest("{ws(q["id"])}","{ws(q.get("title", q["id"]))}","{ws(q.get("campaign", {}).get("chainKind", "campaign"))}")',
                  f'\t{name}.giverId="{ws(j.get("giver", {}).get("id", ""))}"',
                  f'\t{name}.turnInId="{ws(j.get("turnIn", {}).get("id", ""))}"',
                  f'\t{name}.graph=new QuestGraph("{q["initialStageId"]}","{ids([p["id"] for p in q["prerequisites"]])}")']
        for s in q["stages"]:
            lines.append(f'\t{name}.graph.addStage(new QuestStage("{s["id"]}","{ws(s.get("title", s["id"]))}","{ids(s["objectiveIds"])}","{ids(s["nextStageIds"])}"))')
        for i, o in enumerate(q["objectives"]):
            obj = f"{name}objective{i}"
            refs = "".join(f'{r["kind"]}:{r["id"]}~' for r in sorted(o["entityRefs"], key=lambda r:(r["kind"], r["id"])))
            lines += [f'\tlet {obj}=new QuestObjective("{o["id"]}","{ws(o.get("description", ""))}","{o["conditionId"]}","{refs}","{bindings[q["id"] + ":" + o["id"]]}")', f'\t{name}.graph.addObjective({obj})']
            if o["id"] in j.get("destinations", {}):
                lines.append("\t" + guidance(obj + ".guidance", j["destinations"][o["id"]]))
        if j.get("turnInDestination"):
            lines.append("\t" + guidance(name + ".graph.turnInGuidance", j["turnInDestination"]))
        if reward_batches is not None and q["id"] in reward_batches:
            from quest_rewards import emit as emit_rewards
            lines += emit_rewards(name, q["id"], reward_batches[q["id"]], ws)
        # Existing bounded XP remains separately accountable from authored rewards.
        lines += [f'\t{name}.rewardExperience=100', f'\truntime.journal.register({name})']
    return lines
