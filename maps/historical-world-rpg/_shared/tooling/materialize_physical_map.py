#!/usr/bin/env python3
"""Materialize generated regional data as deterministic Warcraft map binaries.

The JSON rasters remain the authority.  This module is deliberately a small
binary adapter: it composes the assigned rasters, derives W3E/WPM cells and
places stock Warcraft representations for authored settlements and anchors.
"""
from __future__ import annotations

import hashlib
import json
import math
import struct
from pathlib import Path
from scenario_inputs import settlement_sources

FORMAT_VERSION = 1
MAX_TERRAIN_CELLS = 256 * 256
MAX_OBJECTS = 8192


class MaterializationError(ValueError):
    pass


def _resize_map_info(data: bytes, width: int, height: int) -> bytes:
    """Resize the supported W3I header with terrain, preserving camera insets.

    The rest of the version-specific layout (players, forces, etc.) is unchanged
    and is independently validated by the artifact checker.
    """
    try:
        version = struct.unpack_from("<i", data)[0]
        if version not in (31, 33, 39):
            raise MaterializationError(f"unsupported W3I resize layout: {version}")
        offset = 28  # version/save/editor/game-version tuple, then four strings
        for _ in range(4):
            offset = data.index(0, offset) + 1
        bounds = list(struct.unpack_from("<8f", data, offset))
        left, right, bottom, top, old_width, old_height = struct.unpack_from("<6i", data, offset + 32)
        if min(left, right, bottom, top) < 0 or width <= left + right or height <= bottom + top:
            raise MaterializationError("invalid W3I camera margins for generated terrain")
        dx = (width - old_width - left - right) * 64.0
        dy = (height - old_height - bottom - top) * 64.0
        for i in (0, 4): bounds[i] -= dx
        for i in (2, 6): bounds[i] += dx
        for i in (1, 7): bounds[i] -= dy
        for i in (3, 5): bounds[i] += dy
        result = bytearray(data)
        struct.pack_into("<8f", result, offset, *bounds)
        struct.pack_into("<2i", result, offset + 48, width - left - right, height - bottom - top)
        return bytes(result)
    except (ValueError, struct.error) as error:
        raise MaterializationError(f"cannot resize malformed W3I: {error}") from error


def _decode(instance: dict) -> list[int]:
    cells = []
    for value, count in instance["surfaceEncoding"]["runs"]:
        cells.extend([value] * count)
    grid = instance["grid"]
    if len(cells) != grid["width"] * grid["height"]:
        raise MaterializationError(f"{instance.get('id', '<terrain>')}: malformed surface raster")
    return cells


def _instances(doc: dict, selected: set[str]) -> list[dict]:
    if doc.get("formatVersion") == 2:
        return [row for row in doc["instances"] if row["id"] in selected]
    # Version-one authorities describe a single regional raster shared by
    # several logical instances.  It is still real geography; a stable visual
    # variation below distinguishes separately packaged physical chapters.
    return [dict(doc, id=doc["regionId"])]


def _compose(documents: list[dict], selected: set[str]) -> tuple[int, int, list[int], dict[str, tuple[int, int, int, int]]]:
    parts = [part for doc in documents for part in _instances(doc, selected)]
    if not parts:
        raise MaterializationError("ordinary physical map has no assigned generated terrain")
    columns = math.ceil(math.sqrt(len(parts)))
    rows = math.ceil(len(parts) / columns)
    slot_w = max(x["grid"]["width"] for x in parts)
    slot_h = max(x["grid"]["height"] for x in parts)
    raw_width, raw_height = columns * slot_w, rows * slot_h
    # Warcraft accepts the standard 32-cell size increments. Padding is void
    # and therefore cannot introduce unintended travel at the outer border.
    width = math.ceil(raw_width / 32) * 32
    height = math.ceil(raw_height / 32) * 32
    if width * height > MAX_TERRAIN_CELLS or width > 256 or height > 256:
        raise MaterializationError(f"composed terrain {width}x{height} exceeds Warcraft budget")
    cells = [0] * (width * height)
    layouts = {}
    for index, part in enumerate(parts):
        ox, oy = index % columns * slot_w, index // columns * slot_h
        pw, ph = part["grid"]["width"], part["grid"]["height"]
        source = _decode(part)
        for y in range(ph):
            cells[(oy + y) * width + ox:(oy + y) * width + ox + pw] = source[y * pw:y * pw + pw]
        layouts[part["id"]] = (ox, oy, pw, ph)
    return width, height, cells, layouts


