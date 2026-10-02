#!/usr/bin/env python3
"""Validate and project the authoritative Americas/Caribbean 1450 baseline."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from middle_east_india_politics import PoliticsError, project as _project, validate as _validate

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "scenario/politics/americas-caribbean-1450.json"
GEOGRAPHY = ROOT / "scenario/geography/americas_caribbean.json"
WORLD = ROOT / "scenario/world/world.json"


def validate(source_path=SOURCE, world_path=WORLD, geography_path=GEOGRAPHY, require_projection=True):
    data = _validate(source_path, world_path, geography_path, require_projection)
    evidence = {row.get("id") for row in data.get("historicalEvidence", []) if isinstance(row, dict)}
    if not evidence or any(not row.get("citation") or not row.get("note") for row in data["historicalEvidence"]):
        raise PoliticsError("Americas/Caribbean baseline requires documented historical evidence")
    represented_instances = set()
    geography = json.loads(Path(geography_path).read_text())
    nodes = {node["id"]: node for node in geography["navigationTopology"]["nodes"]}
    reachable = {nodes[link[end]]["instanceId"] for link in geography["navigationTopology"]["links"] for end in ("from", "to")}
    political_instances = {row["id"] for row in geography["instances"]} - {"americas_pacific_transition"}
    for polity in data["polities"]:
        refs = polity.get("evidenceIds")
        if not refs or any(ref not in evidence for ref in refs):
            raise PoliticsError(f"polity {polity['id']}: invalid historical evidence references")
        represented_instances.add(polity["regionalInstanceId"])
        if polity["regionalInstanceId"] not in reachable:
            raise PoliticsError(f"polity {polity['id']}: regional instance is unreachable in generated navigation")
        if polity.get("structure") in {"decentralized", "confederated"} and not polity.get("capitalException"):
            raise PoliticsError(f"polity {polity['id']}: non-capital structure requires a documented exception")
    if not political_instances <= represented_instances:
        raise PoliticsError("missing authoritative coverage for Americas/Caribbean political instance")
    forbidden = ("modern border", "modern national", "united states", "canada province", "colonial boundary")
    names = " ".join(p["name"] for p in data["polities"])
    names += " " + " ".join(v["name"] for p in data["polities"] for v in p["provinces"])
    if any(term in names.lower() for term in forbidden):
        raise PoliticsError("modern-border-only political geography")
    return data


def project(data, world):
    projected = _project(data, world)
    # Political projection owns boundaries and control, while the settlement
    # authority owns the complete (not merely capital) province membership.
    # Rebuilding that derived membership keeps either projection order stable.
    settlement_provinces = {}
    for settlement in projected.get("settlements", []):
        settlement_provinces.setdefault(settlement.get("provinceId"), []).append(settlement["id"])
    authored = {province["id"] for polity in data["polities"] for province in polity["provinces"]}
    for province in projected["provinces"]:
        if province["id"] in authored:
            province["settlementIds"] = settlement_provinces.get(province["id"], [])
    return projected


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    try:
        if argv == ["--write"]:
            data = validate(require_projection=False)
            WORLD.write_text(json.dumps(project(data, json.loads(WORLD.read_text())), ensure_ascii=False, indent=2) + "\n")
        elif argv:
            raise PoliticsError("usage: americas_caribbean_politics.py [--write]")
        data = validate()
        print(f"Americas/Caribbean politics valid: {len(data['polities'])} polities, "
              f"{sum(len(p['provinces']) for p in data['polities'])} provinces, "
              f"{len(data['sovereigntyRelationships'])} sovereignty relationships, "
              f"{len(data['activeConflicts'])} conflicts")
    except (OSError, json.JSONDecodeError, PoliticsError, KeyError) as error:
        print(f"Americas/Caribbean politics validation failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
