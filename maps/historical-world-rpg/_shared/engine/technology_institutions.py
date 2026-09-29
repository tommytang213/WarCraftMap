"""Deterministic, scenario-neutral technology and institution simulation."""
from __future__ import annotations
import copy, re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Mapping

STATE_SCHEMA_VERSION=1
WORLD_STATE_KEY="technologyInstitutionState"
UNITS_PER_POINT=1_000_000
MAX_PERCENT_UNITS=100*UNITS_PER_POINT
_ID=re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")

class ResearchError(ValueError): pass

@dataclass(frozen=True)
class ResearchEvent:
    sequence:int; kind:str; polity_id:str|None=None; province_id:str|None=None
    node_id:str|None=None; unlock_kind:str|None=None; content_id:str|None=None
    def to_dict(self):
        result={"sequence":self.sequence,"kind":self.kind}
        for key,value in (("polityId",self.polity_id),("provinceId",self.province_id),
                          ("nodeId",self.node_id),("unlockKind",self.unlock_kind),("contentId",self.content_id)):
            if value is not None: result[key]=value
        return result

def _id(value,context):
    if not isinstance(value,str) or not _ID.fullmatch(value): raise ResearchError(f"{context}: invalid stable ID {value!r}")
    return value

def _decimal(value,context,minimum=None,maximum=None):
    if isinstance(value,bool): raise ResearchError(f"{context}: invalid number")
    try: result=Decimal(str(value))
    except (InvalidOperation,ValueError): raise ResearchError(f"{context}: invalid number") from None
    if not result.is_finite() or minimum is not None and result<Decimal(str(minimum)) or maximum is not None and result>Decimal(str(maximum)):
        raise ResearchError(f"{context}: number outside allowed range")
    return result

def _units(value,context,minimum=0,maximum=None):
    return int((_decimal(value,context,minimum,maximum)*UNITS_PER_POINT).to_integral_value(rounding=ROUND_HALF_UP))

def _date(value):
    if not isinstance(value,str): raise ResearchError("current date: expected YYYY-MM-DD")
    try: parsed=date.fromisoformat(value)
    except ValueError as exc: raise ResearchError(f"current date: invalid date {value!r}") from exc
    if parsed.isoformat()!=value: raise ResearchError("current date: expected YYYY-MM-DD")
    return parsed

def _index(values,domain):
    if not isinstance(values,list): raise ResearchError(f"{domain}: must be an array")
    result={}
    for record in values:
        if not isinstance(record,Mapping): raise ResearchError(f"{domain}: entry must be an object")
        ident=_id(record.get("id"),f"{domain}.id")
        if ident in result: raise ResearchError(f"{domain}: duplicate ID {ident!r}")
        result[ident]=record
    return result

