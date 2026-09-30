#!/usr/bin/env python3
"""Validate and project the authoritative Southeast Asia 1450 political baseline."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from middle_east_india_politics import PoliticsError, project as _project, validate as _validate

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "scenario/politics/southeast-asia-1450.json"
GEOGRAPHY = ROOT / "scenario/geography/southeast_asia.json"
WORLD = ROOT / "scenario/world/world.json"


def validate(source_path=SOURCE, world_path=WORLD, geography_path=GEOGRAPHY, require_projection=True):
    data = _validate(source_path, world_path, geography_path, require_projection)
    evidence = {row.get("id") for row in data.get("historicalEvidence", []) if isinstance(row, dict)}
    if not evidence or any(not row.get("citation") or not row.get("note") for row in data["historicalEvidence"]):
        raise PoliticsError("Southeast Asia baseline requires documented historical evidence")
    for polity in data["polities"]:
        refs = polity.get("evidenceIds")
        if not refs or any(ref not in evidence for ref in refs):
            raise PoliticsError(f"polity {polity['id']}: invalid historical evidence references")
    geography = json.loads(Path(geography_path).read_text())
    linked_instances = set()
    nodes = {node["id"]: node for node in geography["navigationTopology"]["nodes"]}
    for link in geography["navigationTopology"]["links"]:
        linked_instances.add(nodes[link["from"]]["instanceId"])
        linked_instances.add(nodes[link["to"]]["instanceId"])
    for polity in data["polities"]:
        if polity["regionalInstanceId"] not in linked_instances:
            raise PoliticsError(f"polity {polity['id']}: regional instance is unreachable in generated navigation")
    forbidden = ("modern border", "modern national border", "modern country")
    for polity in data["polities"]:
        names = " ".join([polity["name"], *(p["name"] for p in polity["provinces"])]).lower()
        if any(term in names for term in forbidden):
            raise PoliticsError(f"polity {polity['id']}: modern-border-only reference")
    return data


def project(data, world):
    return _project(data, world)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    try:
        if argv == ["--write"]:
            data = validate(require_projection=False)
            WORLD.write_text(json.dumps(project(data, json.loads(WORLD.read_text())), ensure_ascii=False, indent=2) + "\n")
        elif argv:
            raise PoliticsError("usage: southeast_asia_politics.py [--write]")
        data = validate()
        print(f"Southeast Asia politics valid: {len(data['polities'])} polities, {sum(len(p['provinces']) for p in data['polities'])} provinces")
    except (OSError, json.JSONDecodeError, PoliticsError, KeyError) as error:
        print(f"Southeast Asia politics validation failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
