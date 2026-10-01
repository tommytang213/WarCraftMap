#!/usr/bin/env python3
import argparse, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT.parent/"_shared"/"engine"))
import final_performance_budget as budgets

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--config",type=Path,default=ROOT/"scenario/benchmarks/final-budgets.json")
    parser.add_argument("--reports",type=Path,default=ROOT/"scenario/benchmarks/reports/final-measurements.json")
    parser.add_argument("--profile",choices=("development","minimum_target"),default="development")
    parser.add_argument("--output",type=Path)
    args=parser.parse_args()
    try:
        config=budgets.load(args.config); reports=json.loads(args.reports.read_text()); result=budgets.compare(config,args.profile,reports)
    except (budgets.BudgetConfigurationError, OSError, ValueError) as error:
        parser.error(str(error))
    text=budgets.canonical(result)+"\n"
    if args.output: args.output.parent.mkdir(parents=True,exist_ok=True); args.output.write_text(text)
    sys.stdout.write(text)
    return 0 if result["passed"] else 2
if __name__=="__main__": raise SystemExit(main())
