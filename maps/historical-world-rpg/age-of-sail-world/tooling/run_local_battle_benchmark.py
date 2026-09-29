#!/usr/bin/env python3
"""Run one or all deterministic local-battle performance profiles."""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent / "_shared" / "engine"))
import local_battle_benchmark as benchmark  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=ROOT / "scenario/benchmarks/local-battle.json")
    parser.add_argument("--profile", choices=("all", "maximum_land", "maximum_naval", "maximum_mixed"), default="all")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    profiles = benchmark.load_profiles(args.config)
    selected = profiles.values() if args.profile == "all" else (profiles[args.profile],)
    results = [benchmark.run(profile) for profile in selected]
    document = {"format": "warcraftmap_local_battle_suite_v1", "passed": all(item["passed"] for item in results), "results": results}
    text = json.dumps(document, sort_keys=True, separators=(",", ":")) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    sys.stdout.write(text)
    if document["passed"]:
        return 0
    return 2 if any(item["status"] == "performance_budget_failure" for item in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
