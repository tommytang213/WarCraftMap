#!/usr/bin/env python3
"""Prepare one bound, nonrelease destination-script control; never launch Warcraft.

Only EuropeCentralEast.w3x/war3map.lua may change in decoded campaign content.
The embedded campaign manifest and source identity intentionally retain baseline
provenance. They do NOT attest the transformed map: the external receipt does.
This tool cannot grant release approval or native acceptance.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
import sys
import tempfile
import zlib

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT.parent / "_shared/tooling"))
from warcraft_campaign import (FILE_COMPRESS, FILE_EXISTS, FILE_SINGLE_UNIT, HASH_EMPTY,
                              MpqReader, _encrypt, _hash)
from warcraft_lua_startup import _tokens, startup_failures
from warcraft_map_info import validate_w3i_structure

BASELINE_SHA256 = "b2f9dfa2ab04d54d97f465aeb11c80a5f4f7852b850d58a82a4cf7d8d2665ba8"
BASELINE_REVISION = "54911cabe2a993b22f3a5d05b549df5dc3995c9c"
BASELINE_MAP_SHA256 = "7a52b5ef128a1ff313271754a6aeba856bb9ae5f9917fb0dff642ff9561d3364"
DESTINATION = "EuropeCentralEast.w3x"
SCRIPT = "war3map.lua"
TEMPLATE = Path(__file__).with_name("diagnostics") / "destination_entry.lua"
FORMAT = "warcraftmap_destination_script_isolation_v1"
CONFIG_NATIVE_GLOBALS = {
    "SetMapName", "SetMapDescription", "SetPlayers", "SetTeams", "SetGamePlacement",
    "DefineStartLocation", "Player", "SetPlayerStartLocation", "ConvertPlayerColor",
    "SetPlayerColor", "SetPlayerRacePreference", "SetPlayerRaceSelectable",
    "SetPlayerController", "SetPlayerTeam", "SetStartLocPrioCount", "SetEnemyStartLocPrioCount",
    "MAP_PLACEMENT_TEAMS_TOGETHER", "RACE_PREF_HUMAN", "MAP_CONTROL_USER",
}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _complete_archive(path: Path) -> tuple[MpqReader, dict[str, bytes]]:
    archive = MpqReader(path)
    members = archive.members()  # Decrypts listfile and checks every live hash entry.
    referenced = {row[4] for row in archive.hashes if row[4] not in (HASH_EMPTY, HASH_EMPTY - 1)}
    live_blocks = {i for i, row in enumerate(archive.blocks) if row[3] & FILE_EXISTS}
    if referenced != live_blocks:
        raise ValueError("refusing to discard unenumerated live MPQ blocks")
    if {"(attributes)", "(signature)"} & members.keys():
        raise ValueError("MPQ attributes/signatures require a separate preservation design")
    archive_size = struct.unpack_from("<I", archive.data, archive.base + 8)[0]
    if archive.base + archive_size != len(archive.data):
        raise ValueError("refusing to discard unknown bytes after the MPQ archive")
    return archive, members


def _block(archive: MpqReader, name: str) -> tuple[int, tuple[int, int, int, int]]:
    rows = [row for row in archive.hashes if row[:2] == (_hash(name, 1), _hash(name, 2))]
    if len(rows) != 1:
        raise ValueError("missing or ambiguous MPQ block: " + name)
    index = rows[0][4]
    return index, archive.blocks[index]


def _block_description(index: int, row: tuple[int, int, int, int]) -> dict:
    offset, packed, size, flags = row
    return {"index": index, "offset": offset, "packedBytes": packed, "decodedBytes": size, "flags": hex(flags)}


def _same_outside(before: bytes, after: bytes, regions: list[tuple[int, int]]) -> bool:
    if len(before) != len(after):
        return False
    at = 0
    for start, length in sorted(regions):
        if start < at or start + length > len(before) or before[at:start] != after[at:start]:
            return False
        at = start + length
    return before[at:] == after[at:]


def _encode_sectors(script: bytes, sector_size: int) -> bytes:
    if not script:
        raise ValueError("diagnostic Lua must not be empty")
    sectors = []
    for at in range(0, len(script), sector_size):
        plain = script[at:at + sector_size]
        compressed = b"\x02" + zlib.compress(plain, level=9)
        sectors.append(compressed if len(compressed) < len(plain) else plain)
    offsets = [(len(sectors) + 1) * 4]
    for sector in sectors:
        offsets.append(offsets[-1] + len(sector))
    return struct.pack(f"<{len(offsets)}I", *offsets) + b"".join(sectors)


def _patch_script(archive: MpqReader, script: bytes) -> tuple[bytes, dict]:
    """Keep the map's format, length, offsets and all other packed blocks intact."""
    index, original_row = _block(archive, SCRIPT)
    offset, packed, size, flags = original_row
    if flags != FILE_EXISTS | FILE_COMPRESS:
        raise ValueError("destination script must use unencrypted zlib sectors without CRC")
    if len(script) >= size:
        raise ValueError("diagnostic script must be shorter than the original runtime")
    sector_size = 512 << archive.block_shift
    compressed = _encode_sectors(script, sector_size)
    if len(compressed) > packed:
        raise ValueError("diagnostic script does not fit in the original packed slot")
    (_, _, _, _, _, hash_at, block_at, hash_count, block_count) = struct.unpack_from(
        "<4sIIHHIIII", archive.data, archive.base)
    if not (32 <= offset and offset + packed <= min(hash_at, block_at)):
        raise ValueError("unexpected script/table layout; fixed-slot patch refused")
    changed = bytearray(archive.data)
    start = archive.base + offset
    changed[start:start + len(compressed)] = compressed
    # Retain the old slot tail verbatim. It is now unreferenced inert padding;
    # no unknown member is discarded, and every following block stays in place.
    blocks = list(archive.blocks)
    blocks[index] = (offset, len(compressed), len(script), flags)
    table = b"".join(struct.pack("<IIII", *row) for row in blocks)
    table = _encrypt(table, _hash("(block table)", 3))
    table_start = archive.base + block_at
    changed[table_start:table_start + len(table)] = table
    result = bytes(changed)
    if not _same_outside(archive.data, result, [(start, len(compressed)), (table_start, len(table))]):
        raise ValueError("fixed-slot patch changed bytes outside the script/table regions")
    return result, {"method": "fixed_slot_sector_patch", "archiveLengthPreserved": True,
                    "scriptBlockBefore": _block_description(index, original_row),
                    "scriptBlockAfter": _block_description(index, blocks[index]),
                    "sectorBytes": sector_size, "hashTableOffset": hash_at,
                    "hashTableBytes": hash_count * 16, "blockTableOffset": block_at,
                    "blockTableBytes": block_count * 16,
                    "allowedMapByteRegions": [{"offset": start, "bytes": len(compressed), "meaning": "new compressed script prefix"},
                                              {"offset": table_start, "bytes": len(table), "meaning": "encrypted block table; only script row differs when decoded"}],
                    "unchangedScriptSlotTailBytes": packed - len(compressed),
                    "scriptSlotTail": "retained byte-for-byte as inert padding outside the shortened script block"}


