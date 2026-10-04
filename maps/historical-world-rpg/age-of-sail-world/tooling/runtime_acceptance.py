#!/usr/bin/env python3
"""Source/compiled-text heuristics and binary structure checks for campaigns."""
from __future__ import annotations
import argparse, hashlib, json, re, struct, sys, zipfile
from pathlib import Path

PROJECT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(PROJECT/"tooling"))
from forsaken_kingdom_map import MapInfoError, validate_w3i_structure
MANIFEST=PROJECT/"scenario/runtime-integration.json"
REPORT_JSON=PROJECT/"reports/runtime-acceptance.json"; REPORT_MD=PROJECT/"reports/runtime-acceptance.md"
FORMAT="age_of_sail_runtime_integration_v1"
STAGES=("dataComplete","headlessSimulationComplete","runtimeIntegrated","playerFacingComplete","releaseValidated")
MANDATORY_SYSTEMS=frozenset({"campaign_launch","origin_selection","country_diplomacy","government_rewards","trade","army_fleet_control","city_capture","garrisons","administration","heroes","inventory_equipment","technology_institutions","quests_journal","treasures_discovery","religion","piracy","save_autosave_load","cross_map_travel","world_map","remote_management"})
COMPILED_TEXT_REQUIREMENTS={
 "campaign_launch":({"initializePlayableCampaignRuntime","installCommandRegistry"},set()),
 "origin_selection":({"registerOriginSelection","configureGeneratedOrigins","compatLoadPhysicalMap"},{"origin"}),
 "country_diplomacy":({"configureGeneratedCountryInteractions"},{"country","peace"}),
 "government_rewards":({"configureGeneratedCountryInteractions"},{"reward"}),
 "trade":({"registerPlayableTrade","configureGeneratedTrade"},{"trade"}),
 "army_fleet_control":({"initializeMilitarySettlementRuntime"},{"army"}),
 "city_capture":({"initializeMilitarySettlementRuntime"},{"army"}), "garrisons":({"initializeMilitarySettlementRuntime"},{"army"}),
 "administration":({"initializeMilitarySettlementRuntime"},{"army"}),
 "heroes":({"registerRpgRuntimeCommands"},{"roster","recruit"}),
 "inventory_equipment":({"registerRpgRuntimeCommands"},{"inventory","equip"}),
 "technology_institutions":({"configureGeneratedRpg","registerRpgRuntimeCommands"},{"technology","research"}),
 "quests_journal":({"registerRpgRuntimeCommands"},{"journal","track"}),
 "treasures_discovery":({"registerRpgRuntimeCommands"},{"interact"}),
 "religion":({"configureGeneratedReligion","registerReligion"},{"faith","convert"}),
 "piracy":({"configureGeneratedPiracy","registerPiracy"},{"piracy","prize-confirm"}),
 "save_autosave_load":({"initializePlayableCampaignRuntime"},{"save","load"}),
 "cross_map_travel":({"configureGeneratedPhysicalBoundaries","compatLoadPhysicalMap"},set()),
 "world_map":({"initializePlayableCampaignRuntime"},{"map"}),
 "remote_management":({"initializeMilitarySettlementRuntime"},{"army"})}
MAX_COMPILED_LUA_BYTES=16*1024*1024; MAX_LUA_LINE_BYTES=256*1024; MAX_LUA_STRING_BYTES=1024*1024
MAX_BOOTSTRAP_LUA_BYTES=512*1024
BOOTSTRAP_FORBIDDEN_REGISTRATIONS=("registerSettlement", "registerMarket", "registerForce", "registerReward", "registerHero", "registerQuest", "registerItem", "registerTechnology")

class RuntimeAcceptanceError(ValueError): pass

def _read(relative):
 p=PROJECT/relative
 if not p.is_file(): raise RuntimeAcceptanceError(f"missing integration evidence: {relative}")
 return p.read_text(encoding="utf-8",errors="replace")

def _evidence_ok(items,label):
 if not isinstance(items,list) or not items: raise RuntimeAcceptanceError(f"{label} requires evidence")
 failures=[]
 for item in items:
  if not isinstance(item,dict) or set(item)!={"path","contains"} or not item["contains"]: raise RuntimeAcceptanceError(f"{label} has malformed evidence")
  try: text=_read(item["path"])
  except RuntimeAcceptanceError as error: failures.append(str(error)); continue
  missing=[token for token in item["contains"] if token not in text]
  if missing: failures.append(f"{item['path']} lacks {', '.join(missing)}")
 return not failures,failures

