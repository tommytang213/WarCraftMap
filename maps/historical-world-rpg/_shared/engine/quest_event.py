"""Scenario-neutral deterministic quest, event, and exploration runtime."""
from __future__ import annotations
import copy, re
from dataclasses import dataclass
from typing import Mapping

STATE_VERSION=1
QUEST_EVENT_WORLD_STATE_KEY="questEventState"
_ID=re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")
_TERMINAL={"completed","failed","cancelled"}
class QuestEventError(ValueError): pass

@dataclass(frozen=True)
class RuntimeEvent:
 sequence:int; kind:str; entity_kind:str; entity_id:str; detail:Mapping
 def to_dict(self): return {"sequence":self.sequence,"kind":self.kind,"entityKind":self.entity_kind,"entityId":self.entity_id,"detail":copy.deepcopy(dict(self.detail))}

class NullScenarioExtensions:
 def evaluate_condition(self,condition_id,entity_refs,snapshot,context): raise QuestEventError(f"no scenario condition evaluator for {condition_id!r}")
 def apply_outcomes(self,outcomes,snapshot,context):
  if outcomes: raise QuestEventError(f"no scenario outcome handler for {outcomes[0]['outcomeId']!r}")
  return snapshot

def _id(v,c):
 if not isinstance(v,str) or not _ID.fullmatch(v): raise QuestEventError(f"{c}: invalid stable ID {v!r}")
 return v
def _index(v,c):
 if not isinstance(v,list): raise QuestEventError(f"{c}: must be an array")
 r={}
 for x in v:
  if not isinstance(x,Mapping): raise QuestEventError(f"{c}: entries must be objects")
  i=_id(x.get("id"),f"{c}.id")
  if i in r: raise QuestEventError(f"{c}: duplicate ID {i!r}")
  r[i]=copy.deepcopy(dict(x))
 return r
def _refs(v,c):
 if not isinstance(v,list): raise QuestEventError(f"{c}: entityRefs must be an array")
 r=[]
 for n,x in enumerate(v):
  if not isinstance(x,Mapping): raise QuestEventError(f"{c}.entityRefs[{n}]: must be an object")
  r.append({"kind":_id(x.get("kind"),c),"id":_id(x.get("id"),c)})
 return tuple(r)

