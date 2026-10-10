#!/usr/bin/env python3
"""Build one hash-bound, manual-only package-init isolation experiment.

This does not compile a repair or run Warcraft. The original campaign is never
changed. Only the selector's Lua member and its outer manifest digest change.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile
import zipfile
import zlib

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[3] / "_shared/tooling"))
from independent_mpq import load_reader, open_archive, read_member
from warcraft_campaign import MpqReader
from isolation_lua import isolation_script
from mpq_patch import replace_member

BASELINE_W3N = "4f2f9cf8ca56f81aaeca524f257ae15e273c2366e52adfaa1eafdf5b996ff9ad"
BASELINE_W3X = "3c953659969c956e509093cb2732aaf1e2d94ed6355556a98204637ab1cb1f16"
BASELINE_LUA = "efaffe67682ca0c3c952722ce0a5f42be1ba954a27c5ad49177f48b6c536ebe3"
BASELINE_REVISION = "1bdfe32feae8775979735d89a379ecfdd0b28c83"
MAP_PATH = "Maps/AgeOfSailWorld.w3x"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def pinned(path, expected):
    data = path.read_bytes()
    if sha(data) != expected:
        raise ValueError(f"input pin mismatch: {path.name}")
    return data


def verified_members(data, independent_reader):
    """Repo reader enumerates; independently decode every non-encrypted member."""
    with tempfile.TemporaryDirectory(prefix="438-read-") as temporary:
        path = Path(temporary) / "archive.mpq"
        path.write_bytes(data)
        repo = MpqReader(path)
        members = repo.members()
        independent = open_archive(independent_reader, data)
        exclusions = []
        for name, payload in members.items():
            # Grill's encrypted listfile is not supported by the pinned mpyq.
            entry = independent.get_hash_table_entry(name.replace("/", "\\"))
            if entry is None:
                raise ValueError(f"independent reader cannot find {name}")
            flags = independent.block_table[entry.block_table_index].flags
            if flags & 0x10000:
                if name != "(listfile)":
                    raise ValueError(f"unexpected encrypted member {name}")
                exclusions.append(name)
                continue
            if read_member(independent, name) != payload:
                raise ValueError(f"independent extraction disagrees: {name}")
        return members, exclusions


def changed_members(before, after):
    if before.keys() != after.keys():
        raise ValueError("member set changed")
    return sorted(name for name in before if before[name] != after[name])


def build(campaign: Path, reader_path: Path, control_root: Path, output: Path):
    if output.exists() or output.with_suffix(".zip").exists():
        raise ValueError("use a new output directory; previous evidence is never overwritten")
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=HERE, text=True).strip()
    recipe_paths = [HERE / name for name in
                    ("build_isolation.py", "isolation_lua.py", "mpq_patch.py",
                     "OWNER-TEST.md", "CONTROL-PROVENANCE.md", "control-provenance.json")]
    recipe_paths += [HERE.parents[3] / "_shared/tooling" / name
                     for name in ("independent_mpq.py", "warcraft_campaign.py")]
    # The commit names the exact recipe. Receipts may be committed afterwards.
    for path in recipe_paths:
        relative = subprocess.check_output(["git", "ls-files", "--full-name", "--", str(path)],
                                           cwd=HERE, text=True).strip()
        if not relative or subprocess.check_output(["git", "show", f"{revision}:{relative}"], cwd=HERE) != path.read_bytes():
            raise ValueError("commit the exact recipe before building a source-bound diagnostic")
    control = json.loads((HERE / "control-provenance.json").read_text())
    positive = pinned(control_root / control["map"]["path"], control["map"]["sha256"])
    license_bytes = pinned(control_root / "LICENSE", control["license"]["sha256"])
    pinned(control_root / control["publishedNativeEvidence"]["source"],
           control["publishedNativeEvidence"]["sha256"])
    original = pinned(campaign, BASELINE_W3N)
    reader = load_reader(reader_path)
    outer_before, _ = verified_members(original, reader)
    selector = outer_before[MAP_PATH.lower()]
    if sha(selector) != BASELINE_W3X:
        raise ValueError("selector pin mismatch")
    map_before, exclusions = verified_members(selector, reader)
    old_lua = map_before["war3map.lua"]
    if sha(old_lua) != BASELINE_LUA:
        raise ValueError("Lua pin mismatch")
    new_lua = isolation_script(old_lua)
    revised_map = replace_member(selector, "war3map.lua", new_lua)
    map_after, after_exclusions = verified_members(revised_map, reader)
    if changed_members(map_before, map_after) != ["war3map.lua"] or exclusions != after_exclusions:
        raise ValueError("isolation changed a non-Lua map member")
    original_manifest = outer_before["campaign-manifest.json"]
    if original_manifest.count(BASELINE_W3X.encode()) != 1:
        raise ValueError("selector digest is not unique in original manifest")
    revised_manifest = original_manifest.replace(BASELINE_W3X.encode(), sha(revised_map).encode())
    revised_campaign = replace_member(original, MAP_PATH, revised_map)
    revised_campaign = replace_member(revised_campaign, "campaign-manifest.json", revised_manifest)
    outer_after, _ = verified_members(revised_campaign, reader)
    if changed_members(outer_before, outer_after) != sorted([MAP_PATH.lower(), "campaign-manifest.json"]):
        raise ValueError("unexpected campaign member change")
    for row in json.loads(revised_manifest)["maps"]:
        if sha(outer_after[row["packagePath"].lower()]) != row["sha256"]:
            raise ValueError("revised campaign manifest mismatch")
    if len(revised_campaign) != len(original) or len(revised_map) != len(selector):
        raise ValueError("archive offsets must remain stable")
    identity = f"438-isolate-g{revision[:12]}-h{sha(revised_campaign)[:12]}"
    campaign_name = f"AgeOfSailWorldCampaign-{identity}.w3n"
    output.mkdir(parents=True)
    (output / "Campaigns").mkdir()
    (output / "Controls").mkdir()
    (output / "Campaigns" / campaign_name).write_bytes(revised_campaign)
    (output / "Controls/BalanceBenchStockTest.w3x").write_bytes(positive)
    negative = b"MPQ\x1a\x00"
    (output / "Controls/CorruptControl.w3x").write_bytes(negative)
    (output / "Controls/BalanceBench-LICENSE.txt").write_bytes(license_bytes)
    shutil.copyfile(HERE / "OWNER-TEST.md", output / "README.md")
    shutil.copyfile(HERE / "CONTROL-PROVENANCE.md", output / "CONTROL-PROVENANCE.md")
    receipt = {
        "format": "warcraftmap_package_init_isolation_v1",
        "identity": identity,
        "purpose": "diagnostic_only_not_a_gameplay_repair",
        "recipeRevision": revision,
        "recipeFiles": {p.name: sha(p.read_bytes()) for p in recipe_paths},
        "recipeRuntime": {"python": platform.python_version(), "zlib": zlib.ZLIB_RUNTIME_VERSION},
        "baselineSourceRevision": BASELINE_REVISION,
        "baselineW3nSha256": BASELINE_W3N,
        "baselineW3xSha256": BASELINE_W3X,
        "baselineLuaSha256": BASELINE_LUA,
        "campaignFile": "Campaigns/" + campaign_name,
        "campaignSha256": sha(revised_campaign),
        "selectorPath": MAP_PATH,
        "selectorSha256": sha(revised_map),
        "luaSha256": sha(new_lua),
        "positiveControl": control,
        "negativeControl": {"file": "Controls/CorruptControl.w3x", "sha256": sha(negative)},
        "verification": {
            "reader": "pinned_mpyq_plus_repository_reader",
            "independentEncryptedMemberExclusions": exclusions,
            "campaignChangedMembers": changed_members(outer_before, outer_after),
            "selectorChangedMembers": changed_members(map_before, map_after),
            "unchangedRegionalMaps": 16,
            "unchangedW3f": True,
            "unchangedW3i": True,
            "allManifestMapHashesVerified": True,
            "archiveLengthsAndUnrelatedMemberOffsetsPreserved": True,
        },
        "nativeStatus": "not_run",
        "realClientLaunchBaseline": "failed",
        "diagnosis": "diagnosis_unconfirmed",
        "releaseCandidate": False,
        "sourceIdentityWarning": "Archived build identity describes original compiled inputs. Recipe revision and this receipt describe the diagnostic Lua override; this is not a freshly compiled campaign.",
    }
    (output / "diagnostic.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    files = sorted(p for p in output.rglob("*") if p.is_file())
    (output / "SHA256SUMS.txt").write_text("".join(f"{sha(p.read_bytes())}  {p.relative_to(output).as_posix()}\n" for p in files))
    with zipfile.ZipFile(output.with_suffix(".zip"), "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(p for p in output.rglob("*") if p.is_file()):
            info = zipfile.ZipInfo(path.relative_to(output).as_posix(), date_time=(2026, 10, 10, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, path.read_bytes(), compresslevel=9)
    if campaign.read_bytes() != original:
        raise ValueError("baseline changed during preparation")
    return receipt


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("campaign", "reader", "control-root", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    result = build(args.campaign, args.reader, args.control_root, args.output)
    print(json.dumps({key: result[key] for key in ("identity", "campaignSha256", "selectorSha256", "nativeStatus")}, indent=2))