def load_manifest(path=MANIFEST):
 try: data=json.loads(path.read_text(encoding="utf-8"))
 except (OSError,json.JSONDecodeError) as error: raise RuntimeAcceptanceError(f"cannot read runtime integration manifest: {error}") from error
 if data.get("format")!=FORMAT or data.get("formatVersion")!=1: raise RuntimeAcceptanceError("unsupported runtime integration manifest")
 systems=data.get("systems"); ids=[x.get("id") for x in systems or []]
 if not systems or len(ids)!=len(set(ids)) or any(not isinstance(x,str) or not x for x in ids): raise RuntimeAcceptanceError("runtime integration system IDs must be unique non-empty strings")
 return data

def audit_sources(path=MANIFEST):
 manifest=load_manifest(path); rows=[]; failures=[]
 for system in manifest["systems"]:
  required=system.get("releaseRequired") is True; simulation=system.get("simulationOnly") is True
  if required and simulation: raise RuntimeAcceptanceError(f"{system['id']}: required system cannot be simulation-only")
  checks={}; diagnostics=[]
  for stage,field in (("dataComplete","authority"),("headlessSimulationComplete","headlessVerification"),("runtimeIntegrated","runtime"),("playerFacingComplete","playerEntry")):
   checks[stage],missing=_evidence_ok(system.get(field),f"{system['id']}.{field}"); diagnostics+=missing
  persistence,missing=_evidence_ok(system.get("persistence"),f"{system['id']}.persistence"); diagnostics+=missing
  verified,missing=_evidence_ok(system.get("runtimeVerification"),f"{system['id']}.runtimeVerification"); diagnostics+=missing
  checks["runtimeIntegrated"] &= persistence and checks["dataComplete"] and checks["headlessSimulationComplete"]
  checks["playerFacingComplete"] &= checks["runtimeIntegrated"]
  checks["releaseValidated"]=False # only a built artifact may promote this
  if required and (not checks["playerFacingComplete"] or not verified): failures.append(f"{system['id']}: source runtime readiness is incomplete")
  rows.append({"id":system["id"],"releaseRequired":required,"simulationOnly":simulation,"stages":checks,"diagnostics":diagnostics})
 required_ids={x["id"] for x in manifest["systems"] if x.get("releaseRequired") is True}
 omitted=sorted(MANDATORY_SYSTEMS-required_ids)
 if omitted: failures.append(f"release-required systems are omitted or exempted: {omitted}")
 covered=set()
 for journey in manifest.get("smokeJourneys",[]):
  covered.update(journey.get("systems",[])); unknown=set(journey.get("systems",[]))-{x["id"] for x in manifest["systems"]}
  if unknown: failures.append(f"{journey.get('id','journey')}: unknown systems {sorted(unknown)}")
  ok,missing=_evidence_ok(journey.get("verification"),f"{journey.get('id')}.verification")
  if not ok: failures+=missing
 uncovered=sorted(required_ids-covered)
 if uncovered: failures.append(f"runtime smoke journeys omit required systems: {uncovered}")
 return {"format":"age_of_sail_runtime_acceptance_report_v2","status":"pass" if not failures else "fail","stages":list(STAGES),"systems":rows,"failures":failures,"evidenceLevel":"source_text_static_heuristic","executionStatus":"not_run","releaseValidationAuthority":"built W3N/W3X artifact gate","smokeJourneys":[x["id"] for x in manifest.get("smokeJourneys",[])]}

