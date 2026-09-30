"""Validate scenario map presentation against canonical world stable IDs."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "engine"))
from map_discovery import MapDiscoveryError, build_catalog  # noqa: E402


def validate(world: dict, scenario_root: Path, fail):
    path = scenario_root / "maps" / "world-map.json"
    try:
        presentation = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        fail(f"map presentation is invalid: {error}")
    if presentation.get("format") != "warcraftmap_map_presentation_v1":
        fail("map presentation has an unsupported format")
    try:
        return build_catalog(world, presentation)
    except MapDiscoveryError as error:
        fail(f"map presentation: {error}")