def _w3e(width: int, height: int, cells: list[int], map_id: str) -> bytes:
    # W3E vertex dimensions are cell dimensions + 1.  Use Lordaeron Summer's
    # stock tile palette and centered world bounds.
    tiles = (b"Ldrt", b"Ldro", b"Ldrg", b"Lrok", b"Lgrs", b"Lgrd")
    cliffs = (b"CLdi", b"CLgr")
    out = bytearray(b"W3E!" + struct.pack("<IcI", 11, b"L", 0))
    out += struct.pack("<I", len(tiles)) + b"".join(tiles)
    out += struct.pack("<I", len(cliffs)) + b"".join(cliffs)
    out += struct.pack("<IIff", width + 1, height + 1, -width * 64.0, -height * 64.0)
    salt = hashlib.sha256(map_id.encode()).digest()
    for y in range(height + 1):
        for x in range(width + 1):
            adjacent = [cells[cy * width + cx] for cy in {max(0, y-1), min(height-1, y)}
                        for cx in {max(0, x-1), min(width-1, x)}]
            land = adjacent.count(1) >= max(1, len(adjacent) // 2)
            water = not land
            ground = 0x2000 if land else 0x1f80
            water_level = 0x2000
            flags = 0x40 if water else 0
            texture = salt[(x + y * 7) % len(salt)] % (6 if land else 2)
            out += struct.pack("<HHBBB", ground, water_level, flags, texture, 0)
    return bytes(out)


def _wpm(width: int, height: int, cells: list[int]) -> bytes:
    # Four pathing pixels per terrain cell. Land blocks water; navigable sea
    # blocks walking/building; decorative/void cells block all normal travel.
    values = {0: 0x4e, 1: 0x40, 2: 0x0a, 3: 0x4e}
    pw, ph = width * 4, height * 4
    payload = bytearray()
    for y in range(height):
        row = b"".join(bytes([values[cells[y * width + x]]]) * 4 for x in range(width))
        payload += row * 4
    return b"MP3W" + struct.pack("<III", 0, pw, ph) + payload


def _unit(type_id: bytes, x: float, y: float, owner: int, creation: int) -> bytes:
    # Warcraft units.doo v8 record with no drops, inventory, abilities or
    # randomization. Stock IDs make the result playable without custom data.
    out = bytearray(type_id + struct.pack("<i", 0))
    out += struct.pack("<fffffff", x, y, 0.0, 0.0, 1.0, 1.0, 1.0)
    out += struct.pack("<Bibbii", 0, owner, 0, 0, -1, -1)
    out += struct.pack("<ii", -1, 0)           # no W3I item table; no dropped item sets
    out += struct.pack("<ifiiii", 0, 0.0, 1, 0, 0, 0)  # gold/target/hero stats
    out += struct.pack("<iii", 0, 0, -1)      # no inventory, abilities or randomization
    out += struct.pack("<iii", -1, -1, creation)
    return bytes(out)


def _positions(project: Path) -> dict[str, dict]:
    result = {}
    for path, _geography, _region in settlement_sources(project):
        for row in json.loads(path.read_text(encoding="utf-8")).get("settlements", []):
            result[row["id"]] = row
    return result


def location_cell(position, layout, width, cells, surfaces, reserved=()):
    """Place an authored local point using the materializer's bounded raster.

    Ties use row/column order, so regeneration cannot reroll an interaction.
    """
    ox, oy, iw, ih = layout
    sx, sy = position
    cx, cy = ox + min(iw - 1, max(0, round(sx))), oy + min(ih - 1, max(0, round(sy)))
    if cells[cy * width + cx] not in surfaces or (cx, cy) in reserved:
        eligible = ((x, y) for y in range(oy, oy + ih) for x in range(ox, ox + iw)
                    if cells[y * width + x] in surfaces and (x, y) not in reserved)
        nearest = min(eligible, key=lambda p: (abs(p[0] - cx) + abs(p[1] - cy), p[1], p[0]), default=None)
        if nearest is None:
            raise MaterializationError("location has no compatible materialized terrain cell")
        cx, cy = nearest
    return cx, cy


def settlement_placements(project: Path, physical, settlements: list[dict], width: int, height: int, cells: list[int], layouts: dict) -> list[dict]:
    """Shared physical placement for map objects and the campaign starting party."""
    authored = _positions(project)
    placed = []
    for settlement in sorted(settlements, key=lambda row: row["id"]):
        source = authored.get(settlement["id"], settlement)
        if source.get("regionalInstanceId") not in physical.regional_instance_ids:
            raise MaterializationError(f"{physical.id}: settlement {settlement['id']} has inconsistent regional placement")
        layout = layouts.get(source["regionalInstanceId"])
        if layout is None:  # v1 region-wide rasters use catalogue coordinates directly
            layout = next(iter(layouts.values()))
        ox, oy, iw, ih = layout
        position = source.get("position")
        if position is None:
            # Abstract minor communities intentionally have no invented source
            # coordinate. Give their required compressed representation a
            # deterministic free cell without promoting it to scenario truth.
            digest = hashlib.sha256(settlement["id"].encode()).digest()
            position = [int.from_bytes(digest[:2], "little") % iw,
                        int.from_bytes(digest[2:4], "little") % ih]
        cx, cy = location_cell(position, layout, width, cells, {1})
        wx, wy = (cx + .5 - width / 2) * 128.0, (cy + .5 - height / 2) * 128.0
        is_port = source.get("settlementClass") == "port" or "port" in source.get("roles", []) or "dockyard" in source.get("services", [])
        placed.append({"id": settlement["id"], "regionalInstanceId": source["regionalInstanceId"],
                       "cell": [cx, cy], "world": [wx, wy], "kind": "port" if is_port else "settlement"})
    return placed


def physical_layout(generated: Path, physical):
    docs = [json.loads((generated / f"terrain-{terrain_id}.json").read_text(encoding="utf-8"))
            for terrain_id in physical.terrain_ids]
    if docs:
        return _compose(docs, set(physical.regional_instance_ids))
    # Encounter chapters use a bounded water arena without regional terrain.
    width = height = 64
    cells = [2 if 0 < x < width - 1 and 0 < y < height - 1 else 0
             for y in range(height) for x in range(width)]
    return width, height, cells, {physical.id: (0, 0, width, height)}


def player_arrival_world(width: int, height: int, placed: list[dict]) -> list[float]:
    """Default editor player-slot marker; not a transferred party's arrival.

    Runtime parties use their authored origin or generated boundary navigation.
    """
    spawn = placed[0]["cell"] if placed else [width // 2, height // 2]
    return [(spawn[0] + .5 - width / 2) * 128.0, (spawn[1] + .5 - height / 2) * 128.0]


def materialize(project: Path, map_dir: Path, generated: Path, physical, runtime: dict) -> dict:
    if physical.bootstrap:
        manifest = {"formatVersion": FORMAT_VERSION, "physicalMapId": physical.id, "bootstrap": True,
                    "terrain": {"width": 64, "height": 64},
                    "objects": {"spawnCount": 1, "settlementCount": 0}}
        runtime_dir = map_dir / "runtime"
        runtime_dir.mkdir(exist_ok=True)
        runtime_dir.joinpath("physical-map.json").write_text(
            json.dumps(manifest, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        return manifest
    docs = [json.loads((generated / f"terrain-{terrain_id}.json").read_text(encoding="utf-8"))
            for terrain_id in physical.terrain_ids]
    width, height, cells, layouts = physical_layout(generated, physical)
    map_dir.joinpath("war3map.w3e").write_bytes(_w3e(width, height, cells, physical.id))
    map_dir.joinpath("war3map.wpm").write_bytes(_wpm(width, height, cells))
    # SHD is one byte per pathing pixel. Retaining the 64x64 source shadow
    # raster after resizing leaves the client with a truncated terrain resource.
    map_dir.joinpath("war3map.shd").write_bytes(bytes(width * height * 16))
    info_path = map_dir / "war3map.w3i"
    info_path.write_bytes(_resize_map_info(info_path.read_bytes(), width, height))
    placed = settlement_placements(project, physical, runtime.get("settlementDefinitions", []), width, height, cells, layouts)
    records = [_unit(b"nshp" if row["kind"] == "port" else b"ntav", *row["world"], 15, index + 1)
               for index, row in enumerate(placed)]
    world_markers = []
    marker_ids = []
    for doc in docs:
        if doc.get("formatVersion") == 1:
            marker_ids += [f"landmark:{x['id']}" for x in doc.get("landmarks", [])]
            marker_ids += [f"route:{x['id']}" for x in doc.get("features", {}).get("linear", [])]
            marker_ids += [f"transition:{x['id']}" for x in doc.get("transitionAnchors", [])]
        else:
            for instance in _instances(doc, set(physical.regional_instance_ids)):
                marker_ids += [f"landmark:{x['id']}" for x in instance.get("features", [])]
                marker_ids += [f"transition:{x['id']}" for x in instance.get("boundaryAnchors", [])]
    for marker_id in sorted(set(marker_ids)):
        digest = hashlib.sha256((physical.id + ":" + marker_id).encode()).digest()
        cx, cy = int.from_bytes(digest[:2], "little") % width, int.from_bytes(digest[2:4], "little") % height
        wx, wy = (cx + .5 - width / 2) * 128.0, (cy + .5 - height / 2) * 128.0
        records.append(_unit(b"nfoh", wx, wy, 15, len(records) + 1))
        world_markers.append({"id": marker_id, "cell": [cx, cy]})
    # Editor player-slot marker, independent of campaign party reconstruction.
    sx, sy = player_arrival_world(width, height, placed)
    records.insert(0, _unit(b"sloc", sx, sy, 0, 0))
    if len(records) > MAX_OBJECTS:
        raise MaterializationError(f"{physical.id}: object budget exceeded")
    map_dir.joinpath("war3mapUnits.doo").write_bytes(b"W3do" + struct.pack("<II", 8, 11) + struct.pack("<I", len(records)) + b"".join(records))
    manifest = {"formatVersion": FORMAT_VERSION, "physicalMapId": physical.id, "bootstrap": False,
        "terrain": {"width": width, "height": height, "cellCount": width * height,
                    "authoritySha256": hashlib.sha256(b"".join((generated / f"terrain-{x}.json").read_bytes() for x in physical.terrain_ids)).hexdigest()},
        "instances": [{"id": key, "layout": list(value)} for key, value in sorted(layouts.items())],
        "objects": {"spawnCount": 1, "arrivalWorld": [sx, sy], "settlementCount": len(placed), "worldMarkerCount": len(world_markers),
                    "unitObjectCount": len(records), "settlements": placed, "worldMarkers": world_markers},
        "representations": {"routes": "pathable terrain plus stock neutral markers", "landmarks": "stock neutral markers",
                            "transitions": "stock neutral markers", "ports": "stock neutral shops"}}
    runtime_dir = map_dir / "runtime"
    runtime_dir.mkdir(exist_ok=True)
    runtime_dir.joinpath("physical-map.json").write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return manifest
