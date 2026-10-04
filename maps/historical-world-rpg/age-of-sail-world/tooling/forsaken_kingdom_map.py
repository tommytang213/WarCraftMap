"""Locked map-info contract for the supported Forsaken Kingdom client.

The layout follows W3I v33 as emitted by the current World Editor.  Keeping the
parser here makes packaging validate bytes the client reads during map-browser
enumeration instead of trusting ``wc3Patch`` or source-code markers.
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path

W3I_FORMAT = 33
EDITOR_VERSION = 6116
GAME_VERSION = (3, 0, 0, 24268)
SCRIPT_LANGUAGE_LUA = 1
GRAPHICS_SD_AND_HD = 3
GAME_DATA_TFT = 1
CAMERA_ZOOM = (1650, 3000, 1250)


class MapInfoError(ValueError):
    pass


class _Reader:
    def __init__(self, data: bytes):
        self.data, self.at = data, 0

    def integer(self) -> int:
        if self.at + 4 > len(self.data):
            raise MapInfoError("war3map.w3i is truncated")
        value = struct.unpack_from("<i", self.data, self.at)[0]
        self.at += 4
        return value

    def skip(self, size: int) -> None:
        if self.at + size > len(self.data):
            raise MapInfoError("war3map.w3i is truncated")
        self.at += size

    def string(self) -> str:
        try:
            end = self.data.index(0, self.at)
        except ValueError as error:
            raise MapInfoError("war3map.w3i has an unterminated string") from error
        value = self.data[self.at:end].decode("utf-8")
        self.at = end + 1
        return value


def parse_w3i(data: bytes) -> dict:
    """Parse the browser-relevant v33 fields and prove the whole tail is sane."""
    r = _Reader(data)
    version, saves, editor = r.integer(), r.integer(), r.integer()
    if version != W3I_FORMAT:
        raise MapInfoError(f"war3map.w3i format {version} is not current format {W3I_FORMAT}")
    game_version = tuple(r.integer() for _ in range(4))
    name, author, description, recommended = (r.string() for _ in range(4))
    r.skip(32 + 16 + 8)  # camera bounds, complements, playable width/height
    flags = r.integer(); r.skip(1)
    r.integer(); r.string(); r.string(); r.string(); r.string(); r.integer()
    r.string(); r.string(); r.string(); r.string()
    r.skip(4 + 12 + 4 + 4); r.string(); r.skip(1 + 4)
    script_language, graphics, game_data = r.integer(), r.integer(), r.integer()
    camera_zoom = (r.integer(), r.integer(), r.integer())
    player_count = r.integer()
    if player_count < 1 or player_count > 24:
        raise MapInfoError(f"war3map.w3i has invalid player count {player_count}")
    for _ in range(player_count):
        r.skip(16); r.string(); r.skip(16 + 8)  # position, ally and enemy priorities
    force_count = r.integer()
    if force_count < 1 or force_count > 24:
        raise MapInfoError(f"war3map.w3i has invalid force count {force_count}")
    for _ in range(force_count):
        r.skip(8); r.string()
    for record_size in (16, 8):
        count = r.integer()
        if count < 0 or count > 100000:
            raise MapInfoError("war3map.w3i has an invalid custom-data count")
        r.skip(count * record_size)
    random_units = r.integer()
    random_items = r.integer() if random_units == 0 else -1
    if random_units != 0 or random_items != 0 or r.at != len(data):
        raise MapInfoError("war3map.w3i has unsupported or trailing random-table data")
    return {"format": version, "saves": saves, "editorVersion": editor,
            "gameVersion": game_version, "name": name, "author": author,
            "description": description, "recommendedPlayers": recommended,
            "flags": flags, "scriptLanguage": script_language,
            "graphicsModes": graphics, "gameDataVersion": game_data,
            "cameraZoom": camera_zoom, "players": player_count, "forces": force_count}


def validate_current_w3i(data: bytes) -> dict:
    info = parse_w3i(data)
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
