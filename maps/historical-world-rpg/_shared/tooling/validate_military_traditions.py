"""Cross-reference validation for scenario military-tradition data."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "engine"))
from military_tradition import MilitaryTraditionRuntime, RecordingTraditionAdapter, TraditionError


def verify_generated_definitions(source: str, definitions: dict) -> None:
    """Compare executable constructor arguments, not the packaged JSON copy."""
    MilitaryTraditionRuntime(definitions, RecordingTraditionAdapter())
    for tradition in definitions["traditions"]:
        match = re.search(r'function traditionDefinition_' + re.escape(tradition["id"]) +
                          r'\(\) returns TraditionDefinition\n(.*?)(?=\n[^\t\n]|\Z)', source, re.S)
        if not match:
            raise TraditionError(f"missing generated tradition {tradition['id']}")
        body = match[1]
        coefficients = re.findall(r'^\tdefinition\.coefficient\("([^"]+)", "(-?\d+)", "(\d+)"\)$', body, re.M)
        expected = [(row["attributeId"], str(row["numerator"]), str(row["denominator"]))
                    for row in tradition["coefficients"]]
        if coefficients != expected:
            raise TraditionError(f"generated coefficients differ for {tradition['id']}")
        milestones = re.findall(r'^\tdefinition\.milestone\("([^"]+)", "(\d+)", "([^"]+)", "([^"]+)", "([^"]*)"\)$', body, re.M)
        expected = [(row["id"], str(row["threshold"]), row["effect"]["effectId"],
                     row["effect"]["mode"], row["effect"]["replacesEffectId"] or "")
                    for row in sorted(tradition["milestones"], key=lambda row: (row["threshold"], row["id"]))]
        if milestones != expected:
            raise TraditionError(f"generated milestones differ for {tradition['id']}")
        for controller in definitions["eligibleControllerIds"]:
            call = (f'runtime.reconcileTradition("{controller}", "{tradition["categoryId"]}", '
                    f'"{tradition["startingExperience"]}", traditionDefinition_{tradition["id"]}(), migrate)')
            if source.count(call) != 1:
                raise TraditionError(f"missing/duplicate generated track {controller}/{tradition['categoryId']}")


def validate(path: str | Path, world_path: str | Path) -> None:
    definitions = json.loads(Path(path).read_text(encoding="utf-8"))
    world = json.loads(Path(world_path).read_text(encoding="utf-8"))
    if definitions.get("format") != "warcraftmap_military_traditions_v1" or definitions.get("schemaVersion") != 1:
        raise TraditionError("unsupported military-tradition document")
    controllers = set(definitions.get("eligibleControllerIds", []))
    polity_ids = {x.get("id") for x in world.get("polities", [])}
    unit_ids = {x.get("id") for x in world.get("strategicUnits", [])}
    if not controllers <= polity_ids | {"player"}:
        raise TraditionError("eligible tradition controller is not a world polity or the player")
    if len(controllers) * len(definitions.get("categories", [])) > 256 or len(definitions.get("experienceSources", [])) > 32:
        raise TraditionError("tradition definitions exceed runtime registration capacity")
    for source in definitions.get("experienceSources", []):
        for field in ("weightNumerator", "weightDenominator"):
            if isinstance(source.get(field), int) and source[field] > 2147483647:
                raise TraditionError("tradition weight exceeds runtime integer representation")
    for assignment in definitions.get("unitAssignments", []):
        if assignment.get("id") not in unit_ids:
            raise TraditionError("tradition assignment names an unknown strategic unit")
        unit = next(x for x in world["strategicUnits"] if x["id"] == assignment["id"])
        if unit.get("controllerPolityId") != assignment.get("controllerId"):
            raise TraditionError("tradition assignment controller differs from strategic state")
    MilitaryTraditionRuntime(definitions, RecordingTraditionAdapter())


if __name__ == "__main__":
    validate(sys.argv[1], sys.argv[2])
