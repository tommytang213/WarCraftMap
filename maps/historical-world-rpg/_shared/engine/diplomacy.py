"""Stable-ID diplomacy, conflict, occupation, and peace simulation."""
from __future__ import annotations
import copy, re
from dataclasses import dataclass
from typing import Mapping

DIPLOMACY_WORLD_STATE_KEY="diplomacyState"; DIPLOMACY_STATE_SCHEMA_VERSION=1
EVENT_CONSUMERS=("military","province","settlement","economy","quest","ui")
_ID=re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")
class DiplomacyError(ValueError): pass
def _id(v,c):
    if not isinstance(v,str) or not _ID.fullmatch(v): raise DiplomacyError(f"{c}: invalid stable ID {v!r}")
    return v
def _pair(a,b): return tuple(sorted((a,b)))

@dataclass(frozen=True)
class DiplomaticEvent:
    sequence:int; kind:str; conflict_id:str; polity_ids:tuple[str,...]
    entity_kind:str|None=None; entity_id:str|None=None; controller_polity_id:str|None=None
    def to_dict(self):
        d={"sequence":self.sequence,"kind":self.kind,"conflictId":self.conflict_id,"polityIds":list(self.polity_ids),"consumers":list(EVENT_CONSUMERS)}
        if self.entity_kind is not None:d.update(entityKind=self.entity_kind,entityId=self.entity_id,controllerPolityId=self.controller_polity_id)
        return d

