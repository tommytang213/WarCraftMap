#!/usr/bin/env python3
"""Run a validated deterministic campaign timeline fixture."""
from __future__ import annotations
import argparse, copy, hashlib, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT.parent/"_shared"/"engine"))
from timeline_simulation import *  # noqa

def read(path):
    try: value=json.loads(path.read_text(encoding="utf-8"))
    except (OSError,json.JSONDecodeError) as exc: raise FixtureError(f"cannot load fixture: {exc}") from exc
    if not isinstance(value,dict): raise FixtureError("fixture root must be an object")
    return value
def integer(value,label,positive=False):
    if isinstance(value,bool) or not isinstance(value,int) or (positive and value<=0): raise FixtureError(f"{label} must be {'a positive ' if positive else 'an '}integer")
def path(value,label):
    if not isinstance(value,list) or not value or not all(isinstance(x,str) and x for x in value): raise FixtureError(f"{label} must be a non-empty key array")
    return value
def resolve(state,keys):
    item=state
    for key in keys[:-1]:
        if not isinstance(item,dict) or key not in item: raise FixtureError(f"state path {keys!r} does not exist")
        item=item[key]
    if not isinstance(item,dict) or keys[-1] not in item: raise FixtureError(f"state path {keys!r} does not exist")
    return item,keys[-1]
def validate(data):
    if data.get("format")!=FIXTURE_FORMAT: raise FixtureError("unsupported timeline fixture format")
    timeline=data.get("timeline")
    if not isinstance(timeline,dict): raise FixtureError("timeline must be an object")
    integer(timeline.get("start"),"timeline.start"); integer(timeline.get("end"),"timeline.end"); integer(timeline.get("step"),"timeline.step",True)
    if timeline["end"]<timeline["start"]: raise FixtureError("timeline.end must not precede start")
    if not isinstance(data.get("initialState"),dict): raise FixtureError("initialState must be an object")
    reject_transient_state(data["initialState"])
    systems=data.get("systems",{})
    if not isinstance(systems,dict): raise FixtureError("systems must be an object")
    if set(systems)-set(SYSTEM_ORDER): raise FixtureError(f"unknown system {sorted(set(systems)-set(SYSTEM_ORDER))[0]!r}")
    for system,operations in systems.items():
        if not isinstance(operations,list): raise FixtureError(f"systems.{system} must be an array")
        names=set()
        for op in operations:
            if not isinstance(op,dict) or not isinstance(op.get("id"),str) or op["id"] in names: raise FixtureError(f"systems.{system} operation IDs must be unique strings")
            names.add(op["id"]); path(op.get("path"),f"operation {op['id']}.path")
            if op.get("kind")=="increment":
                if isinstance(op.get("amountPerTime"),bool) or not isinstance(op.get("amountPerTime"),(int,float)): raise FixtureError(f"operation {op['id']} amountPerTime must be numeric")
            elif op.get("kind")=="scheduled_events":
                if not isinstance(op.get("events"),list): raise FixtureError(f"operation {op['id']} events must be an array")
                event_ids=set()
                for event in op["events"]:
                    if not isinstance(event,dict) or not isinstance(event.get("id"),str) or event["id"] in event_ids: raise FixtureError(f"operation {op['id']} event IDs must be unique strings")
                    event_ids.add(event["id"]); integer(event.get("time"),"event.time"); integer(event.get("priority",0),"event.priority")
            else: raise FixtureError(f"operation {op['id']} has unsupported kind")
    if not isinstance(data.get("invariants",[]),list): raise FixtureError("invariants must be an array")
    return hashlib.sha256(canonical_bytes(data)).hexdigest()
