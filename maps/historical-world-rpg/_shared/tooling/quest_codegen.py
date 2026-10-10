"""Validate and emit the live quest_event stage contract, without scenario rules."""
import json
import re

ID = re.compile(r"^[a-z][a-z0-9_]{0,63}$")


def ids(values):
    if not isinstance(values, list) or len(values) != len(set(values)) or any(not isinstance(x, str) or not ID.fullmatch(x) for x in values):
        raise ValueError("invalid or duplicate stable quest IDs")
    return "".join(x + "~" for x in values)


def validate_graphs(quests, bindings):
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
            if not binding or binding.get("adapter") not in {"physical_visit", "domain_receipt"}:
                raise ValueError(f"quest {q['id']}/{o['id']}: unsupported condition binding {o['conditionId']}")
            refs = o["entityRefs"]
            if not refs or any(not ID.fullmatch(r["kind"]) or not ID.fullmatch(r["id"]) for r in refs):
                raise ValueError("invalid condition entity references")
            if binding["adapter"] == "physical_visit" and (len(refs) != 1 or refs[0]["kind"] != "settlement"):
                raise ValueError("physical_visit requires one settlement reference")
            if binding["adapter"] == "domain_receipt":
                if not binding.get("blocker"):
                    raise ValueError("uninstalled domain condition adapter requires an explicit integration blocker")
                blockers.append({"questId": q["id"], "objectiveId": o["id"], "conditionId": o["conditionId"], "reason": binding["blocker"]})
            result[q["id"] + ":" + o["id"]] = binding["adapter"]
    return result, blockers


def emit_quests(quests, bindings, ws):
    lines = []
    def guidance(name, d):
        precision = d.get("precision", "hidden")
        # Non-exact knowledge never exposes the condition's exact target.
        destination = d.get("locationId", d.get("settlementId", "")) if precision == "exact" else ""
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
        # Existing bounded XP remains separately accountable from authored rewards.
        lines += [f'\t{name}.rewardExperience=100', f'\truntime.journal.register({name})']
    return lines
