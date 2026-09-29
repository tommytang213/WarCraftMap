"""Deterministic, scenario-neutral performance stress harness."""
import copy,hashlib,json,math,statistics,time
from dataclasses import dataclass
from pathlib import Path
METRICS=("simulation_step_ms","save_ms","load_ms","serialized_state_bytes","active_warcraft_objects","visible_operation_hitch_ms")
class ConfigurationError(ValueError):pass
class CorrectnessError(RuntimeError):pass
@dataclass(frozen=True)
class Profile:id:str;seed:int;warmups:int;repeats:int;workload:dict;thresholds:dict;max_cv:float
def canonical(v):return json.dumps(v,sort_keys=True,separators=(",",":"),allow_nan=False).encode()
def load_configuration(path):
 d=json.loads(Path(path).read_text());p={}; req={"polities","settlements","militaryForces","characters","relationships","localRepresentations","simulationSteps","visibleOperations"}
 if d.get("format")!="warcraftmap_performance_config_v1" or d.get("fixtureVersion")!=1:raise ConfigurationError("unsupported configuration")
 for name,r in d.get("profiles",{}).items():
  w=r.get("workload",{});t=r.get("thresholds",{});cv=r.get("maximumCoefficientOfVariation")
  if set(w)!=req or set(t)!=set(METRICS):raise ConfigurationError(f"{name}: incorrect workload or threshold fields")
  if any(isinstance(v,bool) or not isinstance(v,int) or v<0 for v in w.values()) or any(w[k]<1 for k in req-{"localRepresentations"}):raise ConfigurationError(f"{name}: invalid workload")
  if w["localRepresentations"]>w["settlements"]+w["militaryForces"]+w["characters"]:raise ConfigurationError(f"{name}: local representations exceed abstract state")
  if any(isinstance(v,bool) or not isinstance(v,(int,float)) or v<=0 or not math.isfinite(v) for v in t.values()) or not isinstance(cv,(int,float)) or not 0<=cv<=1:raise ConfigurationError(f"{name}: invalid thresholds")
  p[name]=Profile(name,r["seed"],r["warmupRuns"],r["measuredRuns"],w,{k:float(v) for k,v in t.items()},float(cv))
 if not p:raise ConfigurationError("profiles required")
 return d,p
def load_json(path):
 return json.loads(Path(path).read_text())

def validate_snapshot(v,path="fixture"):
 if isinstance(v,dict):
  for k,x in v.items():
   if not isinstance(k,str) or "handle" in k.lower() or "widget" in k.lower():raise CorrectnessError(f"{path}.{k}: transient Warcraft handle or unstable key")
   validate_snapshot(x,f"{path}.{k}")
 elif isinstance(v,list):
  for i,x in enumerate(v):validate_snapshot(x,f"{path}[{i}]")
 elif v is not None and not isinstance(v,(str,int,float,bool)):raise CorrectnessError(f"{path}: non-JSON value")
def generate_fixture(p):
 w=p.workload;s=p.seed
 pol={f"polity_{i:05d}":{"treasury":(s+i*7919)%100000} for i in range(w["polities"])}
 sett={f"settlement_{i:06d}":{"ownerId":f"polity_{i%w['polities']:05d}"} for i in range(w["settlements"])}
 forces={f"force_{i:06d}":{"ownerId":f"polity_{i%w['polities']:05d}"} for i in range(w["militaryForces"])}
 chars={f"character_{i:06d}":{"polityId":f"polity_{i%w['polities']:05d}"} for i in range(w["characters"])}
 rel=[{"id":f"relationship_{i:07d}","fromId":f"character_{i%w['characters']:06d}","toId":f"character_{(i*31+1)%w['characters']:06d}"} for i in range(w["relationships"])]
 ids=list(sett)+list(forces)+list(chars);local=[{"representationId":f"representation_{i:06d}","entityId":ids[i]} for i in range(w["localRepresentations"])]
 f={"format":"warcraftmap_performance_fixture_v1","fixtureVersion":1,"seed":s,"authoritativeState":{"tick":0,"polities":pol,"settlements":sett,"militaryForces":forces,"characters":chars,"relationships":rel},"localWarcraftRepresentations":local};validate_snapshot(f);canonical(f);return f
def aggregate(samples):
 out={}
 for m in METRICS:
  v=samples[m];mean=statistics.fmean(v);out[m]={"median":statistics.median(v),"p95":sorted(v)[math.ceil(.95*len(v))-1],"minimum":min(v),"maximum":max(v),"coefficientOfVariation":statistics.pstdev(v)/mean if mean else 0,"sampleCount":len(v)}
 return out
def measure_once(f,p,timer=time.perf_counter_ns):
 state=copy.deepcopy(f["authoritativeState"]);start=timer()
 for step in range(p.workload["simulationSteps"]):
  state["tick"]+=1
  for x in state["polities"].values():x["treasury"]+=step
 sim=(timer()-start)/1e6;start=timer();raw=canonical(state);save=(timer()-start)/1e6;start=timer();loaded=json.loads(raw);load=(timer()-start)/1e6
 if loaded!=state:raise CorrectnessError("save round trip mismatch")
 start=timer();sum(len(x["entityId"]) for _ in range(p.workload["visibleOperations"]) for x in f["localWarcraftRepresentations"]);hitch=(timer()-start)/1e6
 return dict(zip(METRICS,(sim/p.workload["simulationSteps"],save,load,float(len(raw)),float(len(f["localWarcraftRepresentations"])),hitch/p.workload["visibleOperations"])))
def run(p,build,measurement=measure_once):
 f=generate_fixture(p);base={"format":"warcraftmap_performance_result_v1","fixtureVersion":1,"fixtureHash":hashlib.sha256(canonical(f)).hexdigest(),"build":build,"profile":p.id,"workload":p.workload}
 try:
  for _ in range(p.warmups):measurement(f,p)
  samples={m:[] for m in METRICS}
  for _ in range(p.repeats):
   got=measurement(f,p)
   for m in METRICS:samples[m].append(float(got[m]))
  a=aggregate(samples);fail=[]
  for m in METRICS:
   if a[m]["p95"]>p.thresholds[m]:fail.append({"kind":"budget","metric":m,"observed":a[m]["p95"],"threshold":p.thresholds[m],"message":f"{m} p95 exceeds budget"})
   if m.endswith("_ms") and a[m]["coefficientOfVariation"]>p.max_cv:fail.append({"kind":"variance","metric":m,"message":f"{m} variance exceeds limit; rerun on idle machine"})
  return {**base,"runRules":{"warmupRuns":p.warmups,"measuredRuns":p.repeats,"aggregation":"median_and_nearest_rank_p95","maximumCoefficientOfVariation":p.max_cv},"measurements":a,"thresholds":p.thresholds,"status":"performance_budget_failure" if fail else "pass","passed":not fail,"failures":fail}
 except Exception as e:return {**base,"status":"correctness_failure","passed":False,"failures":[{"kind":"correctness","message":str(e)}]}