class QuestEventRuntime:
 def __init__(self,definitions,*,extensions=None,authoritative_state=None,max_transitions=10000):
  if not isinstance(definitions,Mapping): raise QuestEventError("definitions must be an object")
  self.quests=_index(definitions.get("quests",[]),"quests"); self.events=_index(definitions.get("events",[]),"events"); self.discoveries=_index(definitions.get("discoveries",[]),"discoveries")
  self.ext=extensions or NullScenarioExtensions(); self.limit=max_transitions; self._emitted=[]; self._representations={}
  if isinstance(max_transitions,bool) or not isinstance(max_transitions,int) or max_transitions<1: raise QuestEventError("max_transitions must be positive")
  self._validate_definitions()
  self.state={"schemaVersion":STATE_VERSION,"quests":[{"id":i,"status":"inactive","stageId":None,"reachedStageIds":[],"completedObjectiveIds":[]} for i in sorted(self.quests)],"events":[{"id":i,"occurrences":0} for i in sorted(self.events)],"discoveries":[{"id":i,"discovered":False} for i in sorted(self.discoveries)],"pendingTriggers":[],"processedTriggerKeys":[],"deliveredOutcomeKeys":[],"nextSequence":1,"externalState":copy.deepcopy(dict(authoritative_state or {}))}
 def _validate_definitions(self):
  for qid,q in self.quests.items():
   q["_stages"]=_index(q.get("stages",[]),f"quest {qid}.stages"); q["_objectives"]=_index(q.get("objectives",[]),f"quest {qid}.objectives")
   if q.get("initialStageId") not in q["_stages"]: raise QuestEventError(f"quest {qid}: missing initial stage")
   used=set()
   for sid,s in q["_stages"].items():
    for o in s.get("objectiveIds",[]):
     if o not in q["_objectives"] or o in used: raise QuestEventError(f"quest {qid}: invalid objective {o!r}")
     used.add(o)
    for n in s.get("nextStageIds",[]):
     if n not in q["_stages"] or n==sid: raise QuestEventError(f"quest {qid}: invalid transition")
   if used!=set(q["_objectives"]): raise QuestEventError(f"quest {qid}: objectives must be assigned exactly once")
  for eid,e in self.events.items():
   if not isinstance(e.get("repeatable"),bool): raise QuestEventError(f"event {eid}: repeatable must be boolean")
   e["_triggers"]=_index(e.get("triggers",[]),f"event {eid}.triggers")
   if not e["_triggers"]: raise QuestEventError(f"event {eid}: no triggers")
  for owner,r in [("quest",x) for x in self.quests.values()]+[("event",x) for x in self.events.values()]+[("discovery",x) for x in self.discoveries.values()]:
   for p in r.get("prerequisites",[]): self._check_pre(p,owner)
   for o in r.get("outcomes",[]): self._check_out(o,owner)
 def _check_pre(self,p,owner):
  if not isinstance(p,Mapping): raise QuestEventError(f"{owner}: malformed prerequisite")
  k=p.get("kind")
  if k=="quest_completed" and p.get("id") not in self.quests: raise QuestEventError(f"{owner}: missing quest reference")
  elif k=="event_occurred" and p.get("id") not in self.events: raise QuestEventError(f"{owner}: missing event reference")
  elif k=="quest_stage_reached":
   q=self.quests.get(p.get("id"))
   if q is None or p.get("stageId") not in q["_stages"]: raise QuestEventError(f"{owner}: missing stage reference")
  elif k=="scenario_condition": _id(p.get("conditionId"),owner); _refs(p.get("entityRefs",[]),owner)
  elif k not in {"quest_completed","event_occurred"}: raise QuestEventError(f"{owner}: unsupported prerequisite {k!r}")
 def _check_out(self,o,owner):
  if not isinstance(o,Mapping): raise QuestEventError(f"{owner}: malformed outcome")
  _id(o.get("id"),owner); k=o.get("kind")
  if k=="start_quest" and o.get("questId") not in self.quests: raise QuestEventError(f"{owner}: missing quest")
  elif k=="advance_quest":
   q=self.quests.get(o.get("questId")); a=o.get("fromStageId"); b=o.get("toStageId")
   if q is None or a not in q["_stages"] or b not in q["_stages"][a].get("nextStageIds",[]): raise QuestEventError(f"{owner}: invalid advancement")
  elif k=="emit_event":
   e=self.events.get(o.get("eventId"))
   if e is None or o.get("repeat") is True and not e["repeatable"]: raise QuestEventError(f"{owner}: invalid emitted event")
  elif k=="scenario_outcome": _id(o.get("outcomeId"),owner); _refs(o.get("entityRefs",[]),owner)
  elif k not in {"start_quest","advance_quest","emit_event"}: raise QuestEventError(f"{owner}: unsupported outcome {k!r}")
 def _maps(self,s): return ({x["id"]:x for x in s["quests"]},{x["id"]:x for x in s["events"]},{x["id"]:x for x in s["discoveries"]})
 def _notify(self,out,s,k,ek,eid,**detail): out.append(RuntimeEvent(s["nextSequence"],k,ek,eid,detail)); s["nextSequence"]+=1
 def _condition(self,r,s,c):
  snap=copy.deepcopy(s); before=copy.deepcopy(snap)
  try: answer=self.ext.evaluate_condition(r["conditionId"],_refs(r.get("entityRefs",[]),r["conditionId"]),snap,copy.deepcopy(dict(c)))
  except QuestEventError: raise
  except Exception as x: raise QuestEventError(f"condition {r['conditionId']!r} failed: {x}") from x
  if snap!=before: raise QuestEventError("condition evaluator mutated snapshot")
  if not isinstance(answer,bool): raise QuestEventError("condition evaluator must return boolean")
  return answer
 def _prereqs(self,r,s,c):
  qs,es,_=self._maps(s)
  for p in r.get("prerequisites",[]):
   k=p["kind"]
   if k=="quest_completed" and qs[p["id"]]["status"]!="completed": return False
   if k=="event_occurred" and not es[p["id"]]["occurrences"]: return False
   if k=="quest_stage_reached" and p["stageId"] not in qs[p["id"]]["reachedStageIds"]: return False
   if k=="scenario_condition" and not self._condition(p,s,c): return False
  return True
 def _tx(self,fn):
  candidate=copy.deepcopy(self.state); emitted=[]; fn(candidate,emitted); self.validate_snapshot(candidate); self.state=candidate; self._emitted.extend(emitted); return tuple(emitted)
 def activate_quest(self,qid,*,context=None): return self._tx(lambda s,e:self._activate(s,e,qid,context or {}))
 def _activate(self,s,out,qid,c):
  q=self.quests.get(qid); qs=self._maps(s)[0].get(qid)
  if q is None: raise QuestEventError(f"unknown quest {qid!r}")
  if qs["status"]!="inactive": raise QuestEventError(f"quest {qid!r} is not inactive")
  if not self._prereqs(q,s,c): raise QuestEventError(f"quest {qid!r} prerequisites are not satisfied")
  stage=q["initialStageId"]; qs.update(status="active",stageId=stage,reachedStageIds=[stage]); self._notify(out,s,"quest_activated","quest",qid,stageId=stage)
 def set_objective_complete(self,qid,oid,complete=True,*,context=None):
  def op(s,out):
   q=self.quests.get(qid); qs=self._maps(s)[0].get(qid)
   if q is None or oid not in q["_objectives"]: raise QuestEventError("unknown quest objective")
   if qs["status"]!="active" or oid not in q["_stages"][qs["stageId"]].get("objectiveIds",[]): raise QuestEventError("objective is not active")
   old=oid in qs["completedObjectiveIds"]
   if old==complete: raise QuestEventError("objective transition must change state")
   (qs["completedObjectiveIds"].append(oid) if complete else qs["completedObjectiveIds"].remove(oid)); qs["completedObjectiveIds"].sort(); self._notify(out,s,"objective_completed" if complete else "objective_reopened","objective",oid,questId=qid)
  return self._tx(op)
 def evaluate_objectives(self,*,context=None):
  def op(s,out):
   for qid,q in sorted(self.quests.items()):
    qs=self._maps(s)[0][qid]
    if qs["status"]=="active":
     for oid in sorted(q["_stages"][qs["stageId"]].get("objectiveIds",[])):
      if oid not in qs["completedObjectiveIds"] and self._condition(q["_objectives"][oid],s,context or {}): qs["completedObjectiveIds"].append(oid); qs["completedObjectiveIds"].sort(); self._notify(out,s,"objective_completed","objective",oid,questId=qid)
  return self._tx(op)
 def advance_quest(self,qid,target,*,context=None): return self._tx(lambda s,e:self._advance(s,e,qid,target))
 def _advance(self,s,out,qid,target):
  q=self.quests.get(qid); qs=self._maps(s)[0].get(qid)
  if q is None or qs["status"]!="active": raise QuestEventError("quest is not active")
  old=qs["stageId"]; stage=q["_stages"][old]
  if target not in stage.get("nextStageIds",[]): raise QuestEventError(f"invalid stage transition {old!r} -> {target!r}")
  if not set(stage.get("objectiveIds",[])).issubset(qs["completedObjectiveIds"]): raise QuestEventError("active stage objectives are incomplete")
  if target in qs["reachedStageIds"]: raise QuestEventError("cyclic runtime activation rejected")
  qs["stageId"]=target; qs["reachedStageIds"].append(target); self._notify(out,s,"quest_advanced","quest",qid,fromStageId=old,toStageId=target)
 def complete_quest(self,qid,*,context=None): return self._tx(lambda s,e:self._finish(s,e,qid,"completed",context or {}))
 def fail_quest(self,qid,*,context=None): return self._tx(lambda s,e:self._finish(s,e,qid,"failed",context or {}))
 def cancel_quest(self,qid,*,context=None): return self._tx(lambda s,e:self._finish(s,e,qid,"cancelled",context or {}))
 def _finish(self,s,out,qid,status,c):
  q=self.quests.get(qid); qs=self._maps(s)[0].get(qid)
  if q is None or qs["status"]!="active": raise QuestEventError("quest is not active")
  if status=="completed":
   stage=q["_stages"][qs["stageId"]]
   if stage.get("nextStageIds") or not set(stage.get("objectiveIds",[])).issubset(qs["completedObjectiveIds"]): raise QuestEventError("quest is not at a completed terminal stage")
   self._outcomes(s,out,q.get("outcomes",[]),f"quest:{qid}",1,c)
  qs["status"]=status; self._notify(out,s,f"quest_{status}","quest",qid,stageId=qs["stageId"])
 def enqueue_trigger(self,eid,tid,*,due_time=0,priority=0,occurrence_key=None,context=None):
  if eid not in self.events or tid not in self.events[eid]["_triggers"]: raise QuestEventError("unknown event trigger")
  if isinstance(due_time,bool) or not isinstance(due_time,(int,float)) or isinstance(priority,bool) or not isinstance(priority,int): raise QuestEventError("invalid trigger ordering values")
  key=occurrence_key or f"{due_time}:{priority}:{eid}:{tid}"
  def op(s,out):
   if key in s["processedTriggerKeys"] or any(x["key"]==key for x in s["pendingTriggers"]): return
   s["pendingTriggers"].append({"eventId":eid,"triggerId":tid,"dueTime":due_time,"priority":priority,"key":key,"context":copy.deepcopy(dict(context or {}))}); s["pendingTriggers"].sort(key=lambda x:(x["dueTime"],x["priority"],x["eventId"],x["triggerId"],x["key"]))
  return self._tx(op)
 def process_until(self,target):
  def op(s,out):
   count=0
   while s["pendingTriggers"] and s["pendingTriggers"][0]["dueTime"]<=target:
    count+=1
    if count>self.limit: raise QuestEventError(f"trigger processing exceeded bounded limit {self.limit}")
    p=s["pendingTriggers"].pop(0); s["processedTriggerKeys"].append(p["key"]); s["processedTriggerKeys"].sort(); self._deliver(s,out,p["eventId"],p["triggerId"],p["key"],p["context"])
  return self._tx(op)
 def _deliver(self,s,out,eid,tid,key,c):
  e=self.events[eid]; es=self._maps(s)[1][eid]
  if not e["repeatable"] and es["occurrences"]: self._notify(out,s,"event_deduplicated","event",eid,occurrenceKey=key); return
  if not self._prereqs(e,s,c): self._notify(out,s,"event_blocked","event",eid,occurrenceKey=key); return
  if not self._condition(e["_triggers"][tid],s,c): return
  occurrence=es["occurrences"]+1; self._outcomes(s,out,e.get("outcomes",[]),f"event:{eid}",occurrence,c); es["occurrences"]=occurrence; self._notify(out,s,"event_occurred","event",eid,triggerId=tid,occurrence=occurrence,occurrenceKey=key)
 def discover(self,did,*,context=None):
  def op(s,out):
   d=self.discoveries.get(did); ds=self._maps(s)[2].get(did)
   if d is None: raise QuestEventError(f"unknown discovery {did!r}")
   if ds["discovered"]: return
   if not self._prereqs(d,s,context or {}) or d.get("conditionId") and not self._condition(d,s,context or {}): raise QuestEventError("discovery conditions are not satisfied")
   self._outcomes(s,out,d.get("outcomes",[]),f"discovery:{did}",1,context or {}); ds["discovered"]=True; self._notify(out,s,"discovery_made","discovery",did)
  return self._tx(op)
 def _outcomes(self,s,out,values,owner,occurrence,c):
  fresh=[]
  for x in sorted(values,key=lambda y:y["id"]):
   key=f"{owner}:{occurrence}:{x['id']}"
   if key not in s["deliveredOutcomeKeys"]: fresh.append((x,key))
  scenario=[x for x,k in fresh if x["kind"]=="scenario_outcome"]
  if scenario:
   snap=copy.deepcopy(s); before=copy.deepcopy(snap)
   try: candidate=self.ext.apply_outcomes(tuple(copy.deepcopy(scenario)),snap,copy.deepcopy(dict(c)))
   except QuestEventError: raise
   except Exception as x: raise QuestEventError(f"scenario outcomes failed: {x}") from x
   if snap!=before or not isinstance(candidate,Mapping) or "externalState" not in candidate: raise QuestEventError("outcome handler must return an unmutated complete snapshot")
   protected=copy.deepcopy(dict(candidate)); external=protected.pop("externalState"); expected=copy.deepcopy(before); expected.pop("externalState")
   if protected!=expected: raise QuestEventError("outcome handler changed engine-owned state")
   s["externalState"]=copy.deepcopy(external)
  for x,key in fresh:
   if x["kind"]=="start_quest": self._activate(s,out,x["questId"],c)
   elif x["kind"]=="advance_quest":
    if self._maps(s)[0][x["questId"]]["stageId"]!=x["fromStageId"]: raise QuestEventError("advance outcome source is not active")
    self._advance(s,out,x["questId"],x["toStageId"])
   elif x["kind"]=="emit_event": self._deliver(s,out,x["eventId"],sorted(self.events[x["eventId"]]["_triggers"])[0],key,c)
   s["deliveredOutcomeKeys"].append(key)
  s["deliveredOutcomeKeys"].sort()
 @property
 def emitted_events(self): return tuple(self._emitted)
 def drain_events(self): r=tuple(self._emitted); self._emitted=[]; return r
 def snapshot(self): return copy.deepcopy(self.state)
 def validate_snapshot(self,s):
  required={"schemaVersion","quests","events","discoveries","pendingTriggers","processedTriggerKeys","deliveredOutcomeKeys","nextSequence","externalState"}
  if not isinstance(s,Mapping) or s.get("schemaVersion")!=STATE_VERSION or set(s)!=required: raise QuestEventError("quest/event state schema or fields are invalid")
  qs=_index(s["quests"],"quest state"); es=_index(s["events"],"event state"); ds=_index(s["discoveries"],"discovery state")
  if set(qs)!=set(self.quests) or set(es)!=set(self.events) or set(ds)!=set(self.discoveries): raise QuestEventError("state is incompatible with definitions")
  for i,x in qs.items():
   if x.get("status") not in {"inactive","active",*_TERMINAL}: raise QuestEventError(f"quest {i}: invalid status")
   stage=x.get("stageId")
   if (x["status"]=="inactive")!=(stage is None) or stage is not None and stage not in self.quests[i]["_stages"]: raise QuestEventError(f"quest {i}: invalid stage")
   for f in ("reachedStageIds","completedObjectiveIds"):
    if not isinstance(x.get(f),list) or len(x[f])!=len(set(x[f])): raise QuestEventError(f"quest {i}: invalid {f}")
  for i,x in es.items():
   n=x.get("occurrences")
   if isinstance(n,bool) or not isinstance(n,int) or n<0 or not self.events[i]["repeatable"] and n>1: raise QuestEventError(f"event {i}: invalid occurrences")
  keys=[]
  for p in s["pendingTriggers"]:
   if not isinstance(p,Mapping) or p.get("eventId") not in self.events or p.get("triggerId") not in self.events[p["eventId"]]["_triggers"]: raise QuestEventError("pending trigger has missing reference")
   keys.append(p.get("key"))
  if len(keys)!=len(set(keys)) or set(keys)&set(s["processedTriggerKeys"]): raise QuestEventError("duplicate trigger key")
  if isinstance(s["nextSequence"],bool) or not isinstance(s["nextSequence"],int) or s["nextSequence"]<1: raise QuestEventError("invalid nextSequence")
  return copy.deepcopy(dict(s))
 def restore(self,s): self.state=self.validate_snapshot(s); self._representations={}; self._emitted=[]
 def reconstruct_runtime(self,factory):
  built={}; qs,es,ds=self._maps(self.state)
  for kind,values,predicate in (("quest",qs,lambda x:x["status"]!="inactive"),("event",es,lambda x:x["occurrences"]),("discovery",ds,lambda x:x["discovered"])):
   for i,x in sorted(values.items()):
    if predicate(x): built[f"{kind}:{i}"]=factory(kind,i,copy.deepcopy(x))
  self._representations=built; return dict(built)
 def lose_runtime_representation(self,kind,ident): return self._representations.pop(f"{kind}:{ident}",None) is not None

