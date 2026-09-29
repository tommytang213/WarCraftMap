#!/usr/bin/env python3
"""Validate and inspect the scenario-owned ordinary-unit roster."""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent / "_shared" / "engine"))
from unit_roster import RosterCatalog, RosterError  # noqa: E402


def load_catalog(path=ROOT / "scenario/rosters/foundation.json"):
    source = json.loads(Path(path).read_text(encoding="utf-8"))
    progression = json.loads((ROOT / "scenario/progression/catalog.json").read_text(encoding="utf-8"))
    traditions = json.loads((ROOT / "scenario/military-traditions.json").read_text(encoding="utf-8"))
    world = json.loads((ROOT / "scenario/world/world.json").read_text(encoding="utf-8"))
    references = {
        "technologies": {x["id"] for x in progression["technologies"]},
        "militaryTraditions": {x["id"] for x in traditions["traditions"]},
        "countries": {x["id"] for x in world["polities"]},
    }
    if source.get("format") != "age_of_sail_ordinary_roster_v1" or not source.get("historicalEvidence"):
        raise RosterError("unsupported roster format or missing historical evidence")
    return RosterCatalog(source, references)


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=ROOT / "scenario/rosters/foundation.json")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        catalog = load_catalog(args.source)
        generated = {"format":"age_of_sail_generated_roster_v1", "digest":catalog.digest(), "units":catalog.generated_unit_data()}
        text = json.dumps(generated, sort_keys=True, separators=(",", ":")) + "\n"
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True); args.output.write_text(text, encoding="utf-8")
        print(f"Ordinary roster valid: {len(generated['units'])} archetypes; digest {generated['digest']}")
    except (OSError, json.JSONDecodeError, KeyError, TypeError, RosterError) as error:
        print(f"Ordinary roster validation failed: {error}", file=sys.stderr); return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