def render_markdown(report):
 lines=["# Playable runtime acceptance","",f"Result: **{report['status'].upper()}**","","Each stage below records source text found, including references to tests; this audit does not execute those tests or establish control-flow reachability. Built W3N/W3X structure and compiled-text checks are separate from real-client smoke.","","| System | Data | Headless | Runtime | Player-facing | Release validated |","|---|---:|---:|---:|---:|---:|"]
 for row in report["systems"]:
  stage=row["stages"]; mark=lambda key:"yes" if stage[key] else "artifact gate"
  lines.append(f"| `{row['id']}` | {mark('dataComplete')} | {mark('headlessSimulationComplete')} | {mark('runtimeIntegrated')} | {mark('playerFacingComplete')} | {mark('releaseValidated')} |")
 lines += ["","## Declared smoke journeys (source references only)",""]+[f"- `{x}`" for x in report["smokeJourneys"]]+["","## Failures",""]
 lines += [f"- {x}" for x in report["failures"]] if report["failures"] else ["No unresolved source-readiness failures. The RC packager supplies the built-artifact gate; real-client smoke is tracked separately."]
 return "\n".join(lines)+"\n"

def _lua_code_and_strings(script, string_tokens=False):
 strings=[]; out=[]; i=0
 while i<len(script):
  if script.startswith("--[[",i):
   end=script.find("]]",i+4); i=len(script) if end<0 else end+2; out.append(" "); continue
  if script.startswith("--",i):
   end=script.find("\n",i+2); i=len(script) if end<0 else end; out.append(" "); continue
  if script[i] in "'\"":
   quote=script[i]; j=i+1; value=[]
   while j<len(script) and script[j]!=quote:
    if script[j]=="\\" and j+1<len(script): value.extend(script[j:j+2]); j+=2
    else: value.append(script[j]); j+=1
   out.append(f"__literal_{len(strings)}__" if string_tokens else " "); strings.append("".join(value)); i=min(len(script),j+1); continue
  out.append(script[i]); i+=1
 return "".join(out),strings

def _compiled_call_evidence(text):
 # The pinned compiler renames functions, but supplies source-call locations as
 # the final argument of actual calls. Associate those with defined callees;
 # a diagnostic string on its own must never count as a production call.
 code,strings=_lua_code_and_strings(text, string_tokens=True)
 definitions=set(re.findall(r"\bfunction\s+(\w+)\s*\(",code))
 code=re.sub(r"\bfunction\s+[A-Za-z_]\w*\s*\(","function (",code)
 calls=set(re.findall(r"(?<![\w.])([A-Za-z_]\w*)\s*\(",code))
 registrations=set()
 registry_aliases=set(re.findall(r"\bCommandRegistry\.CommandRegistry_register\s*=\s*(\w+)",code)) & definitions
 def literal(token):
  match=re.fullmatch(r"__literal_(\d+)__",token.strip())
  return strings[int(match[1])] if match else None
 for match in re.finditer(r"\b(\w+)\s*\(([^()\n]*)\)",code):
  callee,args=match[1],match[2].split(',')
  trace=literal(args[-1])
  if callee in definitions and trace:
   origin=re.fullmatch(r"when calling (\w+) in [\w]+, line \d+",trace)
   if origin: calls.add(origin[1])
  if callee in registry_aliases and len(args)>1:
   command=literal(args[1])
   if command: registrations.add(command)
 for match in re.finditer(r"(?:\.|:)register\s*\(\s*(__literal_\d+__)",code):
  registrations.add(literal(match[1]))
 return calls,registrations

def verify_compiled_script(script,path=MANIFEST):
 raw=script if isinstance(script,bytes) else script.encode(); text=raw.decode("utf-8",errors="replace"); failures=[]
 if len(raw)>MAX_COMPILED_LUA_BYTES: failures.append(f"compiled Lua exceeds {MAX_COMPILED_LUA_BYTES} byte budget")
 longest=max((len(x.encode()) for x in text.splitlines()),default=0)
 if longest>MAX_LUA_LINE_BYTES: failures.append(f"compiled Lua line exceeds {MAX_LUA_LINE_BYTES} byte budget")
 code,strings=_lua_code_and_strings(text)
 if max((len(x.encode()) for x in strings),default=0)>MAX_LUA_STRING_BYTES: failures.append(f"compiled Lua string exceeds {MAX_LUA_STRING_BYTES} byte budget")
 calls,registrations=_compiled_call_evidence(text)
 for sid in sorted(x["id"] for x in load_manifest(path)["systems"] if x.get("releaseRequired")):
  required_calls,required_commands=COMPILED_TEXT_REQUIREMENTS.get(sid,(set(),set()))
  if not required_calls: failures.append(f"{sid}: no compiled-text requirement is defined"); continue
  missing=sorted(required_calls-calls); commands=sorted(required_commands-registrations)
  if missing: failures.append(f"{sid}: production calls absent: {', '.join(missing)}")
  if commands: failures.append(f"{sid}: production command registrations absent: {', '.join(commands)}")
 if not re.search(r"\bfunction\s+(?:main|config)\s*\(",code): failures.append("compiled Lua has no Warcraft main/config entry point")
 return {"status":"pass" if not failures else "fail","failures":failures,"evidenceLevel":"compiled_text_static_heuristic","metrics":{"compiledLuaBytes":len(raw),"longestLineBytes":longest,"callNameMatches":len(calls),"commandRegistrations":len(registrations)}}

