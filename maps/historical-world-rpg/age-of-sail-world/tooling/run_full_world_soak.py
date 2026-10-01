#!/usr/bin/env python3
"""Run an Age of Sail authored-world soak profile and print canonical JSON."""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "_shared/engine"))
import full_world_soak


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=PROJECT / "scenario/benchmarks/full-world-soak.json")
    parser.add_argument("--profile", default="smoke")
    parser.add_argument("--summary-out", type=Path)
    parser.add_argument("--max-diagnostics", type=int, default=4)
    args = parser.parse_args(argv)
    config, sources, profiles = full_world_soak.load_config(args.config)
    if args.profile not in profiles:
        parser.error(f"unknown profile {args.profile!r}")
    if args.max_diagnostics <= 0:
        parser.error("--max-diagnostics must be positive")
    result = full_world_soak.run_profile(config, sources, profiles[args.profile], args.max_diagnostics)
    encoded = json.dumps(result, sort_keys=True, separators=(",", ":")) + "\n"
    if args.summary_out:
        args.summary_out.parent.mkdir(parents=True, exist_ok=True)
        args.summary_out.write_text(encoded)
    sys.stdout.write(encoded)
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