class DiplomacyRuntime:
    def __init__(self,polities,provinces=None,settlements=None,initial_conflicts=()):
        self.polities,self.provinces,self.settlements=polities,provinces,settlements
        ids=polities.ids(); self._relations={_pair(a,b):"neutral" for i,a in enumerate(ids) for b in ids[i+1:]}
        self._conflicts={}; self._occupations={}; self._peace=[]; self._events=[]; self._next=1
        for conflict in initial_conflicts:
            attackers=conflict.get("attackerPolityIds",()); defenders=conflict.get("defenderPolityIds",())
            if not attackers or not defenders: raise DiplomacyError("initial conflict sides must not be empty")
            self.declare_war(conflict.get("id"),attackers[0],defenders[0])
            for polity in attackers[1:]: self.join_conflict(conflict["id"],polity,"attacker")
            for polity in defenders[1:]: self.join_conflict(conflict["id"],polity,"defender")
    @property
    def events(self):return tuple(self._events)
    @property
    def peace_records(self):return tuple(copy.deepcopy(self._peace))
    def conflict(self,cid):return copy.deepcopy(self._conflicts.get(cid))
    def occupations(self,cid=None):return tuple(copy.deepcopy(v) for _,v in sorted(self._occupations.items()) if cid is None or v["conflictId"]==cid)
    def _polity(self,p):
        v=self.polities.lookup(p)
        if v is None:raise DiplomacyError(f"unknown polity {p!r}")
        if not v.active:raise DiplomacyError(f"inactive polity {p!r}")
    def relation(self,a,b):
        self._polity(a);self._polity(b)
        if a==b:raise DiplomacyError("bilateral relation requires distinct polities")
        return self._relations[_pair(a,b)]
    def _active(self,cid):
        c=self._conflicts.get(cid)
        if c is None:raise DiplomacyError(f"unknown conflict {cid!r}")
        if c["status"]!="active":raise DiplomacyError(f"conflict {cid!r} is concluded")
        return c
    def _emit(self,kind,cid,polities,**kw):
        e=DiplomaticEvent(self._next,kind,cid,tuple(sorted(polities)),**kw);self._events.append(e);self._next+=1;return e
    def _elsewhere(self,a,b,exclude):
        for cid,c in self._conflicts.items():
            if cid==exclude or c["status"]!="active":continue
            x,y=c["sides"]["attacker"],c["sides"]["defender"]
            if (a in x and b in y) or (b in x and a in y):return True
        return False
    def declare_war(self,cid,attacker,defender):
        _id(cid,"conflict id");self._polity(attacker);self._polity(defender)
        if attacker==defender:raise DiplomacyError("war participants must be distinct")
        if cid in self._conflicts:raise DiplomacyError("duplicate conflict")
        if self._relations[_pair(attacker,defender)]=="war":raise DiplomacyError("polities are already at war")
        self._conflicts[cid]={"id":cid,"status":"active","sides":{"attacker":[attacker],"defender":[defender]},"removedParticipants":[]}
        self._relations[_pair(attacker,defender)]="war";return self._emit("war_declared",cid,(attacker,defender))
    def join_conflict(self,cid,polity,side):
        c=self._active(cid);self._polity(polity)
        if side not in ("attacker","defender"):raise DiplomacyError("side must be attacker or defender")
        active=c["sides"]["attacker"]+c["sides"]["defender"]
        if polity in active:raise DiplomacyError("polity is already an active participant")
        if polity in c["removedParticipants"]:raise DiplomacyError("removed participant cannot rejoin")
        opponents=c["sides"]["defender" if side=="attacker" else "attacker"]
        if any(self._relations[_pair(polity,o)]=="war" for o in opponents):raise DiplomacyError("participant has a contradictory war relation")
        c["sides"][side].append(polity);c["sides"][side].sort()
        for o in opponents:self._relations[_pair(polity,o)]="war"
        return self._emit("participant_joined",cid,(polity,))
    def leave_conflict(self,cid,polity):
        c=self._active(cid);self._polity(polity);side=next((s for s in ("attacker","defender") if polity in c["sides"][s]),None)
        if side is None:raise DiplomacyError("polity is not an active participant")
        if len(c["sides"][side])==1:raise DiplomacyError("last participant must conclude peace")
        if any(o["conflictId"]==cid and o["controllerPolityId"]==polity for o in self._occupations.values()):raise DiplomacyError("an occupying participant must resolve its occupations before leaving")
        opponents=c["sides"]["defender" if side=="attacker" else "attacker"]
        c["sides"][side].remove(polity);c["removedParticipants"].append(polity);c["removedParticipants"].sort()
        for o in opponents:
            if not self._elsewhere(polity,o,cid):self._relations[_pair(polity,o)]="neutral"
        return self._emit("participant_left",cid,(polity,))
    def record_occupation(self,cid,kind,entity_id,controller):
        c=self._active(cid);self._polity(controller)
        runtime=self.provinces if kind=="province" else self.settlements if kind=="settlement" else None
        if runtime is None:raise DiplomacyError("occupation entity kind/runtime must be province or settlement")
        entity=runtime.lookup(entity_id)
        if entity is None:raise DiplomacyError(f"unknown {kind} {entity_id!r}")
        sides=c["sides"]; owner_side=next((s for s in sides if entity.legal_owner_polity_id in sides[s]),None);controller_side=next((s for s in sides if controller in sides[s]),None)
        if owner_side is None or controller_side is None or owner_side==controller_side:raise DiplomacyError("occupation must be by an opposing active participant")
        key=(kind,entity_id)
        if key in self._occupations:raise DiplomacyError("territory already occupied")
        if kind=="province":runtime.transition(entity_id,controller_polity_id=controller,reason="military_occupation")
        else:runtime.update(entity_id,controllerPolityId=controller)
        self._occupations[key]={"conflictId":cid,"entityKind":kind,"entityId":entity_id,"legalOwnerPolityId":entity.legal_owner_polity_id,"controllerPolityId":controller}
        return self._emit("occupation_recorded",cid,(entity.legal_owner_polity_id,controller),entity_kind=kind,entity_id=entity_id,controller_polity_id=controller)
    def conclude_peace(self,cid,*,territorial_outcomes=()):
        c=self._active(cid); outcomes=copy.deepcopy(list(territorial_outcomes));calls=[];seen=set()
        for o in outcomes:
            if not isinstance(o,Mapping):raise DiplomacyError("peace outcomes must be objects")
            kind,ident=o.get("entityKind"),o.get("entityId");key=(kind,ident)
            runtime=self.provinces if kind=="province" else self.settlements if kind=="settlement" else None
            if key in seen:raise DiplomacyError("duplicate peace outcome")
            if runtime is None or runtime.lookup(ident) is None:raise DiplomacyError(f"unknown peace territory {ident!r}")
            owner,controller=o.get("legalOwnerPolityId"),o.get("controllerPolityId");self._polity(owner);self._polity(controller);cur=runtime.require(ident)
            if (owner,controller)==(cur.legal_owner_polity_id,cur.controller_polity_id):raise DiplomacyError("peace outcome must change territory")
            seen.add(key);calls.append((runtime,ident,owner,controller))
        unresolved={key for key,value in self._occupations.items() if value["conflictId"]==cid}-seen
        if unresolved:raise DiplomacyError("peace must explicitly resolve every active occupation")
        backups=[(r,r.snapshot()) for r in set(x[0] for x in calls)]
        try:
            for r,i,o,ctl in calls:
                if r is self.provinces:r.transition(i,legal_owner_polity_id=o,controller_polity_id=ctl,reason="peace_treaty")
                else:r.update(i,legalOwnerPolityId=o,controllerPolityId=ctl)
        except Exception:
            for r,s in backups:r.restore(s)
            raise
        participants=c["sides"]["attacker"]+c["sides"]["defender"];c["status"]="concluded"
        for a in c["sides"]["attacker"]:
            for b in c["sides"]["defender"]:
                if not self._elsewhere(a,b,cid):self._relations[_pair(a,b)]="neutral"
        self._occupations={k:v for k,v in self._occupations.items() if v["conflictId"]!=cid}
        self._peace.append({"id":"peace_"+cid,"conflictId":cid,"participants":sorted(participants),"territorialOutcomes":outcomes})
        return self._emit("peace_concluded",cid,participants)
    def snapshot(self):
        return {"schemaVersion":1,"nextEventSequence":self._next,"relations":[{"polityIds":list(k),"status":v} for k,v in sorted(self._relations.items())],"conflicts":[copy.deepcopy(self._conflicts[k]) for k in sorted(self._conflicts)],"occupations":list(self.occupations()),"peaceRecords":copy.deepcopy(self._peace),"events":[e.to_dict() for e in self._events]}
    def validate_snapshot(self,x):
        if not isinstance(x,Mapping) or x.get("schemaVersion")!=1:raise DiplomacyError("diplomacy state schemaVersion must be 1")
        for k in ("relations","conflicts","occupations","peaceRecords","events"):
            if not isinstance(x.get(k),list):raise DiplomacyError(f"{k} must be an array")
        rel={}
        for r in x["relations"]:
            ids=r.get("polityIds") if isinstance(r,Mapping) else None
            if not isinstance(ids,list) or len(ids)!=2 or ids[0]==ids[1] or r.get("status") not in ("neutral","war"):raise DiplomacyError("invalid bilateral relation")
            for p in ids:self._polity(p)
            pair=_pair(*ids)
            if pair in rel:raise DiplomacyError("duplicate bilateral relation")
            rel[pair]=r["status"]
        if set(rel)!=set(self._relations):raise DiplomacyError("incomplete bilateral relations")
        conflicts={}
        for c in x["conflicts"]:
            if not isinstance(c,Mapping) or c.get("status") not in ("active","concluded"):raise DiplomacyError("invalid conflict")
            cid=_id(c.get("id"),"conflict id");sides=c.get("sides");removed=c.get("removedParticipants")
            if cid in conflicts or not isinstance(sides,Mapping) or set(sides)!={"attacker","defender"} or not isinstance(removed,list):raise DiplomacyError("invalid conflict participants")
            active=[]
            for side in sides:
                if not isinstance(sides[side],list) or not sides[side]:raise DiplomacyError("empty conflict side")
                for p in sides[side]:self._polity(p);active.append(p)
            if len(active)!=len(set(active)) or set(active)&set(removed):raise DiplomacyError("contradictory conflict participants")
            conflicts[cid]=copy.deepcopy(dict(c))
        for pair,status in rel.items():
            war=any(c["status"]=="active" and ((pair[0] in c["sides"]["attacker"] and pair[1] in c["sides"]["defender"]) or (pair[1] in c["sides"]["attacker"] and pair[0] in c["sides"]["defender"])) for c in conflicts.values())
            if (status=="war")!=war:raise DiplomacyError("relation contradicts conflict state")
        occupations={}
        for o in x["occupations"]:
            key=(o.get("entityKind"),o.get("entityId"));runtime=self.provinces if key[0]=="province" else self.settlements if key[0]=="settlement" else None;c=conflicts.get(o.get("conflictId"))
            entity=runtime.lookup(key[1]) if runtime else None
            if key in occupations or c is None or c["status"]!="active" or entity is None or (entity.legal_owner_polity_id,entity.controller_polity_id)!=(o.get("legalOwnerPolityId"),o.get("controllerPolityId")):raise DiplomacyError("occupation contradicts authoritative territory")
            occupations[key]=copy.deepcopy(dict(o))
        events=[]
        for seq,e in enumerate(x["events"],1):
            if not isinstance(e,Mapping) or e.get("sequence")!=seq or tuple(e.get("consumers",()))!=EVENT_CONSUMERS:raise DiplomacyError("invalid deterministic event ordering")
            events.append(DiplomaticEvent(seq,e.get("kind"),e.get("conflictId"),tuple(e.get("polityIds",())),e.get("entityKind"),e.get("entityId"),e.get("controllerPolityId")))
        if x.get("nextEventSequence")!=len(events)+1:raise DiplomacyError("invalid next event sequence")
        return rel,conflicts,occupations,copy.deepcopy(x["peaceRecords"]),events
    def restore(self,x):
        self._relations,self._conflicts,self._occupations,self._peace,self._events=self.validate_snapshot(x);self._next=len(self._events)+1