def verify_compiled_bootstrap(script):
 raw=script if isinstance(script,bytes) else script.encode(); text=raw.decode("utf-8",errors="replace")
 failures=[]
 calls,_=_compiled_call_evidence(text)
 text,_=_lua_code_and_strings(text)
 if len(raw)>MAX_BOOTSTRAP_LUA_BYTES: failures.append(f"bootstrap compiled Lua exceeds {MAX_BOOTSTRAP_LUA_BYTES} byte budget")
 for token in BOOTSTRAP_FORBIDDEN_REGISTRATIONS:
  if token in calls: failures.append(f"bootstrap contains regional registration: {token}")
 # A BJ assignment alone is not a handoff: EndGame does not consume it.
 # Require the destination-consuming native, whether inside a renamed helper
 # or inlined at its call site. This is still textual, not reachability proof.
 change_level=re.search(r"\bChangeLevel\s*\(",text)
 destination_effect=change_level; end_game=re.search(r"\b(?:ChangeLevel|EndGame)\s*\(",text)
 if not destination_effect: failures.append("bootstrap compiled Lua does not select a campaign destination")
 if not end_game: failures.append("bootstrap compiled Lua does not end the selector map")
 if destination_effect and end_game and destination_effect.start()>end_game.start(): failures.append("bootstrap ends before selecting the destination map")
 if "TimerStart" not in text or "showPage" not in text: failures.append("bootstrap does not defer and open origin selection")
 return {"status":"pass" if not failures else "fail","failures":failures,"evidenceLevel":"compiled_text_static_heuristic","metrics":{"compiledLuaBytes":len(raw)}}

def _archive_read(path,name):
 if zipfile.is_zipfile(path):
  with zipfile.ZipFile(path) as archive: return archive.read(name)
 sys.path.insert(0,str(PROJECT.parent/"_shared/tooling")); from warcraft_campaign import MpqReader
 return MpqReader(path).read(name)

