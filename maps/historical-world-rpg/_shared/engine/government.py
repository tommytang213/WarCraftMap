"""Authoritative deterministic government simulation."""
import copy,re
from dataclasses import dataclass
from typing import Mapping
import economy
GOVERNMENT_WORLD_STATE_KEY="governmentState";RANK_ORDER={x:i for i,x in enumerate(("none","knight","baron","count","marquess","duke","prince","king","emperor"))};ID=re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")
class GovernmentError(ValueError):pass
@dataclass(frozen=True)
class GovernmentEvent:
 sequence:int;kind:str;subject_id:str;changes:tuple
 def to_dict(self):return {"sequence":self.sequence,"kind":self.kind,"subjectId":self.subject_id,"changes":[{"field":f,"from":a,"to":b} for f,a,b in self.changes]}
def index(xs,name):
 if not isinstance(xs,list):raise GovernmentError(name+" must be an array")
 out={}
 for x in xs:
  i=x.get("id") if isinstance(x,Mapping) else None
  if not isinstance(i,str) or not ID.fullmatch(i) or i in out:raise GovernmentError(name+" has invalid or duplicate ID")
  out[i]=copy.deepcopy(dict(x))
 return out
class GovernmentRuntime:
 def __init__(self,w,*,active_polity_ids=None,active_character_ids=None,economic_rules=()):
  self.styles=index(w.get("titleStyles",[]),"titleStyles");self.polities=set(index(w.get("polities",[]),"polities"));self.characters=set(index(w.get("characters",[]),"characters"));self.territories={"province":set(index(w.get("provinces",[]),"provinces")),"settlement":set(index(w.get("settlements",[]),"settlements"))};self.rules=index(list(economic_rules),"economicRules")
  self.active={"polity":self.polities if active_polity_ids is None else set(active_polity_ids),"character":self.characters if active_character_ids is None else set(active_character_ids)}
  self.grants=index(w.get("titleGrants",[]),"titleGrants");self.holdings=index(w.get("territorialHoldings",[]),"territorialHoldings");self.allegiances=index(w.get("allegiances",[]),"allegiances");self.events=[];self.next=1;self._validate(self.grants,self.holdings,self.allegiances)
 def _cycles(self,d,f):
  for start in d:
   seen=set();x=start
   while x is not None:
    if x in seen:raise GovernmentError("hierarchy cycle")
    seen.add(x);x=d[x].get(f)
 def _validate(self,g,h,a):
  for i,x in g.items():
   s=x.get("titleStyleId");p=x.get("grantorTitleId");holder=x.get("holder")
   if s not in self.styles or not isinstance(holder,Mapping) or holder.get("id") not in self.active.get(holder.get("kind"),set()) or x.get("allegiancePolityId") not in self.active["polity"]:raise GovernmentError("missing or inactive title participant")
   if not isinstance(x.get("sovereign"),bool) or x["sovereign"]==(p is not None):raise GovernmentError("contradictory sovereignty")
   if p is not None and (p not in g or RANK_ORDER[self.styles[s]["rankTier"]]>=RANK_ORDER[self.styles[g[p]["titleStyleId"]]["rankTier"]]):raise GovernmentError("grantor lacks authority for rank")
  self._cycles(g,"grantorTitleId");seen=set()
  for i,x in h.items():
   t=x.get("territory");p=x.get("overlordHoldingId")
   if not isinstance(t,Mapping) or t.get("id") not in self.territories.get(t.get("kind"),set()) or (t["kind"],t["id"]) in seen:raise GovernmentError("invalid territory")
   seen.add((t["kind"],t["id"]))
   for f in ("controllerPolityId","governingPolityId","sovereignPolityId"):
    if x.get(f) not in self.active["polity"]:raise GovernmentError("missing or inactive polity")
   for f in ("autonomyPercent","overlordTaxRatePercent","upkeepRatePercent"):
    v=x.get(f)
    if isinstance(v,bool) or not isinstance(v,(int,float)) or v<0 or v>100 or f=="upkeepRatePercent" and v==0:raise GovernmentError("invalid percentage")
   if p is None and (x["overlordTaxRatePercent"] or x.get("obligations") or x["sovereignPolityId"]!=x["governingPolityId"]):raise GovernmentError("contradictory independent sovereignty")
   if p is not None and p not in h:raise GovernmentError("missing overlord")
  self._cycles(h,"overlordHoldingId")
  for x in h.values():
   if x.get("overlordHoldingId") and x["sovereignPolityId"]!=h[x["overlordHoldingId"]]["sovereignPolityId"]:raise GovernmentError("contradictory sovereignty")
 def _commit(self,g,h,a,kind,i,changes,cat=None,state=None):
  self._validate(g,h,a);e=GovernmentEvent(self.next,kind,i,tuple(changes));self.grants,self.holdings,self.allegiances=g,h,a;self.events.append(e);self.next+=1;return e,cat,state
 def grant_title(self,x):
  g=copy.deepcopy(self.grants);i=x["id"]
  if i in g:raise GovernmentError("duplicate title")
  g[i]=copy.deepcopy(x);return self._commit(g,copy.deepcopy(self.holdings),copy.deepcopy(self.allegiances),"title_granted",i,(("title",None,x),))
 def revoke_title(self,i):
  if any(x.get("grantorTitleId")==i for x in self.grants.values()):raise GovernmentError("title has subordinates")
  g=copy.deepcopy(self.grants);old=g.pop(i);return self._commit(g,copy.deepcopy(self.holdings),copy.deepcopy(self.allegiances),"title_revoked",i,(("title",old,None),))
 def transfer_title(self,i,holder):
  g=copy.deepcopy(self.grants);old=g[i]["holder"];g[i]["holder"]=copy.deepcopy(holder);return self._commit(g,copy.deepcopy(self.holdings),copy.deepcopy(self.allegiances),"title_transferred",i,(("holder",old,holder),))
 def update_control(self,i,*,controller_polity_id,governing_polity_id=None):
  h=copy.deepcopy(self.holdings);old=copy.deepcopy(h[i]);h[i]["controllerPolityId"]=controller_polity_id
  if governing_polity_id is not None:h[i]["governingPolityId"]=governing_polity_id
  return self._commit(copy.deepcopy(self.grants),h,copy.deepcopy(self.allegiances),"holding_control_changed",i,tuple((f,old.get(f),h[i].get(f)) for f in ("controllerPolityId","governingPolityId") if old.get(f)!=h[i].get(f)))
 def set_autonomy(self,i,value):
  h=copy.deepcopy(self.holdings);old=h[i]["autonomyPercent"];h[i]["autonomyPercent"]=value;return self._commit(copy.deepcopy(self.grants),h,copy.deepcopy(self.allegiances),"autonomy_changed",i,(("autonomyPercent",old,value),))
 def change_vassalage(self,i,overlord_holding_id,*,tax_rate_percent,obligations,**kw):
  h=copy.deepcopy(self.holdings);old=copy.deepcopy(h[i]);h[i].update({"overlordHoldingId":overlord_holding_id,"overlordTaxRatePercent":tax_rate_percent,"obligations":copy.deepcopy(obligations),"sovereignPolityId":h[overlord_holding_id]["sovereignPolityId"]});cat,state=self._sync(h,kw.get("economy_catalog"),kw.get("economy_state"));return self._commit(copy.deepcopy(self.grants),h,copy.deepcopy(self.allegiances),"vassalage_changed",i,(("holding",old,h[i]),),cat,state)
 def declare_independence(self,i,*,sovereign_polity_id=None,**kw):
  h=copy.deepcopy(self.holdings);old=copy.deepcopy(h[i]);h[i].pop("overlordHoldingId",None);h[i]["overlordTaxRatePercent"]=0;h[i]["obligations"]=[];h[i]["sovereignPolityId"]=sovereign_polity_id or h[i]["governingPolityId"];cat,state=self._sync(h,kw.get("economy_catalog"),kw.get("economy_state"));return self._commit(copy.deepcopy(self.grants),h,copy.deepcopy(self.allegiances),"independence_declared",i,(("holding",old,h[i]),),cat,state)
 def _sync(self,h,cat,state):
  if cat is None and state is None:return None,None
  cat,state=copy.deepcopy(cat),copy.deepcopy(state);managed={x["obligationId"] for x in self.rules.values()};desired={}
  for x in self.rules.values():
   if h[x["holdingId"]].get("overlordHoldingId") and h[x["holdingId"]]["overlordTaxRatePercent"]>0:
    y={k:x[k] for k in ("payerStoreId","payeeStoreId","currencyId","amountMinor","intervalTicks")};y["id"]=x["obligationId"];desired[y["id"]]=y
  cat["obligations"]=[x for x in cat["obligations"] if x["id"] not in managed]+list(desired.values());state["pendingObligations"]=[x for x in state.get("pendingObligations",[]) if x["obligationId"] not in managed]+[{"obligationId":i,"nextDueTick":state.get("currentTick",0)+x["intervalTicks"],"occurrencesSettled":0} for i,x in desired.items()];economy.validate_state(cat,state);return cat,state
 def snapshot(self):return {"schemaVersion":1,"nextEventSequence":self.next,"titleGrants":list(copy.deepcopy(self.grants).values()),"territorialHoldings":list(copy.deepcopy(self.holdings).values()),"allegiances":list(copy.deepcopy(self.allegiances).values()),"events":[x.to_dict() for x in self.events]}
 def restore(self,x):self.grants=index(x["titleGrants"],"titleGrants");self.holdings=index(x["territorialHoldings"],"territorialHoldings");self.allegiances=index(x["allegiances"],"allegiances");self._validate(self.grants,self.holdings,self.allegiances);self.next=x["nextEventSequence"];self.events=[GovernmentEvent(e["sequence"],e["kind"],e["subjectId"],tuple((c["field"],c.get("from"),c.get("to")) for c in e["changes"])) for e in x["events"]]
class GovernmentSaveAdapter:
 def __init__(self,runtime,world_state):self.runtime,self.world_state=runtime,copy.deepcopy(dict(world_state))
 def capture_world(self):x=copy.deepcopy(self.world_state);x[GOVERNMENT_WORLD_STATE_KEY]=self.runtime.snapshot();return x
 def migrate_legacy_world(self,x):y=copy.deepcopy(dict(x));y.setdefault(GOVERNMENT_WORLD_STATE_KEY,self.runtime.snapshot());return y
 def validate_world(self,x):self.runtime._validate(index(x[GOVERNMENT_WORLD_STATE_KEY]["titleGrants"],"titleGrants"),index(x[GOVERNMENT_WORLD_STATE_KEY]["territorialHoldings"],"territorialHoldings"),index(x[GOVERNMENT_WORLD_STATE_KEY]["allegiances"],"allegiances"))
 def reconstruct(self,x):self.validate_world(x);return copy.deepcopy(x[GOVERNMENT_WORLD_STATE_KEY])
 def activate(self,x,reconstructed):self.runtime.restore(reconstructed);self.world_state=copy.deepcopy(dict(x))