class DiplomacySaveAdapter:
    def __init__(self,runtime,world_state):self.runtime,self.world_state=runtime,copy.deepcopy(dict(world_state))
    def capture_world(self):d=copy.deepcopy(self.world_state);d[DIPLOMACY_WORLD_STATE_KEY]=self.runtime.snapshot();return d
    def migrate_legacy_world(self,x):
        if not isinstance(x,Mapping):raise DiplomacyError("legacy world state must be an object")
        d=copy.deepcopy(dict(x));d.setdefault(DIPLOMACY_WORLD_STATE_KEY,self.runtime.snapshot());self.validate_world(d);return d
    def validate_world(self,x):
        if not isinstance(x,Mapping) or DIPLOMACY_WORLD_STATE_KEY not in x:raise DiplomacyError("world state is missing diplomacyState")
        self.runtime.validate_snapshot(x[DIPLOMACY_WORLD_STATE_KEY])
    def reconstruct(self,x):self.validate_world(x);return copy.deepcopy(x[DIPLOMACY_WORLD_STATE_KEY])
    def activate(self,x,reconstructed):
        if reconstructed!=x[DIPLOMACY_WORLD_STATE_KEY]:raise DiplomacyError("reconstructed diplomacy state mismatch")
        self.runtime.restore(reconstructed);self.world_state=copy.deepcopy(dict(x))