def configure(harness,data):
    for system,operations in data.get("systems",{}).items():
        for op in operations:
            keys=op["path"]
            if op["kind"]=="increment":
                amount=op["amountPerTime"]
                def callback(state,ctx,keys=keys,amount=amount):
                    parent,key=resolve(state,keys)
                    if isinstance(parent[key],bool) or not isinstance(parent[key],(int,float)): raise FixtureError("increment target must be numeric")
                    parent[key]+=amount*ctx.delta
            else:
                events=sorted(op["events"],key=lambda x:(x["time"],x.get("priority",0),x["id"]))
                def callback(state,ctx,keys=keys,events=events):
                    parent,key=resolve(state,keys)
                    if not isinstance(parent[key],list): raise FixtureError("scheduled event target must be an array")
                    parent[key].extend(copy.deepcopy(e) for e in events if ctx.previous_time<e["time"]<=ctx.time)
            harness.register_step(system,op["id"],callback)
    for i,spec in enumerate(data.get("invariants",[])):
        if not isinstance(spec,dict) or spec.get("kind") not in ("non_negative","maximum"): raise FixtureError(f"invariants[{i}] has unsupported kind")
        name,entity,keys=spec.get("id"),spec.get("entityId"),path(spec.get("path"),f"invariants[{i}].path")
        if not isinstance(name,str) or not isinstance(entity,str): raise FixtureError(f"invariants[{i}] requires id and entityId")
        limit=spec.get("value",0)
        def invariant(state,ctx,spec=spec,name=name,entity=entity,keys=keys,limit=limit):
            parent,key=resolve(state,keys); value=parent[key]
            bad=isinstance(value,bool) or not isinstance(value,(int,float)) or (spec["kind"]=="non_negative" and value<0) or (spec["kind"]=="maximum" and value>limit)
            return Diagnostic(ctx.time,ctx.system,entity,name,f"{name} failed for {entity}: value {value!r}") if bad else None
        harness.register_invariant(name,invariant)
def write(path,value): path.write_bytes(canonical_bytes(value)+b"\n")
def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__); p.add_argument("fixture",type=Path); p.add_argument("--seed",type=int); p.add_argument("--start",type=int); p.add_argument("--end",type=int); p.add_argument("--step",type=int); p.add_argument("--checkpoint-at",type=int,action="append",default=[]); p.add_argument("--checkpoint-out",type=Path); p.add_argument("--resume",type=Path); p.add_argument("--compare-uninterrupted",action="store_true"); p.add_argument("--summary-out",type=Path); p.add_argument("--max-diagnostics",type=int,default=1); a=p.parse_args(argv)
    try:
        if a.max_diagnostics<1: raise FixtureError("max-diagnostics must be positive")
        data=read(a.fixture.resolve()); digest=validate(data); cfg=data["timeline"]; seed=a.seed if a.seed is not None else data.get("seed",0); start=a.start if a.start is not None else cfg["start"]; end=a.end if a.end is not None else cfg["end"]; step=a.step if a.step is not None else cfg["step"]
        if a.resume:
            harness=TimelineHarness.from_checkpoint(read(a.resume.resolve()),digest)
            if a.seed is not None and a.seed!=harness.seed: raise FixtureError("seed does not match checkpoint")
        else: harness=TimelineHarness(seed=seed,start_time=start,state=data["initialState"],fixture_hash=digest)
        configure(harness,data); summary=harness.run(end_time=end,step_size=step,checkpoint_times=a.checkpoint_at)
        if a.checkpoint_out:
            if a.checkpoint_at:
                selected=a.checkpoint_at[-1]
                if selected not in harness.checkpoints: raise FixtureError(f"checkpoint time {selected} is not on a simulation step boundary")
                checkpoint=harness.checkpoints[selected]
            else: checkpoint=harness.checkpoint()
            write(a.checkpoint_out,checkpoint)
        if a.compare_uninterrupted:
            baseline=TimelineHarness(seed=harness.seed,start_time=cfg["start"],state=data["initialState"],fixture_hash=digest); configure(baseline,data); expected=baseline.run(end_time=end,step_size=step); summary["resumeEquivalent"]=expected["stateHash"]==summary["stateHash"]
            if not summary["resumeEquivalent"]: raise FixtureError("resumed result differs from uninterrupted execution")
        if a.summary_out: write(a.summary_out,summary)
        print(canonical_bytes(summary).decode()); return 0
    except SimulationFailure as exc: result={"status":"failed","diagnostics":[exc.diagnostic.to_dict()]}
    except FixtureError as exc: result={"status":"invalid","diagnostics":[{"message":str(exc)}]}
    print(canonical_bytes(result).decode(),file=sys.stderr); return 1
if __name__=="__main__": raise SystemExit(main())
