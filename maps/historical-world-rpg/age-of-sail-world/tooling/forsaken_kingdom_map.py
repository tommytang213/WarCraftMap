"""Authoring compatibility fixture, backed by the shared map-info parser.

W3I 31 and 33 share most fields inspected here; the three forced-camera-zoom
values were added in v32. A format/editor/game-version
number is evidence about the producer, not by itself evidence that Warcraft can
or cannot load the map; validation therefore parses the matching layout and
checks the browser-relevant structure instead of requiring one magic version.
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "_shared/tooling"))
from warcraft_map_info import (MapInfoError, SUPPORTED_W3I_FORMATS, _Reader,
                               parse_w3i, validate_w3i_structure)

W3I_FORMAT = 33
EDITOR_VERSION = 6116
GAME_VERSION = (3, 0, 0, 24268)
SCRIPT_LANGUAGE_LUA = 1
GRAPHICS_SD_AND_HD = 3
GAME_DATA_TFT = 1
CAMERA_ZOOM = (1650, 3000, 1250)


def validate_current_w3i(data: bytes) -> dict:
    """Validate the repository's deliberately locked authoring fixture."""
    info = validate_w3i_structure(data)
    expected = {"editorVersion": EDITOR_VERSION, "gameVersion": GAME_VERSION,
                "scriptLanguage": SCRIPT_LANGUAGE_LUA,
                "graphicsModes": GRAPHICS_SD_AND_HD, "gameDataVersion": GAME_DATA_TFT,
                "cameraZoom": CAMERA_ZOOM, "players": 1, "forces": 1}
    mismatches = [f"{key}={info[key]!r} (expected {value!r})"
                  for key, value in expected.items() if info[key] != value]
    if mismatches:
        raise MapInfoError("war3map.w3i does not match the locked Forsaken Kingdom 3.0.0.24268 fixture: "
                           + ", ".join(mismatches))
    return info


def upgrade_v25_to_current(data: bytes) -> bytes:
    """One-time, deterministic conversion of the repository's stock v25 map."""
    r = _Reader(data)
    if r.integer() != 25:
        raise MapInfoError("W3I upgrade input must be the canonical v25 map")
    saves, _legacy_editor = r.integer(), r.integer()
    body_start = r.at
    for _ in range(4): r.string()
    r.skip(32 + 16 + 8); r.integer(); r.skip(1); r.integer()
    for _ in range(4): r.string()
    r.integer()
    for _ in range(4): r.string()
    r.skip(4 + 12 + 4 + 4); r.string(); r.skip(1 + 4)
    player_count_at = r.at
    player_count = r.integer()
    if player_count != 1:
        raise MapInfoError("canonical selector input must contain exactly one player")
    player_start = r.at
    r.skip(16); r.string(); r.skip(16)
    player_end = r.at
    out = bytearray(struct.pack("<iii4i", W3I_FORMAT, saves, EDITOR_VERSION, *GAME_VERSION))
    out += data[body_start:player_count_at]
    out += struct.pack("<6i", SCRIPT_LANGUAGE_LUA, GRAPHICS_SD_AND_HD, GAME_DATA_TFT, *CAMERA_ZOOM)
    out += struct.pack("<i", player_count)
    out += data[player_start:player_end] + struct.pack("<ii", 0, 0)
    out += data[player_end:]
    validate_current_w3i(bytes(out))
    return bytes(out)


if __name__ == "__main__":
    source, destination = map(Path, sys.argv[1:3])
    destination.write_bytes(upgrade_v25_to_current(source.read_bytes()))