class TechnologyInstitutionRuntime:
    """Authoritative fixed-point polity research and province adoption."""
    def __init__(self,world,current_date):
        if not isinstance(world,Mapping): raise ResearchError("world definitions must be an object")
        self.initial_date=_date(current_date).isoformat(); data=copy.deepcopy(dict(world))
        self.polity_ids=tuple(sorted(_index(data.get("polities"),"polities")))
        self.province_ids=tuple(sorted(_index(data.get("provinces"),"provinces")))
        technologies=_index(data.get("technologies"),"technologies"); institutions=_index(data.get("institutions"),"institutions")
        overlap=set(technologies)&set(institutions)
        if overlap: raise ResearchError(f"research graph: duplicate node {sorted(overlap)[0]!r}")
        self.nodes={**technologies,**institutions}
        self.node_kinds={x:"technology" for x in technologies}|{x:"institution" for x in institutions}
        for node_id,node in self.nodes.items():
            prerequisites=node.get("prerequisiteIds")
            if not isinstance(prerequisites,list) or len(prerequisites)!=len(set(prerequisites)): raise ResearchError(f"research node {node_id}: invalid prerequisites")
            if any(x not in self.nodes for x in prerequisites): raise ResearchError(f"research node {node_id}: unknown prerequisite")
            cost=node.get("timeCost")
            if not isinstance(cost,Mapping) or isinstance(cost.get("preferredYear"),bool) or not isinstance(cost.get("preferredYear"),int): raise ResearchError(f"research node {node_id}: invalid time cost")
            _units(cost.get("baseCost"),f"{node_id}.baseCost",Decimal("0.000001"))
            _decimal(cost.get("aheadOfTimeCostMultiplier"),f"{node_id}.ahead multiplier",1)
            _decimal(cost.get("additionalMultiplierPerYearAhead"),f"{node_id}.year multiplier",0)
            if not isinstance(node.get("unlocks"),list): raise ResearchError(f"research node {node_id}: invalid unlocks")
            for unlock in node["unlocks"]:
                if not isinstance(unlock,Mapping): raise ResearchError(f"research node {node_id}: invalid unlock")
                _id(unlock.get("kind"),f"{node_id}.unlock kind"); _id(unlock.get("contentId"),f"{node_id}.unlock content")
        self.research={x:{"completed":set(),"progress":{}} for x in self.polity_ids}
        self.adoption={x:{} for x in self.province_ids}; self._events=[]; self.next_sequence=1
        self._load_initial(data)

    def _load_initial(self,data):
        seen=set()
        for raw in data.get("polityResearchStates",[]):
            polity=raw.get("polityId") if isinstance(raw,Mapping) else None
            if polity not in self.research or polity in seen: raise ResearchError("invalid or duplicate polity research state")
            seen.add(polity); completed=list(raw.get("completedTechnologyIds",[]))+list(raw.get("establishedInstitutionIds",[]))
            if len(completed)!=len(set(completed)) or any(x not in self.nodes for x in completed): raise ResearchError(f"polity {polity}: invalid completion")
            progress={}
            for item in raw.get("researchProgress",[]):
                node=item.get("nodeId") if isinstance(item,Mapping) else None
                if node not in self.nodes or node in progress or node in completed: raise ResearchError(f"polity {polity}: invalid progress node {node!r}")
                percent=_decimal(item.get("progress"),f"polity {polity}.{node}.progress",0,Decimal("99.999999"))
                progress[node]=int((self.cost_units(node,self.initial_date)*percent/100).to_integral_value(rounding=ROUND_HALF_UP))
            self.research[polity]={"completed":set(completed),"progress":progress}
        seen.clear()
        for raw in data.get("provinceAdoptionStates",[]):
            province=raw.get("provinceId") if isinstance(raw,Mapping) else None
            if province not in self.adoption or province in seen: raise ResearchError("invalid or duplicate province adoption state")
            seen.add(province); values={}
            for item in raw.get("adoption",[]):
                node=item.get("nodeId") if isinstance(item,Mapping) else None
                if node not in self.nodes or node in values: raise ResearchError(f"province {province}: invalid adoption node {node!r}")
                values[node]=_units(item.get("level"),f"province {province}.{node}.level",0,100)
            self.adoption[province]=values

    @property
    def events(self): return tuple(self._events)
    def _polity(self,value):
        if value not in self.research: raise ResearchError(f"unknown polity {value!r}")
    def _province(self,value):
        if value not in self.adoption: raise ResearchError(f"unknown province {value!r}")
    def _node(self,value):
        if value not in self.nodes: raise ResearchError(f"unknown research node {value!r}")
    def completed(self,polity): self._polity(polity); return tuple(sorted(self.research[polity]["completed"]))
    def progress_units(self,polity,node): self._polity(polity); self._node(node); return self.research[polity]["progress"].get(node,0)
    def adoption_units(self,province,node): self._province(province); self._node(node); return self.adoption[province].get(node,0)

    def cost_units(self,node,current_date):
        self._node(node) if hasattr(self,"nodes") else None
        record=self.nodes[node]; cost=record["timeCost"]; years=max(0,cost["preferredYear"]-_date(current_date).year)
        multiplier=Decimal(1) if years==0 else _decimal(cost["aheadOfTimeCostMultiplier"],"ahead multiplier")+_decimal(cost["additionalMultiplierPerYearAhead"],"year multiplier")*years
        return _units(_decimal(cost["baseCost"],"base cost")*multiplier,"research cost",Decimal("0.000001"))

    def advance_research(self,polity,node,points,current_date):
        self._polity(polity); self._node(node); amount=_units(points,"research points",Decimal("0.000001"))
        state=self.research[polity]
        if node in state["completed"]: raise ResearchError(f"research node {node!r} is already complete")
        missing=sorted(set(self.nodes[node]["prerequisiteIds"])-state["completed"])
        if missing: raise ResearchError(f"research node {node!r}: unavailable prerequisites {missing!r}")
        total=state["progress"].get(node,0)+amount; required=self.cost_units(node,current_date)
        if total<required: state["progress"][node]=total; return ()
        state["progress"].pop(node,None); state["completed"].add(node)
        kind="technology_completed" if self.node_kinds[node]=="technology" else "institution_established"
        emitted=[ResearchEvent(self.next_sequence,kind,polity_id=polity,node_id=node)]; sequence=self.next_sequence+1
        for unlock in sorted(self.nodes[node]["unlocks"],key=lambda x:(x["kind"],x["contentId"])):
            emitted.append(ResearchEvent(sequence,"content_unlocked",polity_id=polity,node_id=node,unlock_kind=unlock["kind"],content_id=unlock["contentId"])); sequence+=1
        self._events.extend(emitted); self.next_sequence=sequence; return tuple(emitted)

    def advance_adoption(self,province,node,points):
        self._province(province); self._node(node); amount=_units(points,"adoption points",Decimal("0.000001"))
        old=self.adoption[province].get(node,0)
        if old>=MAX_PERCENT_UNITS: raise ResearchError(f"province {province}: node {node!r} is already fully adopted")
        self.adoption[province][node]=min(MAX_PERCENT_UNITS,old+amount)
        event=ResearchEvent(self.next_sequence,"province_adoption_changed",province_id=province,node_id=node)
        self._events.append(event); self.next_sequence+=1; return event

    def snapshot(self):
        return {"schemaVersion":1,"nextEventSequence":self.next_sequence,
          "polities":[{"polityId":p,"completedNodeIds":sorted(s["completed"]),"progress":[{"nodeId":n,"workUnits":s["progress"][n]} for n in sorted(s["progress"])]} for p,s in sorted(self.research.items())],
          "provinces":[{"provinceId":p,"adoption":[{"nodeId":n,"levelUnits":s[n]} for n in sorted(s)]} for p,s in sorted(self.adoption.items())],
          "events":[x.to_dict() for x in self._events]}

    def _parse(self,candidate):
        if not isinstance(candidate,Mapping) or candidate.get("schemaVersion")!=1 or set(candidate)!={"schemaVersion","nextEventSequence","polities","provinces","events"}: raise ResearchError("invalid technology/institution state")
        research={}
        if not isinstance(candidate["polities"],list): raise ResearchError("polities must be an array")
        for raw in candidate["polities"]:
            p=raw.get("polityId") if isinstance(raw,Mapping) else None
            if not isinstance(raw,Mapping) or set(raw)!={"polityId","completedNodeIds","progress"} or p not in self.research or p in research: raise ResearchError("invalid polity research record")
            done=raw["completedNodeIds"]
            if not isinstance(done,list) or done!=sorted(set(done)) or any(x not in self.nodes for x in done): raise ResearchError(f"polity {p}: malformed completions")
            progress={}
            if not isinstance(raw["progress"],list): raise ResearchError(f"polity {p}: malformed progress")
            for item in raw["progress"]:
                n=item.get("nodeId") if isinstance(item,Mapping) else None; u=item.get("workUnits") if isinstance(item,Mapping) else None
                if not isinstance(item,Mapping) or set(item)!={"nodeId","workUnits"} or n not in self.nodes or n in progress or n in done or isinstance(u,bool) or not isinstance(u,int) or u<0: raise ResearchError(f"polity {p}: malformed progress")
                progress[n]=u
            research[p]={"completed":set(done),"progress":progress}
        if set(research)!=set(self.research): raise ResearchError("polity research snapshot is incomplete")
        adoption={}
        if not isinstance(candidate["provinces"],list): raise ResearchError("provinces must be an array")
        for raw in candidate["provinces"]:
            p=raw.get("provinceId") if isinstance(raw,Mapping) else None
            if not isinstance(raw,Mapping) or set(raw)!={"provinceId","adoption"} or p not in self.adoption or p in adoption or not isinstance(raw["adoption"],list): raise ResearchError("invalid province adoption record")
            values={}
            for item in raw["adoption"]:
                n=item.get("nodeId") if isinstance(item,Mapping) else None; u=item.get("levelUnits") if isinstance(item,Mapping) else None
                if not isinstance(item,Mapping) or set(item)!={"nodeId","levelUnits"} or n not in self.nodes or n in values or isinstance(u,bool) or not isinstance(u,int) or not 0<=u<=MAX_PERCENT_UNITS: raise ResearchError(f"province {p}: malformed adoption")
                values[n]=u
            adoption[p]=values
        if set(adoption)!=set(self.adoption): raise ResearchError("province adoption snapshot is incomplete")
        events=[]; allowed={"technology_completed","institution_established","content_unlocked","province_adoption_changed"}
        if not isinstance(candidate["events"],list): raise ResearchError("events must be an array")
        for sequence,raw in enumerate(candidate["events"],1):
            if not isinstance(raw,Mapping) or raw.get("sequence")!=sequence or raw.get("kind") not in allowed or not set(raw)<={"sequence","kind","polityId","provinceId","nodeId","unlockKind","contentId"}: raise ResearchError("malformed research event history")
            if raw.get("nodeId") not in self.nodes or raw.get("polityId") is not None and raw["polityId"] not in self.research or raw.get("provinceId") is not None and raw["provinceId"] not in self.adoption: raise ResearchError("research event has invalid references")
            events.append(ResearchEvent(sequence,raw["kind"],raw.get("polityId"),raw.get("provinceId"),raw.get("nodeId"),raw.get("unlockKind"),raw.get("contentId")))
        nxt=candidate["nextEventSequence"]
        if isinstance(nxt,bool) or not isinstance(nxt,int) or nxt!=len(events)+1: raise ResearchError("nextEventSequence does not follow event history")
        return research,adoption,events,nxt
    def validate_snapshot(self,candidate): self._parse(candidate)
    def restore(self,candidate):
        self.research,self.adoption,self._events,self.next_sequence=self._parse(candidate)

