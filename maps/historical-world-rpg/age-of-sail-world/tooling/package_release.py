#!/usr/bin/env python3
"""Scenario entry point for the shared Wurst map packager."""

from pathlib import Path
import sys

PROJECT = Path(__file__).resolve().parents[1]
SHARED = PROJECT.parent / "_shared" / "tooling"
sys.path.insert(0, str(SHARED))
sys.path.insert(0, str(PROJECT / "tooling"))

from package_wurst_map import main  # noqa: E402
from validate_map_source import ValidationError, validate  # noqa: E402

if __name__ == "__main__":
    try:
        validate(PROJECT / "map" / "map-source.json")
    except ValidationError as error:
        print(f"packaging failed: invalid canonical source map: {error}", file=sys.stderr)
        raise SystemExit(1)
    raise SystemExit(main([str(PROJECT / "package.json")]))