class QuestEventSaveAdapter:
 def __init__(self,runtime,world_state): self.runtime,self.world_state=runtime,copy.deepcopy(dict(world_state))
 def capture_world(self): r=copy.deepcopy(self.world_state); r[QUEST_EVENT_WORLD_STATE_KEY]=self.runtime.snapshot(); return r
 def migrate_legacy_world(self,s):
  if not isinstance(s,Mapping): raise QuestEventError("legacy world state must be an object")
  r=copy.deepcopy(dict(s)); r.setdefault(QUEST_EVENT_WORLD_STATE_KEY,self.runtime.snapshot()); self.validate_world(r); return r
 def validate_world(self,s):
  if not isinstance(s,Mapping) or QUEST_EVENT_WORLD_STATE_KEY not in s: raise QuestEventError(f"world state is missing {QUEST_EVENT_WORLD_STATE_KEY}")
  self.runtime.validate_snapshot(s[QUEST_EVENT_WORLD_STATE_KEY])
 def reconstruct(self,s): self.validate_world(s); return self.runtime.validate_snapshot(s[QUEST_EVENT_WORLD_STATE_KEY])
 def activate(self,s,reconstructed):
  if reconstructed!=self.runtime.validate_snapshot(s[QUEST_EVENT_WORLD_STATE_KEY]): raise QuestEventError("reconstructed state mismatch")
  self.runtime.restore(reconstructed); self.world_state=copy.deepcopy(dict(s))
