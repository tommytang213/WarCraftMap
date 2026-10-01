#!/usr/bin/env python3
import argparse, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT.parent/"_shared"/"engine"))
import campaign_save_stress as stress, large_world_stress as worlds

def main():
    p=argparse.ArgumentParser(); p.add_argument("--profile",default="representative"); p.add_argument("--summary-out",type=Path); a=p.parse_args()
    _,wp=worlds.load_profiles(ROOT/"scenario/benchmarks/large-world.json")
    profiles=stress.load_profiles(ROOT/"scenario/benchmarks/campaign-save-stress.json",wp)
    if a.profile not in profiles: p.error("unknown profile")
    result=stress.run(a.profile,profiles[a.profile],wp[profiles[a.profile]["worldProfile"]]); encoded=json.dumps(result,sort_keys=True,separators=(",",":"))
    if a.summary_out: a.summary_out.parent.mkdir(parents=True,exist_ok=True); a.summary_out.write_text(encoded+"\n",encoding="utf-8")
    print(encoded); return 0 if result["passed"] else 1
if __name__=="__main__": raise SystemExit(main())
