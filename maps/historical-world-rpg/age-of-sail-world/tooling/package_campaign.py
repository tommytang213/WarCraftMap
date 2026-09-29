#!/usr/bin/env python3
"""Scenario entry point for the complete deterministic campaign build."""
from pathlib import Path
import sys

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT.parent / "_shared" / "tooling"))

from package_wurst_campaign import main  # noqa: E402

if __name__ == "__main__":
    arguments = sys.argv[1:]
    if arguments not in ([], ["clean"]):
        print("usage: package_campaign.py [clean]", file=sys.stderr)
        raise SystemExit(2)
    raise SystemExit(main([*arguments, str(PROJECT / "physical-maps.json")]))