class TechnologyInstitutionSaveAdapter:
    def __init__(self,runtime,world_state): self.runtime=runtime; self.world_state=copy.deepcopy(dict(world_state))
    def capture_world(self):
        result=copy.deepcopy(self.world_state); result[WORLD_STATE_KEY]=self.runtime.snapshot(); return result
    def migrate_legacy_world(self,candidate):
        if not isinstance(candidate,Mapping): raise ResearchError("legacy world state must be an object")
        result=copy.deepcopy(dict(candidate)); result.setdefault(WORLD_STATE_KEY,self.runtime.snapshot()); self.validate_world(result); return result
    def validate_world(self,candidate):
        if not isinstance(candidate,Mapping) or WORLD_STATE_KEY not in candidate: raise ResearchError(f"world state is missing {WORLD_STATE_KEY}")
        self.runtime.validate_snapshot(candidate[WORLD_STATE_KEY])
    def reconstruct(self,candidate): self.validate_world(candidate); return copy.deepcopy(candidate[WORLD_STATE_KEY])
    def activate(self,candidate,reconstructed):
        if reconstructed!=candidate[WORLD_STATE_KEY]: raise ResearchError("reconstructed research state does not match candidate")
        self.runtime.restore(reconstructed); self.world_state=copy.deepcopy(dict(candidate))
