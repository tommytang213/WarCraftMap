#!/usr/bin/env python3
"""Validate and project the authoritative Pacific 1450 political baseline."""
from __future__ import annotations

import json
import sys
from collections import deque
from pathlib import Path

from middle_east_india_politics import PoliticsError, project as _project, validate as _validate

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "scenario/politics/pacific-1450.json"
GEOGRAPHY = ROOT / "scenario/geography/pacific.json"
WORLD = ROOT / "scenario/world/world.json"


def validate(source_path=SOURCE, world_path=WORLD, geography_path=GEOGRAPHY, require_projection=True):
    data = _validate(source_path, world_path, geography_path, require_projection)
    evidence = {row.get("id") for row in data.get("historicalEvidence", []) if isinstance(row, dict)}
    if not evidence or any(not row.get("citation") or not row.get("note") for row in data["historicalEvidence"]):
        raise PoliticsError("Pacific baseline requires documented historical evidence")

    geography = json.loads(Path(geography_path).read_text())
    instances = {row["id"] for row in geography["instances"]}
    represented_instances = {row["regionalInstanceId"] for row in data["polities"]}
    if represented_instances != instances:
        raise PoliticsError("missing authoritative coverage for Pacific regional instances")

    nodes = {row["id"]: row for row in geography["navigationTopology"]["nodes"]}
    adjacency = {ident: set() for ident in nodes}
    for link in geography["navigationTopology"]["links"]:
        if "naval" in link["movementClasses"] or "amphibious" in link["movementClasses"]:
            adjacency[link["from"]].add(link["to"])
            adjacency[link["to"]].add(link["from"])
    start = next(iter(nodes)); reached = {start}; pending = deque([start])
    while pending:
        for neighbor in adjacency[pending.popleft()]:
            if neighbor not in reached:
                reached.add(neighbor); pending.append(neighbor)
    reachable_instances = {nodes[node]["instanceId"] for node in reached}

    allowed_structures = {"kingdom", "paramount_chiefdom", "chiefdoms", "confederated", "decentralized"}
    for polity in data["polities"]:
        refs = polity.get("evidenceIds")
        if not refs or any(ref not in evidence for ref in refs):
            raise PoliticsError(f"polity {polity['id']}: invalid historical evidence references")
        if polity.get("structure") not in allowed_structures:
            raise PoliticsError(f"polity {polity['id']}: invalid governance structure")
        if polity["regionalInstanceId"] not in reachable_instances:
            raise PoliticsError(f"polity {polity['id']}: island group is unreachable in navigation topology")
        if polity["structure"] in {"chiefdoms", "confederated", "decentralized"} and not polity.get("capitalException"):
            raise PoliticsError(f"polity {polity['id']}: distributed governance requires a political-center exception")
        if not polity.get("preservedEntities"):
            raise PoliticsError(f"polity {polity['id']}: compressed communities must be preserved explicitly")
        names = " ".join([polity["name"], *(p["name"] for p in polity["provinces"])]).lower()
        if any(term in names for term in ("modern border", "modern national border", "modern country")):
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
            raise PoliticsError("usage: pacific_politics.py [--write]")
        data = validate()
        print(f"Pacific politics valid: {len(data['polities'])} polities, {sum(len(p['provinces']) for p in data['polities'])} provinces")
    except (OSError, json.JSONDecodeError, PoliticsError, KeyError) as error:
        print(f"Pacific politics validation failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
