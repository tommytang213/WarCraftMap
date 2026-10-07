"""Read complete v8/11 placement records, independently of the materializer.

Field order follows War3Net's UnitData binary reader. The supported campaign
W3I contract has no random item tables, so a placement cannot reference one.
"""
from __future__ import annotations

import struct

from warcraft_map_info import _Reader


def validate_units(data: bytes) -> list[dict]:
    if data[:12] != b"W3do" + struct.pack("<II", 8, 11):
        raise ValueError("war3mapUnits.doo requires the supported v8/11 layout")
    r = _Reader(data)
    r.skip(12)

    def count(label):
        value = r.integer()
        if not 0 <= value <= 8192:
            raise ValueError(f"war3mapUnits.doo has invalid {label} count")
        return value

    rows, skins, creations = [], set(), set()
    try:
        for _ in range(count("unit")):
            start = r.at
            r.skip(4)
            type_id = data[start:r.at].decode("ascii")
            variation = r.integer()
            position = r.floats(3)
            rotation, = r.floats(1)
            scale = r.floats(3)
            r.skip(1)
            skinned = data[r.at - 1] >= 0x20
            if skinned:
                r.skip(4)  # remaining skin bytes and flags
            skins.add(skinned)
            owner = r.integer()
            r.skip(2)
            hp, mp = r.integer(), r.integer()
            item_table = r.integer()
            if item_table != -1:
                raise ValueError("war3mapUnits.doo references a missing W3I item table")
            for _ in range(count("dropped item set")):
                r.skip(count("dropped item") * 8)
            r.integer()  # resource amount
            acquisition, = r.floats(1)
            hero = tuple(r.integer() for _ in range(4))
            r.skip(count("inventory") * 8)
            r.skip(count("ability") * 12)
            random_mode = r.integer()
            if random_mode == 0:
                r.skip(4)  # 24-bit level and 8-bit item class
            elif random_mode == 1:
                r.skip(8)
            elif random_mode == 2:
                r.skip(count("random unit") * 8)
            elif random_mode != -1:
                raise ValueError("war3mapUnits.doo has invalid random-unit mode")
            color, waygate, creation = r.integer(), r.integer(), r.integer()
            if not 0 <= owner < 28 or creation in creations or any(value <= 0 for value in scale):
                raise ValueError("war3mapUnits.doo has invalid owner, scale or duplicate creation number")
            creations.add(creation)
            rows.append({"typeId": type_id, "position": position, "owner": owner,
                         "itemTable": item_table, "heroLevel": hero[0],
                         "randomMode": random_mode, "creationNumber": creation})
    except (UnicodeError, struct.error, ValueError) as error:
        raise ValueError(f"invalid war3mapUnits.doo record: {error}") from error
    if len(skins) > 1 or r.at != len(data):
        raise ValueError("war3mapUnits.doo has mixed skin layouts or trailing record bytes")
    return rows
