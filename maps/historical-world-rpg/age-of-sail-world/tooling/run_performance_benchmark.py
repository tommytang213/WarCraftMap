#!/usr/bin/env python3
import argparse,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT.parent/"_shared"/"engine"));import performance_benchmark as b
def main():
 p=argparse.ArgumentParser();p.add_argument("--config",type=Path,default=ROOT/"scenario/benchmarks/performance.json");p.add_argument("--profile",default="representative_development");p.add_argument("--output",type=Path);a=p.parse_args()
 try:
  _,profiles=b.load_configuration(a.config);profile=profiles[a.profile]
 except (b.ConfigurationError,KeyError) as e:p.error(str(e))
 def git(*x):
  r=subprocess.run(["git",*x],cwd=ROOT,text=True,capture_output=True);return r.stdout.strip() if r.returncode==0 else "unknown"
 result=b.run(profile,{"revision":git("rev-parse","HEAD"),"dirty":bool(git("status","--porcelain")),"python":sys.version.split()[0]});text=json.dumps(result,sort_keys=True,separators=(",",":"))+"\n"
 if a.output:a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(text)
 sys.stdout.write(text);return 0 if result["passed"] else (2 if result["status"]=="performance_budget_failure" else 1)
if __name__=="__main__":raise SystemExit(main())
