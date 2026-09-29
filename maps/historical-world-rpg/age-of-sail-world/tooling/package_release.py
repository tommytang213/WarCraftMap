#!/usr/bin/env python3
"""Scenario entry point for the shared Wurst map packager."""

from pathlib import Path
import sys

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT.parent / "_shared" / "tooling"))
sys.path.insert(0, str(PROJECT / "tooling"))

from package_wurst_map import main  # noqa: E402
from validate_map_source import ValidationError, validate  # noqa: E402
from validate_europe_politics import validate as validate_europe_politics  # noqa: E402
from validate_africa_politics import validate as validate_africa_politics  # noqa: E402
from europe_settlements import validate as validate_europe_settlements  # noqa: E402
from middle_east_india_content import MiddleEastIndiaContentError, validate as validate_middle_east_india_content  # noqa: E402
from southeast_asia_politics import PoliticsError, validate as validate_southeast_asia_politics  # noqa: E402
from east_asia_politics import validate as validate_east_asia_politics  # noqa: E402
from pacific_politics import validate as validate_pacific_politics  # noqa: E402
from east_asia_content import EastAsiaContentError, validate as validate_east_asia_content  # noqa: E402

if __name__ == "__main__":
    try:
        validate(PROJECT / "map" / "map-source.json")
        validate_europe_politics(PROJECT / "scenario" / "politics" / "europe-1450.json")
        validate_africa_politics(PROJECT / "scenario" / "politics" / "africa-1450.json")
        validate_europe_settlements(PROJECT / "scenario" / "settlements" / "europe-1450.json")
        validate_middle_east_india_content(PROJECT / "scenario" / "settlements" / "middle-east-india-1450.json")
        validate_southeast_asia_politics()
        validate_east_asia_politics()
        validate_pacific_politics()
        validate_east_asia_content()
    except (ValidationError, MiddleEastIndiaContentError, EastAsiaContentError, PoliticsError) as error:
        print(f"packaging failed: invalid canonical source map: {error}", file=sys.stderr)
        raise SystemExit(1)
    arguments = sys.argv[1:]
    if arguments not in ([], ["clean"]):
        print("usage: package_release.py [clean]", file=sys.stderr)
        raise SystemExit(2)
    raise SystemExit(main([*arguments, str(PROJECT / "package.json")]))
