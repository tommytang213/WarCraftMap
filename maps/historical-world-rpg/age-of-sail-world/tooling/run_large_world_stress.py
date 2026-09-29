#!/usr/bin/env python3
"""Run a configured synthetic large-world profile and print canonical JSON."""
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT.parent/"_shared"/"engine"))
import large_world_stress as stress
def main(argv=None):
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("--config",type=Path,default=ROOT/"scenario/benchmarks/large-world.json");parser.add_argument("--profile",default="small_correctness");parser.add_argument("--summary-out",type=Path);parser.add_argument("--max-diagnostics",type=int,default=3);args=parser.parse_args(argv)
 try: result=stress.run_profile(stress.load_profiles(args.config)[1][args.profile],args.max_diagnostics)
 except (stress.StressError,KeyError) as exc: parser.error(str(exc))
 output=json.dumps(result,sort_keys=True,separators=(",",":"))+"\n"
 if args.summary_out: args.summary_out.parent.mkdir(parents=True,exist_ok=True);args.summary_out.write_text(output)
 sys.stdout.write(output);return 0 if result["passed"] else 1
if __name__=="__main__":raise SystemExit(main())
