#!/usr/bin/env python3
"""Deterministic Phase 8 whole-game release-candidate content audit."""
from __future__ import annotations
import argparse, json, re
from collections import Counter, defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
REPORT=ROOT/"reports/phase8-content-coverage.json"; HUMAN_REPORT=ROOT/"reports/phase8-content-coverage.md"
YEARS=(1450,1550,1650,1750,1820)
REGIONS=("europe","africa","middle_east_india","southeast_asia","east_asia","americas_caribbean","pacific")
REGION_FILES={r:r.replace("_","-") for r in REGIONS}

class AuditError(ValueError): pass
def load(relative): return json.loads((ROOT/relative).read_text())
def require(condition,message,failures):
    if not condition: failures.append(message)
def year_of(value): return int(value[:4]) if isinstance(value,str) else int(value)
def active(window,year):
    return year_of(window.get("startDate",window.get("historicalStartYear",1450)))<=year<=year_of(window.get("endDate",window.get("historicalEndYear",1820)))

def build():
    failures=[]
    world=load("scenario/world/world.json"); land=load("scenario/rosters/phase8-land-rosters.json")
    land_report=load("scenario/rosters/reports/phase8-land-coverage.json"); naval=load("scenario/naval/phase8.json")
    naval_report=load("scenario/naval/reports/coverage.json"); chars=load("scenario/characters/phase8.json")
    military_breadth=load("scenario/rosters/reports/release-military-breadth.json")
    char_report=load("scenario/characters/reports/coverage.json"); goods_report=load("scenario/economy/reports/global-goods-validation.json")
    progression=load("scenario/progression/catalog.json"); events=load("scenario/historical-events.json")
    quests=load("scenario/campaign-quests.json"); treasure=load("scenario/treasures/age-of-sail.json")
    assets=load("scenario/assets/reports/phase6-asset-audit.json"); budgets=load("scenario/benchmarks/reports/final-measurements.json")
    settlement_integration=load("reports/settlement-integration.json")

    polity_region={}
    for region,filename in REGION_FILES.items():
        for polity in load(f"scenario/politics/{filename}-1450.json")["polities"]:
            # Border powers can intentionally occur in two regional political
            # source slices; the first slice is the stable reporting home.
            polity_region.setdefault(polity["id"],region)
    world_polities={p["id"] for p in world["polities"]}
    require(world_polities<=set(polity_region),"world contains polity without authoritative region",failures)

    layers=Counter(a.get("rosterLayer","pre_phase8") for a in land["archetypes"])
    require(all(layers[x] for x in ("common","regional","polity","elite")),"land roster is missing a required layer",failures)
    require(land_report.get("status")=="complete","land subsystem coverage report is not complete",failures)
    land_eras={}
    for year in YEARS:
        rows=[a for a in land["archetypes"] if active(a.get("availability",{}),year)]
        land_eras[str(year)]={"activeArchetypes":len(rows),"layers":dict(sorted(Counter(a["rosterLayer"] for a in rows).items()))}
    require(all(land_eras[str(y)]["activeArchetypes"] for y in YEARS),"land roster has an empty era snapshot",failures)

    naval_roles={k:len(v) for k,v in sorted(naval_report["families"].items()) if k in {"merchant","transport","sailing_warship","line_of_battle","coastal","riverine"}}
    require(all(naval_roles.get(x,0) for x in ("merchant","transport","sailing_warship")),"naval merchant/transport/warship coverage is incomplete",failures)
    require(all(x.get("region") and x.get("reason") for x in naval.get("exceptions",[])),"naval sparse-case allowlist has an unexplained entry",failures)
    require(military_breadth.get("status")=="pass","release military-breadth report is not complete",failures)
    require(350<=military_breadth.get("counts",{}).get("playerFacing",0)<=550,"release military breadth is outside the 350-500+ planning range",failures)
    require(set(military_breadth.get("coverage",{}).get("regions",[]))==set(REGIONS),"military breadth omits a major region",failures)
    require(tuple(military_breadth.get("coverage",{}).get("years",[]))==YEARS,"military breadth omits an era fixture",failures)

    econ_regions={k.replace("-","_"):v for k,v in goods_report["regionalCoverage"].items()}
    require(set(econ_regions)==set(REGIONS),"economy report does not cover every major region",failures)
    require(not any(goods_report["diagnostics"].values()),"economy report contains unresolved or unreachable goods",failures)
    require(goods_report["settlements"]>0,"economy report has no authored settlement identities",failures)

    nodes=progression["technologies"]+progression["institutions"]
    progression_eras={str(y):sum(year_of(n["preferredYear"])<=y for n in nodes) for y in YEARS}
    new_after_1450=sum(year_of(n["preferredYear"])>1450 for n in nodes)
    require(new_after_1450>=len(nodes)//2,"progression is materially front-loaded at 1450",failures)
    require(all(n.get("unlocks") is not None for n in nodes),"technology or institution omits unlock metadata",failures)
    event_regions=Counter(e["region"].replace("-","_") for e in events["events"])
    event_eras={str(y):sum(year_of(e["date"])<=y for e in events["events"]) for y in YEARS}
    require(all(event_regions[r] for r in REGIONS),"historical events omit a major region",failures)
    require(max(year_of(e["date"]) for e in events["events"])>=1800,"historical events do not reach the final campaign era",failures)

    authored_ids=[c["id"] for c in chars["characters"]]; projected_ids=[c["id"] for c in world.get("characters",[])]
    require(len(authored_ids)==len(set(authored_ids)) and len(projected_ids)==len(set(projected_ids)),"authoritative character is physically duplicated",failures)
    placeholder=re.compile(r"(?:^|[_ -])(todo|tbd|dummy|placeholder|test[_ -]?name)(?:$|[_ -])",re.I)
    leaked=[c.get("displayName","") for c in chars["characters"] if placeholder.search(c.get("displayName",""))]
    require(not leaked,f"placeholder character names leaked: {leaked}",failures)
    require(set(char_report["byRegion"])==set(REGIONS),"character report omits a major region",failures)
    require(all(char_report["byRegion"][r]>=5 for r in REGIONS),"a major region has materially thin character coverage",failures)
    require(char_report["byRole"].get("commander",0) and char_report["byRole"].get("admiral",0),"commander or admiral coverage is empty",failures)
    require(char_report["personalQuestCount"]>=char_report["characterCount"],"an authored historical character lacks personal quest coverage",failures)

    quest_regions=defaultdict(Counter); quest_characters=Counter()
    for quest in quests["quests"]:
        quest_regions[quest["region"]][quest["chainKind"]]+=1
        for stage in quest["stages"]:
            for objective in stage["objectives"]:
                for kind,ident in objective["refs"]:
                    if kind=="character": quest_characters[ident]+=1
    candidate_region={x["id"]:x["regionId"] for x in treasure["candidateLocations"]}; treasure_regions=Counter(); treasure_kinds=Counter()
    for item in treasure["treasures"]:
        treasure_kinds[item["kind"]]+=1
        require(all(item.get(k) for k in ("clueIds","guardIds","hazardIds","encounterIds")),f"treasure lacks discovery content: {item['id']}",failures)
        for region in {candidate_region[x] for x in item["candidateLocationIds"]}: treasure_regions[region]+=1
    for region in REGIONS:
        require(quest_regions[region]["regional"]>=2,f"thin regional quest coverage: {region}",failures)
        require(quest_regions[region]["personal"]>=1,f"thin personal quest coverage: {region}",failures)
        require(treasure_regions[region]>=3,f"thin treasure coverage: {region}",failures)
    require(quest_regions["global"]["cross_region"] and quest_regions["global"]["long"],"cross-region or campaign-spanning quest coverage is empty",failures)

    settlement_count=len(world["settlements"])
    require(settlement_integration["status"]=="pass" and settlement_integration["settlementCount"]==settlement_count,"release-scale settlement integration report is incomplete",failures)
    require(not settlement_integration["inertSettlements"] and not settlement_integration["unresolvedReferences"],"settlement integration contains inert or unresolved content",failures)
    administration={"settlementsResolved":settlement_integration["settlementCount"],"newlyCapturedResolution":"deterministic_acting_official","generatedIdentity":"culture_name_pool_plus_persistent_character_id","authoritativePhysicalDuplicates":settlement_integration["duplicatedCharacters"]}
    defense={"settlementsResolved":settlement_integration["settlementCount"],"defaultProfile":"local_militia","captureResolution":"retire_then_rebuild_from_abstract_state","reinforcementCosts":"positive_manpower_supply_and_time"}
    require(assets["gates"]["allMaterialPlaceholdersResolved"],"Phase 6 asset audit has unresolved material placeholders",failures)
    require(assets.get("status")=="pass" and all(assets["gates"].values()),"Phase 6 asset audit has an unapproved release-facing asset",failures)
    require(all(not row.get("correctnessFailures") for row in budgets.values()),"Phase 7 benchmark has correctness failures",failures)

    major=sorted(naval["majorPowers"]); assigned={p for row in land["assignments"] for p in row["polityIds"]}
    identity={p:{"region":polity_region[p],"landSpecific":p in assigned,"navalSpecific":any(p in r["polityIds"] for r in naval["regions"]),"historicalCharacters":sum(c.get("allegiancePolityId")==p for c in chars["characters"])} for p in major}
    for polity,row in identity.items():
        require(any(bool(row[k]) for k in ("landSpecific","navalSpecific","historicalCharacters")),f"materially thin major-power identity: {polity}",failures)

    region_rows={}
    for region in REGIONS:
        region_rows[region]={"polities":sum(r==region for r in polity_region.values()),"land":"common_and_regional","navalFamilies":sum(1 for x in naval["regions"] if region in x["id"] or (region=="middle_east_india" and x["id"] in {"mediterranean","indian_ocean"})),"goods":econ_regions[region],"events":event_regions[region],"characters":char_report["byRegion"][region],"regionalQuests":quest_regions[region]["regional"],"personalQuests":quest_regions[region]["personal"],"treasures":treasure_regions[region]}
    thin=[m for m in failures if "thin" in m or "omit" in m or "missing" in m]
    return {"schemaVersion":2,"status":"pass" if not failures else "fail","campaignYears":[1450,1820],"snapshotYears":list(YEARS),
      "policy":{"minorPolitiesMayShareRegionalContent":True,"majorPowersRequireAdditionalIdentity":True,"sparseCasesRequireExplicitReason":True,"playerQaRequired":False},
      "regions":region_rows,"majorPowers":identity,"militaryBreadth":military_breadth["counts"],
      "eras":{str(y):{"landArchetypes":land_eras[str(y)]["activeArchetypes"],"landLayers":land_eras[str(y)]["layers"],"progressionNodesAvailable":progression_eras[str(y)],"historicalEventsOccurred":event_eras[str(y)]} for y in YEARS},
      "categories":{"land":{"catalogArchetypes":land_report["catalog"]["landArchetypes"],"layers":dict(sorted(layers.items())),"requiredRoles":land_report["requiredRoles"]},"naval":{"archetypes":naval_report["counts"]["navalArchetypes"],"roles":naval_roles,"sparseAllowlist":naval["exceptions"]},"governance":{"representedPolities":len(world_polities),**administration},"garrisons":defense,"economy":{"goods":goods_report["catalogueGoods"],"settlementsResolved":settlement_count,"authoredSettlementIdentities":goods_report["settlements"],"fallback":"regional_defaults","tradeRoutes":goods_report["tradeRoutes"],"diagnostics":goods_report["diagnostics"]},"progression":{"technologies":len(progression["technologies"]),"institutions":len(progression["institutions"]),"newAfter1450":new_after_1450},"events":{"total":len(events["events"]),"byRegion":dict(sorted(event_regions.items()))},"characters":{"total":char_report["characterCount"],"roles":char_report["byRole"],"personalQuests":char_report["personalQuestCount"]},"quests":{"total":len(quests["quests"]),"byType":dict(sorted(Counter(q["chainKind"] for q in quests["quests"]).items())),"charactersWithObjectives":dict(sorted(quest_characters.items()))},"treasures":{"total":len(treasure["treasures"]),"byKind":dict(sorted(treasure_kinds.items()))},"assetsAndBudgets":{"phase6AssetsApproved":not any("Phase 6" in x for x in failures),"phase7CorrectnessClean":not any("Phase 7" in x for x in failures)}},"thinContentFlags":thin,"failures":failures}

def markdown(report):
    lines=["# Phase 8 full-content audit","",f"Result: **{report['status'].upper()}**","","This deterministic release-candidate gate audits regional and era breadth; it does not substitute a global raw-count threshold.","","## Regional coverage","","| Region | Polities | Goods | Events | Characters | Regional quests | Personal quests | Treasures |","|---|---:|---:|---:|---:|---:|---:|---:|"]
    for region,row in report["regions"].items(): lines.append(f"| {region} | {row['polities']} | {row['goods']} | {row['events']} | {row['characters']} | {row['regionalQuests']} | {row['personalQuests']} | {row['treasures']} |")
    lines += ["","## Era snapshots","","| Year | Active land archetypes | Progression nodes | Events occurred |","|---:|---:|---:|---:|"]
    for year,row in report["eras"].items(): lines.append(f"| {year} | {row['landArchetypes']} | {row['progressionNodesAvailable']} | {row['historicalEventsOccurred']} |")
    lines += ["","## Gate findings",""]
    if report["failures"]: lines.extend(f"- FAIL: {x}" for x in report["failures"])
    else: lines += ["- No materially thin major region, major power, era, or gameplay category was found.","- Every settlement resolves administration, generated official identity, capture handling, and local defense from persistent authoritative state.","- Phase 6 asset approval and Phase 7 correctness/budget inputs are clean.","- Minor-polity common/regional sharing and all sparse naval cases follow explicit policy."]
    return "\n".join(lines)+"\n"

def main():
    parser=argparse.ArgumentParser(); parser.add_argument("--write",action="store_true",help="refresh both checked-in reports"); args=parser.parse_args()
    report=build(); human=markdown(report)
    if report["failures"]: raise AuditError("Phase 8 audit failed:\n- " + "\n- ".join(report["failures"]))
    if args.write: REPORT.parent.mkdir(exist_ok=True); REPORT.write_text(json.dumps(report,indent=2)+"\n"); HUMAN_REPORT.write_text(human)
    elif not REPORT.exists() or json.loads(REPORT.read_text())!=report or not HUMAN_REPORT.exists() or HUMAN_REPORT.read_text()!=human: raise SystemExit("Phase 8 reports are stale; run tooling/phase8_content_coverage.py --write")
    print(f"Phase 8 full-content audit passed for {len(report['regions'])} regions and {len(report['eras'])} era snapshots")
if __name__=="__main__": raise SystemExit(main())
