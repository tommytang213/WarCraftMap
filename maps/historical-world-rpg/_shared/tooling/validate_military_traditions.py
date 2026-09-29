"""Cross-reference validation for scenario military-tradition data."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "engine"))
from military_tradition import MilitaryTraditionRuntime, RecordingTraditionAdapter, TraditionError


def validate(path: str | Path, world_path: str | Path) -> None:
    definitions = json.loads(Path(path).read_text(encoding="utf-8"))
    world = json.loads(Path(world_path).read_text(encoding="utf-8"))
    if definitions.get("format") != "warcraftmap_military_traditions_v1" or definitions.get("schemaVersion") != 1:
        raise TraditionError("unsupported military-tradition document")
    controllers = set(definitions.get("eligibleControllerIds", []))
    polity_ids = {x.get("id") for x in world.get("polities", [])}
    unit_ids = {x.get("id") for x in world.get("strategicUnits", [])}
    if not controllers <= polity_ids:
        raise TraditionError("eligible tradition controller is not a world polity")
    for assignment in definitions.get("unitAssignments", []):
        if assignment.get("id") not in unit_ids:
            raise TraditionError("tradition assignment names an unknown strategic unit")
        unit = next(x for x in world["strategicUnits"] if x["id"] == assignment["id"])
        if unit.get("controllerPolityId") != assignment.get("controllerId"):
            raise TraditionError("tradition assignment controller differs from strategic state")
    MilitaryTraditionRuntime(definitions, RecordingTraditionAdapter())


if __name__ == "__main__":
    validate(sys.argv[1], sys.argv[2])
