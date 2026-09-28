"""Scenario-neutral authoritative polity runtime state."""
from __future__ import annotations
import copy, re
from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping

POLITY_STATE_SCHEMA_VERSION=1
POLITY_WORLD_STATE_KEY="polityState"
SOVEREIGN_TIERS=frozenset({"none","knight","baron","count","marquess","duke","prince","king","emperor"})
_ID=re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")
class PolityError(ValueError): pass

@dataclass(frozen=True)
class PolityDefinition:
    id:str; name:str; adjective:str; sovereign_tier:str; native_sovereign_title:str
    capital_settlement_id:str; province_ids:tuple[str,...]
@dataclass(frozen=True)
class PolityView:
    definition:PolityDefinition; active:bool
    @property
    def id(self): return self.definition.id

def _id(value,context):
    if not isinstance(value,str) or not _ID.fullmatch(value): raise PolityError(f"{context}: invalid stable ID {value!r}")
    return value
def _index(values,domain):
    if not isinstance(values,list): raise PolityError(f"{domain}: must be an array")
    result={}
    for value in values:
        if not isinstance(value,Mapping): raise PolityError(f"{domain}: every entry must be an object")
        ident=_id(value.get("id"),f"{domain}.id")
        if ident in result: raise PolityError(f"{domain}: duplicate ID {ident!r}")
        result[ident]=value
    return result
def _text(value,context):
    if not isinstance(value,str) or not value.strip(): raise PolityError(f"{context}: must be non-empty text")
    return value
def _catalog(world):
    if not isinstance(world,Mapping): raise PolityError("world definitions must be an object")
    settlements=_index(world.get("settlements"),"settlements"); provinces=_index(world.get("provinces"),"provinces")
    records=world.get("polities")
    if not isinstance(records,list): raise PolityError("polities: must be an array")
    seen=set(); result=[]
    for record in records:
        if not isinstance(record,Mapping): raise PolityError("polities: every entry must be an object")
        ident=_id(record.get("id"),"polities.id")
        if ident in seen: raise PolityError(f"polities: duplicate ID {ident!r}")
        seen.add(ident); tier=record.get("sovereignTier")
        if tier not in SOVEREIGN_TIERS: raise PolityError(f"polity {ident}: invalid sovereign tier {tier!r}")
        capital=_id(record.get("capitalSettlementId"),f"polity {ident}.capitalSettlementId")
        if capital not in settlements: raise PolityError(f"polity {ident}: missing capital settlement {capital!r}")
        refs=record.get("provinceIds")
        if not isinstance(refs,list): raise PolityError(f"polity {ident}.provinceIds: must be an array")
        province_ids=[]
        for province_id in refs:
            province_id=_id(province_id,f"polity {ident}.provinceIds")
            if province_id in province_ids: raise PolityError(f"polity {ident}: duplicate province reference {province_id!r}")
            if province_id not in provinces: raise PolityError(f"polity {ident}: missing province {province_id!r}")
            if provinces[province_id].get("legalOwnerPolityId")!=ident: raise PolityError(f"polity {ident}: province {province_id!r} has an incompatible legal owner")
            province_ids.append(province_id)
        result.append(PolityDefinition(ident,_text(record.get("name"),f"polity {ident}.name"),_text(record.get("adjective"),f"polity {ident}.adjective"),tier,_text(record.get("nativeSovereignTitle"),f"polity {ident}.nativeSovereignTitle"),capital,tuple(province_ids)))
    if not result: raise PolityError("at least one polity is required")
    return tuple(sorted(result,key=lambda item:item.id))

class PolityRuntime:
    """Immutable scenario definitions plus authoritative mutable lifecycle state."""
    def __init__(self,world_definitions):
        self._definitions=_catalog(copy.deepcopy(dict(world_definitions))); self._rebuild_indexes()
        self._active={item.id:True for item in self._definitions}
    def _rebuild_indexes(self): self._by_id=MappingProxyType({item.id:item for item in self._definitions})
    @property
    def definitions(self): return self._definitions
    def ids(self,active_only=False): return tuple(x.id for x in self._definitions if not active_only or self._active[x.id])
    def lookup(self,polity_id):
        definition=self._by_id.get(polity_id)
        return None if definition is None else PolityView(definition,self._active[polity_id])
    def require(self,polity_id):
        result=self.lookup(polity_id)
        if result is None: raise PolityError(f"unknown polity {polity_id!r}")
        return result
    def enumerate(self,active_only=False): return tuple(self.require(x) for x in self.ids(active_only))
    def set_active(self,polity_id,active):
        if not isinstance(active,bool): raise PolityError("active status must be boolean")
        self.require(polity_id); changed=self._active[polity_id]!=active; self._active[polity_id]=active; return changed
    def snapshot(self): return {"schemaVersion":1,"polities":[{"id":x,"active":self._active[x]} for x in self.ids()]}
    def validate_snapshot(self,candidate):
        if not isinstance(candidate,Mapping) or candidate.get("schemaVersion")!=1: raise PolityError("polity state schemaVersion must be 1")
        records=candidate.get("polities")
        if not isinstance(records,list): raise PolityError("polity state polities must be an array")
        restored={}
        for record in records:
            if not isinstance(record,Mapping) or set(record)!={"id","active"}: raise PolityError("polity state entries must contain only id and active")
            ident=_id(record.get("id"),"polity state id")
            if ident in restored: raise PolityError(f"polity state: duplicate ID {ident!r}")
            if ident not in self._by_id: raise PolityError(f"polity state: incompatible polity {ident!r}")
            if not isinstance(record.get("active"),bool): raise PolityError(f"polity state {ident}.active must be boolean")
            restored[ident]=record["active"]
        missing=set(self._by_id)-set(restored)
        if missing: raise PolityError(f"polity state: missing polity {sorted(missing)[0]!r}")
        return restored
    def restore(self,candidate):
        restored=self.validate_snapshot(candidate); self._active=restored; self._rebuild_indexes()

class PolitySaveAdapter:
    """CampaignSaveManager callback adapter; snapshots contain stable IDs only."""
    def __init__(self,runtime,world_state): self.runtime=runtime; self.world_state=copy.deepcopy(dict(world_state))
    def capture_world(self):
        result=copy.deepcopy(self.world_state); result[POLITY_WORLD_STATE_KEY]=self.runtime.snapshot(); return result
    def migrate_legacy_world(self,candidate):
        if not isinstance(candidate,Mapping): raise PolityError("legacy world state must be an object")
        migrated=copy.deepcopy(dict(candidate))
        if POLITY_WORLD_STATE_KEY not in migrated: migrated[POLITY_WORLD_STATE_KEY]=self.runtime.snapshot()
        self.validate_world(migrated); return migrated
    def validate_world(self,candidate):
        if not isinstance(candidate,Mapping) or POLITY_WORLD_STATE_KEY not in candidate: raise PolityError(f"world state is missing {POLITY_WORLD_STATE_KEY}")
        self.runtime.validate_snapshot(candidate[POLITY_WORLD_STATE_KEY])
    def reconstruct(self,candidate):
        self.validate_world(candidate); return self.runtime.validate_snapshot(candidate[POLITY_WORLD_STATE_KEY])
    def activate(self,candidate,reconstructed):
        if dict(reconstructed)!=self.runtime.validate_snapshot(candidate[POLITY_WORLD_STATE_KEY]): raise PolityError("reconstructed polity indexes do not match candidate state")
        self.runtime.restore(candidate[POLITY_WORLD_STATE_KEY]); self.world_state=copy.deepcopy(dict(candidate))