def extract_config(script: bytes) -> bytes:
    """Extract the pinned compiler's column-zero config declaration exactly.

    This is intentionally a bound compiler-layout check, not a general Lua parser.
    Its internal block endings are indented; only the function end is column zero.
    """
    matches = list(re.finditer(rb"(?m)^function config\(\)[^\r\n]*\r?\n.*?^end(?:\r?\n|$)", script, re.S))
    if len(matches) != 1:
        raise ValueError("expected one pinned-compiler config() declaration")
    config = matches[0].group()
    if config.count(b"__wurst_init_bootstrap()") != 1:
        raise ValueError("unexpected config bootstrap adapter contract")
    tokens = _tokens(config.decode("utf-8"))
    local_names = {tokens[i + 1] for i, token in enumerate(tokens[:-1]) if token == "local"}
    identifiers = {token for token in tokens if re.fullmatch(r"[A-Za-z_]\w*", token)}
    keywords = {"function", "end", "local", "nil", "false", "true", "if", "then", "not"}
    unknown = identifiers - local_names - CONFIG_NATIVE_GLOBALS - keywords - {"config", "__wurst_init_bootstrap"}
    if unknown:
        raise ValueError("config depends on globals excluded by the diagnostic: " + ", ".join(sorted(unknown)))
    return config


