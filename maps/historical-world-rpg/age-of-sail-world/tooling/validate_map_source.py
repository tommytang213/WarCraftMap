#!/usr/bin/env python3
"""Validate the canonical unpacked Warcraft III source map without World Editor."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import struct
import sys
from pathlib import Path

from forsaken_kingdom_map import MapInfoError, validate_current_w3i


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = PROJECT_ROOT / "map" / "map-source.json"
EXPECTED_METADATA = {
    "author": "WarCraftMap Project",
    "name": "Age of Sail: The World",
    "scriptBackend": "lua",
    "wc3Patch": "v3.0",
}

COMPATIBILITY_FILE = "WC3Compatibility.wurst"
COMPATIBILITY_FIXTURE = "WC3CompatibilityCompileFixture.wurst"
NATIVE_SAVE_FIXTURE = "NativeSaveRegressionFixture.wurst"
WRAPPED_NATIVES = (
    "GetEquippedItem", "GetUnequippedItem", "GetItemEquipmentType", "GetItemTag",
    "IsItemEquipped", "IsItemInBag", "UnitEquipItem", "UnitUnequipItem",
    "UnitUnequipItemFromSlot", "UnitExtendedInventorySize", "UnitItemInBagSlot",
    "UnitItemInEquipmentSlot", "UnitHasItemBagged", "UnitHasItemEquipped",
    "UnitHasLoadoutSlotEmpty", "UnitHasAnyItemEquiped",
    "UnitHasItemEquipmentOfType", "UnitCanEquipItemOfEquipmentType", "SaveGame",
    "LoadGame", "SaveGameExists", "CopySaveGame", "RenameSaveDirectory",
    "RemoveSaveDirectory", "SaveGameCheckpoint", "InitGameCache", "HaveStoredString",
    "GetStoredString", "StoreString", "FlushStoredString", "SaveGameCache", "BlzCreateFrameByType",
    "BlzFrameSetVisible", "BlzFrameSetEnable", "IsTerrainPathable",
    "SetUnitPosition", "SetUnitX", "SetUnitY", "BlzGetUnitMaxHP",
    "BlzSetUnitMaxHP", "BlzGetUnitCollisionSize",
)


class ValidationError(ValueError):
    pass


def validate_compatibility_boundary(project_root: Path = PROJECT_ROOT) -> None:
    wurst_root = project_root / "wurst"
    compatibility = wurst_root / COMPATIBILITY_FILE
    fixture = wurst_root / COMPATIBILITY_FIXTURE
    native_save_fixture = wurst_root / NATIVE_SAVE_FIXTURE
    missing = [path.name for path in (compatibility, fixture) if not path.is_file()]
    if missing:
        raise ValidationError("WC3 compatibility source is missing: " + ", ".join(missing))
    boundary_text = compatibility.read_text(encoding="utf-8")
    for required in (
        'WC3_COMPAT_PATCH_FAMILY = "v3.0"',
        'WC3_COMPAT_SCRIPT_BACKEND = "LUA"',
        "requireWC3Compatibility()",
        "WC3_HAS_MODERN_INVENTORY",
        "WC3_HAS_NATIVE_SAVE_MANAGEMENT",
        "WC3_HAS_FRAME_UI",
        "WC3_HAS_PATHING_QUERIES",
        "WC3_HAS_MODERN_UNIT_FIELDS",
    ):
        if required not in boundary_text:
            raise ValidationError(f"WC3 compatibility boundary is missing {required}")
    native_pattern = re.compile(
        r"\b(" + "|".join(map(re.escape, WRAPPED_NATIVES)) + r")\s*\("
    )
    violations = []
    for source in sorted(wurst_root.rglob("*.wurst")):
        if source == compatibility:
            continue
        for line_number, line in enumerate(source.read_text(encoding="utf-8").splitlines(), 1):
            match = native_pattern.search(line)
            if match:
                violations.append(f"{source.relative_to(project_root)}:{line_number}: {match.group(1)}")
    if violations:
        raise ValidationError(
            "wrapped Warcraft natives must only be used in "
            + COMPATIBILITY_FILE + ": " + "; ".join(violations)
        )
    # Small isolated boundary fixtures used by unit tests predate the native-save
    # gate. Canonical projects contain this optional companion and validate it.
    if native_save_fixture.is_file():
        native_text = native_save_fixture.read_text(encoding="utf-8")
        for required in (
            'NATIVE_SAVE_FIXTURE_ID = "wc3-v3.0-lua-native-save-regression"',
            "nativeSaveRegressionStart", "nativeSaveRegressionAfterLoad",
            "nativeSaveRegressionRequestDuring", "reconstructRegisteredRuntime",
            "compatSaveGame(saveName)",
        ):
            if required not in native_text:
                raise ValidationError(f"native save regression fixture is missing {required}")
        bootstrap = wurst_root / "Bootstrap.wurst"
        if bootstrap.is_file() and "NativeSaveRegressionFixture" in bootstrap.read_text(encoding="utf-8"):
            raise ValidationError("native save fixture must remain developer-controlled and dormant in release bootstrap")


def _read(path: Path) -> bytes:
    try:
        return path.read_bytes()
    except OSError as error:
        raise ValidationError(f"cannot read {path}: {error}") from error


def _u32(data: bytes, offset: int, label: str) -> int:
    if len(data) < offset + 4:
        raise ValidationError(f"{label} is truncated")
    return struct.unpack_from("<I", data, offset)[0]


def _validate_w3e(path: Path) -> tuple[int, int]:
    data = _read(path)
    if data[:4] != b"W3E!":
        raise ValidationError("war3map.w3e has an invalid W3E header")
    if _u32(data, 4, "war3map.w3e") not in (11, 12):
        raise ValidationError("war3map.w3e uses an unsupported format version")

    offset = 13
    ground_tiles = _u32(data, offset, "war3map.w3e")
    offset += 4 + ground_tiles * 4
    cliff_tiles = _u32(data, offset, "war3map.w3e")
    offset += 4 + cliff_tiles * 4
    width = _u32(data, offset, "war3map.w3e")
    height = _u32(data, offset + 4, "war3map.w3e")
    if width < 2 or height < 2:
        raise ValidationError("war3map.w3e has invalid terrain dimensions")
    expected_size = offset + 16 + width * height * 7
    if len(data) != expected_size:
        raise ValidationError(
            f"war3map.w3e size is malformed: expected {expected_size}, got {len(data)}"
        )
    return width, height


def _validate_wpm(path: Path, terrain: tuple[int, int]) -> None:
    data = _read(path)
    if data[:4] != b"MP3W":
        raise ValidationError("war3map.wpm has an invalid pathing header")
    width = _u32(data, 8, "war3map.wpm")
    height = _u32(data, 12, "war3map.wpm")
    if len(data) != 16 + width * height:
        raise ValidationError("war3map.wpm dimensions do not match its payload")
    terrain_width, terrain_height = terrain
    expected = ((terrain_width - 1) * 4, (terrain_height - 1) * 4)
    if (width, height) != expected:
        raise ValidationError(
            f"war3map.wpm dimensions {(width, height)} do not match terrain {expected}"
        )


def _validate_counted_file(path: Path, magic: bytes, label: str) -> None:
    data = _read(path)
    if data[:4] != magic or len(data) < 16:
        raise ValidationError(f"{label} has an invalid or truncated header")
    count = _u32(data, 12, label)
    if count != 0 and label == "war3map.doo":
        raise ValidationError("the clean placeholder map must not contain doodads")
    if label == "war3mapUnits.doo":
        if count != 1 or b"sloc" not in data or len(data) != 127:
            raise ValidationError(
                "the clean placeholder map must contain exactly one stock start location"
            )


def _validate_wts(path: Path, expected_name: str) -> None:
    text = _read(path).decode("utf-8-sig")
    entries = dict(
        re.findall(r"(?ms)^STRING\s+(\d+)\s*\n\{\s*\n(.*?)\n\}", text)
    )
    if entries.get("8", "").strip() != expected_name:
        raise ValidationError("war3map.wts STRING 8 must contain the canonical map name")
    required_ids = {"1", "2", "8", "9", "10"}
    if not required_ids.issubset(entries):
        raise ValidationError("war3map.wts is missing required metadata strings")
    if entries["10"].strip() != EXPECTED_METADATA["author"]:
        raise ValidationError("war3map.wts STRING 10 must contain the canonical author")


def validate(manifest_path: Path) -> Path:
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValidationError(f"invalid map source manifest: {error}") from error
    if manifest.get("format") != "warcraft-3-folder-map" or manifest.get("formatVersion") != 1:
        raise ValidationError("map source manifest has an unsupported format")
    if manifest.get("metadata") != EXPECTED_METADATA:
        raise ValidationError("map source manifest metadata is not canonical")
    try:
        build_config = (PROJECT_ROOT / "wurst.build").read_text(encoding="utf-8")
    except OSError as error:
        raise ValidationError(f"cannot read wurst.build: {error}") from error
    required_config = (
        "scriptMode: LUA",
        "wc3Patch: v3.0",
        "name: \"Age of Sail: The World\"",
        "author: WarCraftMap Project",
    )
    missing_config = [entry for entry in required_config if entry not in build_config]
    if missing_config:
        raise ValidationError("wurst.build is not connected to canonical map metadata: " + ", ".join(missing_config))
    validate_compatibility_boundary(PROJECT_ROOT)

    map_name = manifest.get("mapDirectory")
    if not isinstance(map_name, str) or not map_name.endswith(".w3x"):
        raise ValidationError("mapDirectory must name a .w3x folder")
    map_dir = manifest_path.parent / map_name
    if not map_dir.is_dir():
        raise ValidationError(f"map folder is missing: {map_dir}")

    required = manifest.get("requiredFiles")
    if not isinstance(required, list) or not required or len(required) != len(set(required)):
        raise ValidationError("requiredFiles must be a non-empty list without duplicates")
    missing = [name for name in required if not (map_dir / name).is_file()]
    if missing:
        raise ValidationError("required map files are missing: " + ", ".join(sorted(missing)))

    hashes = manifest.get("binarySha256")
    if not isinstance(hashes, dict):
        raise ValidationError("binarySha256 must record the opaque binary inputs")
    for name, expected_hash in hashes.items():
        if name not in required or not re.fullmatch(r"[0-9a-f]{64}", expected_hash):
            raise ValidationError(f"invalid binary checksum entry: {name}")
        actual_hash = hashlib.sha256(_read(map_dir / name)).hexdigest()
        if actual_hash != expected_hash:
            raise ValidationError(f"binary source differs from canonical checksum: {name}")

    terrain = _validate_w3e(map_dir / "war3map.w3e")
    _validate_wpm(map_dir / "war3map.wpm", terrain)
    _validate_counted_file(map_dir / "war3map.doo", b"W3do", "war3map.doo")
    _validate_counted_file(map_dir / "war3mapUnits.doo", b"W3do", "war3mapUnits.doo")
    _validate_wts(map_dir / "war3map.wts", EXPECTED_METADATA["name"])

    w3i = _read(map_dir / "war3map.w3i")
    try:
        validate_current_w3i(w3i)
    except MapInfoError as error:
        raise ValidationError(str(error)) from error
    if b"TRIGSTR_008\0" not in w3i:
        raise ValidationError("war3map.w3i does not reference the canonical map-name string")

    shadow = _read(map_dir / "war3map.shd")
    expected_shadow_size = (terrain[0] - 1) * (terrain[1] - 1) * 16
    if len(shadow) != expected_shadow_size:
        raise ValidationError("war3map.shd size does not match terrain dimensions")
    for empty_name in ("war3map.mmp", "war3map.w3c", "war3map.w3r"):
        if len(_read(map_dir / empty_name)) < 8:
            raise ValidationError(f"{empty_name} is truncated")
    return map_dir


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", nargs="?", type=Path, default=DEFAULT_MANIFEST)
    args = parser.parse_args(argv)
    try:
        map_dir = validate(args.manifest.resolve())
    except ValidationError as error:
        print(f"map source validation failed: {error}", file=sys.stderr)
        return 1
    print(f"map source validation passed: {map_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
