#!/usr/bin/env python3
"""Validate and inspect the scenario-owned ordinary-unit roster."""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent / "_shared" / "engine"))
from unit_roster import RosterCatalog, RosterError  # noqa: E402

SLICE_PATH = ROOT / "scenario/rosters/europe-africa-middle-east-india.json"


def _combined_source(path):
    source = json.loads(Path(path).read_text(encoding="utf-8"))
    if Path(path) == ROOT / "scenario/rosters/foundation.json" and SLICE_PATH.exists():
        regional = json.loads(SLICE_PATH.read_text(encoding="utf-8"))
        for key in ("weapons", "armor", "abilities", "formations", "ships", "archetypes", "historicalEvidence"):
            source[key].extend(regional.get(key, []))
        source["rosterAssignments"] = regional.get("assignments", [])
        source["equipmentCatalog"] = regional.get("equipment", [])
        source["reformCatalog"] = regional.get("reforms", [])
    return source


def load_catalog(path=ROOT / "scenario/rosters/foundation.json"):
    source = _combined_source(path)
    progression = json.loads((ROOT / "scenario/progression/catalog.json").read_text(encoding="utf-8"))
    traditions = json.loads((ROOT / "scenario/military-traditions.json").read_text(encoding="utf-8"))
    world = json.loads((ROOT / "scenario/world/world.json").read_text(encoding="utf-8"))
    references = {
        "technologies": {x["id"] for x in progression["technologies"]},
        "institutions": {x["id"] for x in progression["institutions"]},
        "militaryTraditions": {x["id"] for x in traditions["traditions"]},
        "countries": {x["id"] for x in world["polities"]},
        "equipment": set(source.get("equipmentCatalog", [])),
        "reforms": set(source.get("reformCatalog", [])),
        "resources": {"grain", "flour", "ship_provisions"},
    }
    if source.get("format") != "age_of_sail_ordinary_roster_v1" or not source.get("historicalEvidence"):
        raise RosterError("unsupported roster format or missing historical evidence")
    catalog = RosterCatalog(source, references)
    assignments = source.get("rosterAssignments", [])
    seen = set()
    for assignment in assignments:
        polities, units = assignment.get("polityIds"), assignment.get("archetypeIds")
        if not isinstance(polities, list) or not polities or not isinstance(units, list) or not units:
            raise RosterError("roster assignment must name non-empty polity and archetype arrays")
        if not set(polities) <= references["countries"] or not set(units) <= set(catalog.archetypes):
            raise RosterError("roster assignment has broken polity or archetype reference")
        for polity in polities:
            for unit in units:
                if catalog.archetypes[unit].get("countryId") not in (None, polity):
                    raise RosterError(f"roster assignment gives {unit} to incompatible polity {polity}")
                seen.add((polity, unit))
    if len(seen) != sum(len(x["polityIds"]) * len(x["archetypeIds"]) for x in assignments):
        raise RosterError("duplicate roster assignment")
    catalog.assignments = tuple(sorted(seen))
    return catalog


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