def inspect_built_map(path,expected_map_id=None,bootstrap=None):
 try:
  script=_archive_read(path,"war3map.lua"); w3e=_archive_read(path,"war3map.w3e"); wpm=_archive_read(path,"war3map.wpm"); units=_archive_read(path,"war3mapUnits.doo")
  runtime=json.loads(_archive_read(path,"runtime/scenario-runtime.json")); physical=json.loads(_archive_read(path,"runtime/physical-map.json")); w3i=_archive_read(path,"war3map.w3i")
 except (KeyError,OSError,ValueError,json.JSONDecodeError) as error: raise RuntimeAcceptanceError(f"built map is missing or has invalid required content: {error}") from error
 compiled=verify_compiled_bootstrap(script) if bootstrap is True else verify_compiled_script(script)
 failures=list(compiled["failures"]); tw=th=objects=0
 try:
  offset=13; ground=struct.unpack_from("<I",w3e,offset)[0]; offset+=4+ground*4; cliffs=struct.unpack_from("<I",w3e,offset)[0]; offset+=4+cliffs*4
  tw,th=struct.unpack_from("<II",w3e,offset); pw,ph=struct.unpack_from("<II",wpm,8); objects=struct.unpack_from("<I",units,12)[0]
  cells=w3e[offset+16:]; paths=wpm[16:]
  if w3e[:8]!=b"W3E!"+struct.pack("<I",11) or not 1<=ground<=16 or not 0<=cliffs<=16 or len(cells)!=tw*th*7 or tw<3 or th<3: failures.append("terrain binary is malformed")
  if wpm[:8]!=b"MP3W\0\0\0\0" or (pw,ph)!=((tw-1)*4,(th-1)*4) or len(paths)!=pw*ph: failures.append("pathing binary does not match terrain")
  if units[:12]!=b"W3do"+struct.pack("<II",8,11) or objects<1 or b"sloc" not in units: failures.append("map has no valid player spawn representation")
  vertices={cells[i:i+7] for i in range(0,len(cells),7)}
  if bootstrap is not True and (len(vertices)<2 or len(set(paths))<2): failures.append("physical terrain/pathing is blank or placeholder-only")
 except struct.error: failures.append("terrain/pathing/object binary is truncated")
 map_id=physical.get("physicalMapId")
 if expected_map_id is not None and map_id!=expected_map_id: failures.append(f"physical-map identity {map_id!r} does not match {expected_map_id!r}")
 if bootstrap is not None and physical.get("bootstrap") is not bool(bootstrap): failures.append("physical-map bootstrap identity is inconsistent")
 if bootstrap is not True and (not runtime.get("ids",{}).get("polities") or not runtime.get("regionalGeography")): failures.append("compiled runtime data is not populated")
 if bootstrap is True and (runtime.get("settlementDefinitions") or runtime.get("physicalBoundaries")): failures.append("bootstrap runtime contains regional gameplay records")
 try: info=validate_w3i_structure(w3i)
 except MapInfoError as error: failures.append(str(error))
 else:
  left,right,bottom,top=info["cameraComplements"]
  expected=(tw-1-left-right,th-1-bottom-top)
  if (info["playableWidth"],info["playableHeight"])!=expected: failures.append("W3I playable dimensions and camera bounds do not match terrain")
 return {"status":"pass" if not failures else "fail","failures":failures,"mapId":map_id,"bootstrap":physical.get("bootstrap"),"compiledScript":compiled,"executionStatus":"not_run","terrainSha256":hashlib.sha256(w3e).hexdigest(),"pathingSha256":hashlib.sha256(wpm).hexdigest(),"objectCount":objects,"width":tw-1 if tw else 0,"height":th-1 if th else 0}

def verify_built_map(path,expected_map_id=None,bootstrap=None):
 result=inspect_built_map(path,expected_map_id,bootstrap)
 if result["failures"]: raise RuntimeAcceptanceError("; ".join(result["failures"]))
 return result

def verify_campaign_maps(maps):
 rows=[]; failures=[]
 for path,map_id,bootstrap in maps:
  row=inspect_built_map(path,map_id,bootstrap); rows.append(row); failures += [f"{map_id}: {x}" for x in row["failures"]]
 ids=[x["mapId"] for x in rows]
 if len(ids)!=len(set(ids)): failures.append("physical-map identities are not unique")
 if sum(bool(x["bootstrap"]) for x in rows)!=1: failures.append("campaign must have exactly one bootstrap map")
 regional=[x for x in rows if not x["bootstrap"]]
 if not regional: failures.append("bootstrap records destinations but campaign contains no regional map")
 if len(regional)>1 and len({(x["terrainSha256"],x["pathingSha256"]) for x in regional})==1: failures.append("regional maps use identical placeholder terrain/pathing")
 return {"status":"pass" if not failures else "fail","failures":failures,"maps":rows}

def main(argv=None):
 parser=argparse.ArgumentParser(description=__doc__); parser.add_argument("--write",action="store_true"); args=parser.parse_args(argv); report=audit_sources()
 encoded=json.dumps(report,indent=2,sort_keys=True)+"\n"; human=render_markdown(report)
 if args.write: REPORT_JSON.parent.mkdir(parents=True,exist_ok=True); REPORT_JSON.write_text(encoded); REPORT_MD.write_text(human)
 elif not REPORT_JSON.is_file() or REPORT_JSON.read_text()!=encoded or not REPORT_MD.is_file() or REPORT_MD.read_text()!=human: raise RuntimeAcceptanceError("runtime-acceptance reports are missing or stale; run with --write")
 print(json.dumps({"status":report["status"],"failures":len(report["failures"])},sort_keys=True)); return 0 if report["status"]=="pass" else 1
if __name__=="__main__": raise SystemExit(main())
