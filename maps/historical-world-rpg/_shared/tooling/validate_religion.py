"""Cross-reference scenario religion identities against authoritative world data."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "engine"))
from religion import ReligionError, ReligionRuntime


def validate(path: str | Path, world_path: str | Path) -> None:
    definitions = json.loads(Path(path).read_text(encoding="utf-8"))
    world = json.loads(Path(world_path).read_text(encoding="utf-8"))
    polity_ids = {x.get("id") for x in world.get("polities", [])}
    region_ids = ({x.get("id") for x in world.get("provinces", [])} |
                  {x.get("id") for x in world.get("settlements", [])})
    if not set(definitions.get("polityIds", [])) <= polity_ids:
        raise ReligionError("religion data names a polity absent from world data")
    if not set(definitions.get("regionIds", [])) <= region_ids:
        raise ReligionError("religion data names a province/settlement absent from world data")
    ReligionRuntime(definitions)


if __name__ == "__main__": validate(sys.argv[1], sys.argv[2])
