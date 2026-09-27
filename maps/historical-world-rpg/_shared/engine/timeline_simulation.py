"""Deterministic, Warcraft-independent long-timeline simulation harness."""
from __future__ import annotations
import copy, hashlib, json, re
from dataclasses import dataclass
from typing import Any, Callable, Iterable, Mapping

SYSTEM_ORDER=("world","technology_institutions","economy","quests_events","military","government","persistence")
CHECKPOINT_FORMAT="warcraftmap_timeline_checkpoint_v1"
FIXTURE_FORMAT="warcraftmap_timeline_fixture_v1"
_ID=re.compile(r"^[a-z][a-z0-9_]*$")
_TRANSIENT=re.compile(r"handle|widget",re.I)

class FixtureError(ValueError): pass

@dataclass(frozen=True)
class StepContext:
    seed:int; previous_time:int; time:int; delta:int; system:str
    def random_int(self,entity_id:str,stream:str,minimum:int,maximum:int)->int:
        if maximum<minimum: raise ValueError("maximum must not be less than minimum")
        raw=f"{self.seed}|{self.time}|{self.system}|{entity_id}|{stream}".encode()
        return minimum+int.from_bytes(hashlib.sha256(raw).digest()[:8],"big")%(maximum-minimum+1)

@dataclass(frozen=True)
class Diagnostic:
    time:int; system:str; entity_id:str; invariant:str; message:str
    def to_dict(self):
        return {"time":self.time,"system":self.system,"entityId":self.entity_id,"invariant":self.invariant,"message":self.message}

class SimulationFailure(RuntimeError):
    def __init__(self,diagnostic): super().__init__(diagnostic.message); self.diagnostic=diagnostic

def canonical_bytes(value):
    try: return json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False).encode()
    except (TypeError,ValueError) as exc: raise FixtureError(f"state is not canonical JSON data: {exc}") from exc

def reject_transient_state(value,path="state"):
    if isinstance(value,Mapping):
        for key,child in value.items():
            if not isinstance(key,str): raise FixtureError(f"{path}: object keys must be strings")
            if _TRANSIENT.search(key): raise FixtureError(f"{path}.{key}: transient Warcraft handle state is forbidden")
            reject_transient_state(child,f"{path}.{key}")
    elif isinstance(value,list):
        for i,child in enumerate(value): reject_transient_state(child,f"{path}[{i}]")
    elif value is not None and not isinstance(value,(str,int,float,bool)):
        raise FixtureError(f"{path}: only JSON values are allowed")

Step=Callable[[dict[str,Any],StepContext],None]
Invariant=Callable[[Mapping[str,Any],StepContext],Diagnostic|None]

class TimelineHarness:
    def __init__(self,*,seed,start_time,state=None,fixture_hash=""):
        if isinstance(seed,bool) or not isinstance(seed,int): raise FixtureError("seed must be an integer")
        if isinstance(start_time,bool) or not isinstance(start_time,int): raise FixtureError("start time must be an integer")
        self.seed,self.time,self.fixture_hash=seed,start_time,fixture_hash
        self.state=copy.deepcopy(dict(state or {})); reject_transient_state(self.state); canonical_bytes(self.state)
        self._steps={name:[] for name in SYSTEM_ORDER}; self._invariants=[]; self.checkpoints={}
    def register_step(self,system,name,step):
        if system not in self._steps: raise FixtureError(f"unknown system {system!r}")
        if not isinstance(name,str) or not _ID.fullmatch(name): raise FixtureError("step name must be a stable snake_case ID")
        if any(n==name for n,_ in self._steps[system]): raise FixtureError(f"duplicate step {system}:{name}")
        self._steps[system].append((name,step))
    def register_invariant(self,name,invariant):
        if not isinstance(name,str) or not _ID.fullmatch(name): raise FixtureError("invariant name must be a stable snake_case ID")
        if any(n==name for n,_ in self._invariants): raise FixtureError(f"duplicate invariant {name!r}")
        self._invariants.append((name,invariant))
    def run(self,*,end_time,step_size,checkpoint_times=()):
        if isinstance(end_time,bool) or not isinstance(end_time,int) or end_time<self.time: raise FixtureError("end time must be an integer at or after current time")
        if isinstance(step_size,bool) or not isinstance(step_size,int) or step_size<=0: raise FixtureError("step size must be a positive integer")
        requested=set(checkpoint_times)
        if any(isinstance(t,bool) or not isinstance(t,int) or t<self.time or t>end_time for t in requested): raise FixtureError("checkpoint times must be integers within the run")
        if self.time in requested:self.checkpoints[self.time]=self.checkpoint()
        count=0
        while self.time<end_time:
            previous=self.time; self.time=min(self.time+step_size,end_time)
            for system in SYSTEM_ORDER:
                context=StepContext(self.seed,previous,self.time,self.time-previous,system)
                for _,callback in self._steps[system]: callback(self.state,context)
                reject_transient_state(self.state); canonical_bytes(self.state)
                for name,invariant in self._invariants:
                    diagnostic=invariant(self.state,context)
                    if diagnostic:
                        if diagnostic.invariant!=name: raise FixtureError(f"invariant {name!r} returned mismatched diagnostic")
                        raise SimulationFailure(diagnostic)
            count+=1
            if self.time in requested:self.checkpoints[self.time]=self.checkpoint()
        return self.summary(count)
    def checkpoint(self):
        value={"format":CHECKPOINT_FORMAT,"fixtureHash":self.fixture_hash,"seed":self.seed,"time":self.time,"state":copy.deepcopy(self.state)}
        reject_transient_state(value); canonical_bytes(value); return value
    @classmethod
    def from_checkpoint(cls,value,fixture_hash=""):
        if value.get("format")!=CHECKPOINT_FORMAT: raise FixtureError("unsupported timeline checkpoint format")
        if fixture_hash and value.get("fixtureHash")!=fixture_hash: raise FixtureError("checkpoint was created from a different fixture")
        if not isinstance(value.get("state"),dict): raise FixtureError("checkpoint state must be an object")
        return cls(seed=value.get("seed"),start_time=value.get("time"),state=value["state"],fixture_hash=value.get("fixtureHash",""))
    def summary(self,steps):
        digest=hashlib.sha256(canonical_bytes(self.state)).hexdigest()
        return {"status":"complete","seed":self.seed,"time":self.time,"steps":steps,"stateHash":digest,"state":copy.deepcopy(self.state)}
