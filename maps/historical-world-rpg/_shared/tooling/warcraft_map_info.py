"""Independent structural validation of the supported Warcraft map-info layouts.

Producer version labels are not compatibility verdicts. Parse the matching
layout, including player records and the complete supported tail, instead of
comparing an output with a potentially malformed authoring fixture.
"""
from __future__ import annotations

import math
import struct

SUPPORTED_W3I_FORMATS = frozenset((31, 33))


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

    def floats(self, count: int) -> tuple[float, ...]:
        start = self.at
        self.skip(count * 4)
        values = struct.unpack_from(f"<{count}f", self.data, start)
        if not all(math.isfinite(value) for value in values):
            raise MapInfoError("war3map.w3i has non-finite coordinates or environment values")
        return values

    def skip(self, size: int) -> None:
        if size < 0 or self.at + size > len(self.data):
            raise MapInfoError("war3map.w3i is truncated")
        self.at += size

    def string(self) -> str:
        try:
            end = self.data.index(0, self.at)
        except ValueError as error:
            raise MapInfoError("war3map.w3i has an unterminated string") from error
        try:
            value = self.data[self.at:end].decode("utf-8")
        except UnicodeError as error:
            raise MapInfoError("war3map.w3i has an invalid UTF-8 string") from error
        self.at = end + 1
        return value


def parse_w3i(data: bytes) -> dict:
    """Parse v31/v33 metadata; reject unsupported tails instead of ignoring them."""
    r = _Reader(data)
    version, saves, editor = r.integer(), r.integer(), r.integer()
    if version not in SUPPORTED_W3I_FORMATS:
        raise MapInfoError(f"war3map.w3i format {version} has no supported structural parser")
    game_version = tuple(r.integer() for _ in range(4))
    name, author, description, recommended = (r.string() for _ in range(4))
    camera_bounds = r.floats(8)
    camera_complements = tuple(r.integer() for _ in range(4))
    if any(value < 0 for value in camera_complements):
        raise MapInfoError("war3map.w3i has invalid camera-bound complements")
    playable_width, playable_height = r.integer(), r.integer()
    if playable_width < 1 or playable_height < 1:
        raise MapInfoError("war3map.w3i has invalid playable dimensions")
    flags = r.integer(); r.skip(1)
    r.integer(); r.string(); r.string(); r.string(); r.string(); r.integer()
    r.string(); r.string(); r.string(); r.string()
    r.integer(); r.floats(3); r.skip(4 + 4); r.string(); r.skip(1 + 4)
    script_language, graphics, game_data = r.integer(), r.integer(), r.integer()
    camera_zoom = (r.integer(), r.integer(), r.integer()) if version >= 32 else None
    player_count = r.integer()
    if player_count < 1 or player_count > 24:
        raise MapInfoError(f"war3map.w3i has invalid player count {player_count}")
    players = []
    for _ in range(player_count):
        slot, controller, race, fixed = (r.integer() for _ in range(4))
        player_name = r.string()
        position = r.floats(2)
        priorities = tuple(r.integer() & 0xffffffff for _ in range(4))
        if slot not in range(24) or slot in {row["id"] for row in players} or fixed not in (0, 1):
            raise MapInfoError("war3map.w3i has invalid or duplicate player-slot data")
        players.append({"id": slot, "controller": controller, "race": race,
                        "fixedStartPosition": fixed, "name": player_name,
                        "position": position, "priorities": priorities})
    force_count = r.integer()
    if force_count < 0 or force_count > 24:
        raise MapInfoError(f"war3map.w3i has invalid force count {force_count}")
    forces = []
    for _ in range(force_count):
        force_flags = r.integer()
        mask = r.integer() & 0xffffffff
        # The authoring fixture uses an all-slots mask even with one player.
        # A force mask is not a declaration of additional active player slots.
        forces.append({"flags": force_flags, "playerMask": mask, "name": r.string()})
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
            "cameraZoom": camera_zoom, "players": player_count, "forces": force_count,
            "playerSlots": players, "forceRecords": forces, "cameraBounds": camera_bounds,
            "playableWidth": playable_width, "playableHeight": playable_height,
            "cameraComplements": camera_complements}


def validate_w3i_structure(data: bytes) -> dict:
    """Validate the supported Lua single-player campaign map contract."""
    info = parse_w3i(data)
    expected = {"scriptLanguage": 1, "players": 1}
    mismatches = [f"{key}={info[key]!r} (expected {value!r})"
                  for key, value in expected.items() if info[key] != value]
    if mismatches:
        raise MapInfoError("war3map.w3i has invalid campaign map structure: " + ", ".join(mismatches))
    player = info["playerSlots"][0]
    if player["id"] != 0 or player["controller"] != 1:
        raise MapInfoError("war3map.w3i requires a playable human in player slot 0")
    return info