def _verify_spawn(members: dict[str, bytes]) -> dict:
    runtime = json.loads(members["runtime/scenario-runtime.json"])
    physical = json.loads(members["runtime/physical-map.json"])
    origins = [row for row in runtime["newCampaignOrigins"] if row["polityId"] == "austria"]
    settlements = [row for row in physical["objects"]["settlements"] if row["id"] == "vienna"]
    expected = {"physicalMapId": "europe_central_east", "regionalInstanceId": "europe_central_alpine",
                "settlementId": "vienna", "worldPosition": [576.0, 64.0]}
    if (len(origins) != 1 or origins[0]["startingLocation"] != expected or len(settlements) != 1
            or settlements[0]["world"] != expected["worldPosition"]
            or physical["physicalMapId"] != expected["physicalMapId"]):
        raise ValueError("baseline Austria/Vienna spawn records do not agree")
    info = validate_w3i_structure(members["war3map.w3i"])
    bounds = info["cameraBounds"]
    if not (min(bounds[::2]) < 576 < max(bounds[::2]) and min(bounds[1::2]) < 64 < max(bounds[1::2])):
        raise ValueError("Austria spawn lies outside original camera bounds")
    # Confirm the materializer's 32-world-unit pathing pixels around the spawn.
    w3e, wpm = members["war3map.w3e"], members["war3map.wpm"]
    if w3e[:8] != b"W3E!" + struct.pack("<I", 11) or wpm[:8] != b"MP3W\0\0\0\0":
        raise ValueError("unsupported baseline terrain/pathing layout")
    at = 13
    ground = struct.unpack_from("<I", w3e, at)[0]
    at += 4 + ground * 4
    cliffs = struct.unpack_from("<I", w3e, at)[0]
    at += 4 + cliffs * 4
    width, height, left, bottom = struct.unpack_from("<IIff", w3e, at)
    pw, ph = struct.unpack_from("<II", wpm, 8)
    if (pw, ph) != ((width - 1) * 4, (height - 1) * 4) or len(wpm) != 16 + pw * ph:
        raise ValueError("baseline pathing dimensions differ from terrain")
    px, py = int((576 - left) // 32), int((64 - bottom) // 32)
    pixels = [(x, y) for y in range(py - 1, py + 2) for x in range(px - 1, px + 2)]
    if any(not (0 <= x < pw and 0 <= y < ph) or wpm[16 + y * pw + x] & 0x02 for x, y in pixels):
        raise ValueError("baseline Austria spawn neighborhood blocks walking")
    return {"origin": "austria", **expected, "cameraBounds": list(bounds),
            "pathing": {"walkablePixelsChecked": len(pixels), "centerPixel": [px, py]},
            "evidenceLevel": "archived_data_static; native pathing and movement not_run"}


def make_script(original: bytes, camera_bounds: list[float], template: bytes | None = None) -> bytes:
    template = TEMPLATE.read_bytes() if template is None else template
    config = extract_config(original)
    models = re.findall(rb"(?m)^\s*SetDayNightModels\([^\r\n]+\)", original)
    template_models = re.findall(rb"(?m)^\s*SetDayNightModels\([^\r\n]+\)", template)
    if len(models) != 1 or len(template_models) != 1 or models[0].strip() != template_models[0].strip():
        raise ValueError("diagnostic must retain the original terrain/unit lighting models")
    for token in (b"-- @BASELINE_CONFIG@", b"-- @CAMERA_BOUNDS@"):
        if template.count(token) != 1:
            raise ValueError("diagnostic source has missing or duplicate substitution token")
    result = template.replace(b"-- @BASELINE_CONFIG@", config.rstrip(b"\r\n"))
    result = result.replace(b"-- @CAMERA_BOUNDS@", ", ".join(repr(value) for value in camera_bounds).encode())
    if extract_config(result) != config:
        raise ValueError("diagnostic changed the original config() declaration")
    failures = startup_failures(result)
    if failures:
        raise ValueError("diagnostic Lua entry contract failed: " + "; ".join(failures))
    return result


def _diff(before: dict[str, bytes], after: dict[str, bytes]) -> list[dict]:
    if before.keys() != after.keys():
        raise ValueError("isolation must not add or remove any archive members")
    return [{"member": name, "beforeSha256": sha(before[name]), "afterSha256": sha(after[name]),
             "beforeBytes": len(before[name]), "afterBytes": len(after[name])}
            for name in sorted(before) if before[name] != after[name]]


def replace_script(campaign: Path, script: bytes, output: Path) -> dict:
    """Patch and verify the single-member delta; inputs may be test fixtures.

    Public preparation below additionally enforces the exact failed artifact and
    source revision. Neither this helper nor the CLI modifies the baseline.
    """
    if output.exists() or output.resolve() == campaign.resolve():
        raise ValueError("diagnostic output must be a new file")
    original = campaign.read_bytes()
    outer, outer_members = _complete_archive(campaign)
    target = DESTINATION.lower()
    with tempfile.TemporaryDirectory(prefix="destination-script-isolation-") as directory:
        work = Path(directory)
        old_map = work / "baseline.w3x"
        old_map.write_bytes(outer_members[target])
        nested, nested_members = _complete_archive(old_map)
        if script == nested_members[SCRIPT]:
            raise ValueError("unchanged script cannot relabel a failed campaign")
        patched_map, layout = _patch_script(nested, script)
        outer_index, outer_row = _block(outer, target)
        offset, packed, size, flags = outer_row
        if flags != FILE_EXISTS | FILE_SINGLE_UNIT or packed != size or len(patched_map) != size:
            raise ValueError("outer destination must be a fixed-size uncompressed single-unit block")
        changed = bytearray(original)
        start = outer.base + offset
        changed[start:start + size] = patched_map
        if not _same_outside(original, changed, [(start, size)]):
            raise ValueError("outer campaign changed outside destination payload")
        new_outer = work / "control.w3n"
        new_outer.write_bytes(changed)
        reopened_outer, checked_outer = _complete_archive(new_outer)
        checked_map = work / "reopened.w3x"
        checked_map.write_bytes(checked_outer[target])
        reopened_nested, checked_nested = _complete_archive(checked_map)
        outer_diff = _diff(outer_members, checked_outer)
        nested_diff = _diff(nested_members, checked_nested)
        if [row["member"] for row in outer_diff] != [target] or [row["member"] for row in nested_diff] != [SCRIPT]:
            raise ValueError("control changed a member outside the destination script")
        if checked_nested[SCRIPT] != script or reopened_outer.hashes != outer.hashes or reopened_outer.blocks != outer.blocks:
            raise ValueError("script bytes or outer MPQ tables differ from the intended patch")
        script_index = layout["scriptBlockBefore"]["index"]
        if reopened_nested.hashes != nested.hashes or any(
                before != after for i, (before, after) in enumerate(zip(nested.blocks, reopened_nested.blocks))
                if i != script_index):
            raise ValueError("nested MPQ tables changed outside the script block row")
        for i, (at, length, _, _) in enumerate(nested.blocks):
            if i != script_index and nested.data[nested.base + at:nested.base + at + length] != patched_map[nested.base + at:nested.base + at + length]:
                raise ValueError("a non-script packed block changed")
        if campaign.read_bytes() != original:
            raise ValueError("baseline campaign changed while preparing diagnostic")
        result = {"campaignSha256": sha(new_outer.read_bytes()), "baselineSha256": sha(original),
                  "destinationBeforeSha256": sha(outer_members[target]),
                  "destinationAfterSha256": sha(checked_outer[target]),
                  "outerMemberCount": len(outer_members), "destinationMemberCount": len(nested_members),
                  "outerMemberDiff": outer_diff, "destinationMemberDiff": nested_diff,
                  "unchangedOuterMembers": len(outer_members) - 1,
                  "unchangedDestinationMembers": len(nested_members) - 1,
                  "completeMemberEnumeration": True,
                  "containerPreservation": {**layout,
                      "campaignBytes": len(original), "destinationBytes": size,
                      "outerDestinationBlock": _block_description(outer_index, outer_row),
                      "outerHeaderAndTablesByteIdentical": True,
                      "innerHeaderAndHashTableByteIdentical": True,
                      "allOtherDecodedBlockRowsIdentical": True,
                      "allOtherPackedBlocksByteIdentical": True,
                      "campaignAndDestinationLengthsIdentical": True,
                      "allowedCampaignByteRegions": [{**row, "offset": start + row["offset"]}
                                                     for row in layout["allowedMapByteRegions"]]}}
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("xb") as destination:
            destination.write(new_outer.read_bytes())
    return result


def prepare(campaign: Path, output: Path) -> dict:
    if output.exists():
        raise ValueError("use a new diagnostic directory; existing artifacts are never overwritten")
    if campaign.suffix.lower() != ".w3n":
        raise ValueError("input must retain its installed .w3n filename")
    original = campaign.read_bytes()
    if sha(original) != BASELINE_SHA256:
        raise ValueError("destination isolation is bound to failed baseline " + BASELINE_SHA256)
    _, outer_members = _complete_archive(campaign)
    map_bytes = outer_members[DESTINATION.lower()]
    if sha(map_bytes) != BASELINE_MAP_SHA256:
        raise ValueError("baseline destination hash mismatch")
    with tempfile.TemporaryDirectory(prefix="destination-isolation-prepare-") as directory:
        work = Path(directory)
        source = work / "baseline.w3x"
        source.write_bytes(map_bytes)
        _, members = _complete_archive(source)
        identity = json.loads(members["runtime/build-identity.json"])
        if identity.get("sourceRevision") != BASELINE_REVISION:
            raise ValueError("baseline source revision mismatch")
        spawn = _verify_spawn(members)
        script = make_script(members[SCRIPT], spawn["cameraBounds"])
        transformed = work / "control.w3n"
        changes = replace_script(campaign, script, transformed)
        from stage_launch_smoke import reject_failed_digest
        reject_failed_digest(changes["campaignSha256"])
        # A new directory, receipt and content hash distinguish the control;
        # changing the installed campaign filename would add another variable.
        name = campaign.name
        result = {"format": FORMAT, "transformation": "replace_destination_script_only",
                  "releaseCandidate": False, "playerTestRequested": False,
                  "nativeStatus": "native_not_run", "campaign_native": "not_run",
                  "origin_to_region_native": "not_run", "diagnosis": "diagnosis_unconfirmed",
                  "baselineSourceIdentity": identity, "baselineNativeStatus": "failed_after_victory_continue",
                  "destination": DESTINATION, "changedContentPath": DESTINATION + "/" + SCRIPT,
                  "outputCampaign": name, **changes, "spawn": spawn,
                  "externalFilenamePreserved": True,
                  "filenameConstraint": "input basename must match the previously failed installed W3N filename",
                  "originalConfigSha256": sha(extract_config(members[SCRIPT])),
                  "configPreservedByteForByte": True,
                  "configGlobals": "all dependencies are original Warcraft natives/constants, local variables, or the explicit no-op adapter",
                  "wurstBootstrapAdapter": "explicit no-op; regional generated globals excluded from isolation",
                  "diagnosticScriptSha256": sha(script),
                  "transformationSources": {Path(__file__).relative_to(PROJECT).as_posix(): sha(Path(__file__).read_bytes()),
                                            TEMPLATE.relative_to(PROJECT).as_posix(): sha(TEMPLATE.read_bytes())},
                  "embeddedManifest": {"preservedByteForByte": True, "meaning": "baseline provenance only",
                                       "destinationChecksumDescribesBaseline": True,
                                       "validReleaseManifestForTransformation": False},
                  "campaignSaveContract": "selector unchanged; destination control never opens, consumes, acknowledges, or saves campaign cache",
                  "acceptance": "visible destination terrain and selected unit responding to movement; heartbeat or Victory alone is insufficient"}
        if campaign.read_bytes() != original:
            raise ValueError("baseline changed before diagnostic output")
        output.mkdir(parents=True, exist_ok=False)
        (output / name).write_bytes(transformed.read_bytes())
        (output / SCRIPT).write_bytes(script)
        (output / "destination-isolation.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
        (output / "SHA256SUMS.txt").write_text(changes["campaignSha256"] + "  " + name + "\n" + sha(script) + "  " + SCRIPT + "\n")
        (output / "DIAGNOSTIC-ONLY.txt").write_text(
            "Developer-owned destination-script isolation. NOT A RELEASE OR A CLAIMED FIX.\n"
            "Native execution: NOT RUN. No player retest is requested.\n"
            "The failed baseline and every other decoded campaign/map member are preserved.\n"
            "Only EuropeCentralEast.w3x/war3map.lua changes in decoded content.\n"
            "The new compressed script occupies its original slot; only its block row changes.\n"
            "Archive lengths, headers, hash tables and all other packed members stay identical.\n"
            "Unused bytes in the old script slot remain unchanged as inert padding.\n"
            "The encrypted inner block table is updated; only the script row differs decoded.\n"
            "The embedded destination checksum is INTENTIONALLY STALE baseline provenance.\n"
            "This transformed map CANNOT PASS RELEASE MANIFEST VERIFICATION.\n"
            "Use destination-isolation.json for transformation hashes and exact member differences.\n"
            "The input W3N filename is preserved: use the same name as the failed installed W3N.\n"
            "The selector still uses ChangeLevel(path, true); all campaign paths and W3F are unchanged.\n"
            "The destination creates a stock controllable Footman at archived Vienna (576, 64).\n"
            "A visible heartbeat proves callback activity, not player movement or release readiness.\n"
            "Success requires terrain and the selected unit responding to a movement order.\n"
            "The destination never consumes or changes campaign saves; the unchanged selector\n"
            "still commits its normal pending origin request. Gameplay systems are absent.\n")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--campaign", type=Path, required=True, help="exact failed b2f9dfa2... baseline W3N")
    parser.add_argument("--output", type=Path, required=True, help="new local diagnostic directory")
    args = parser.parse_args()
    try:
        result = prepare(args.campaign, args.output)
    except (OSError, ValueError, KeyError, struct.error, zlib.error) as error:
        print("destination isolation refused: " + str(error), file=sys.stderr)
        return 1
    print(json.dumps({key: result[key] for key in ("format", "baselineSha256", "campaignSha256", "nativeStatus", "outputCampaign")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
