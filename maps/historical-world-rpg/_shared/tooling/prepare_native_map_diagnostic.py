#!/usr/bin/env python3
"""Prepare exact standalone maps with an independent reader; never launch a game."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import shutil

from independent_mpq import READER_REVISION, READER_SHA256, load_reader, open_archive, read_member, sha256


def prepare(campaign: Path, expected_sha: str, reader_path: Path, output: Path,
            map_path: str, build_evidence: Path | None = None) -> dict:
    if not re.fullmatch(r"[0-9a-f]{64}", expected_sha):
        raise ValueError("a full W3N SHA-256 is required")
    original = campaign.read_bytes()
    if sha256(original) != expected_sha:
        raise ValueError("W3N SHA-256 mismatch")
    if output.exists():
        raise ValueError("use a new diagnostic directory; original files are never overwritten")
    reader = load_reader(reader_path)
    outer = open_archive(reader, original)
    manifest = json.loads(read_member(outer, "campaign-manifest.json"))
    entries = manifest["maps"]
    if len({row["packagePath"].casefold() for row in entries}) != len(entries):
        raise ValueError("duplicate manifest map paths")
    selected = next((row for row in entries if row["packagePath"] == map_path), None)
    if selected is None:
        raise ValueError("requested map is not in the campaign manifest")
    maps, target, source = [], None, None
    # Reopen all actual maps but extract only the requested map. No member path
    # becomes a filesystem path, so malicious listfiles cannot write outside it.
    for entry in entries:
        data = read_member(outer, entry["packagePath"])
        if sha256(data) != entry["sha256"]:
            raise ValueError(f"nested map manifest hash mismatch: {entry['id']}")
        nested = open_archive(reader, data)
        identity = json.loads(read_member(nested, "runtime/build-identity.json"))
        if not re.fullmatch(r"[0-9a-f]{40}", identity.get("sourceRevision", "")) or not re.fullmatch(
                r"[0-9a-f]{64}", identity.get("sourceTreeSha256", "")):
            raise ValueError("invalid archived source identity")
        if source is not None and identity != source:
            raise ValueError("mixed map source identities")
        source = identity
        maps.append({"path": entry["packagePath"], "sha256": sha256(data)})
        if entry == selected:
            target = data
            # The adapter needs a Lua map, not the JASS reference fixture.
            read_member(nested, "war3map.lua")
    compiler = {"status": "not_verified"}
    if build_evidence:
        evidence = json.loads(build_evidence.read_text())
        if evidence["campaignSha256"] != expected_sha or evidence["sourceIdentity"] != source:
            raise ValueError("build evidence does not belong to these archive bytes")
        compiler = {"status": "reported_by_build_receipt", "receiptSha256": sha256(build_evidence.read_bytes()),
                    "wurstInterpreter": evidence["wurstInterpreter"]}
    map_sha = sha256(target)
    filename = f"selector-{map_sha[:16]}.w3x"
    # Deliberately invalid MPQ, never a mutation of the input or installed map.
    corrupted = b"MPQ\x1a\x00"
    result = {
        "format": "warcraftmap_native_diagnostic_v1", "source_revision": source["sourceRevision"],
        "sourceIdentity": source, "w3nSha256": expected_sha, "w3xSha256": map_sha,
        "mapPath": map_path, "mapFile": filename, "maps": maps,
        "static_archive": {"status": "passed", "scope": "independent extraction and all manifest map hashes",
                           "reader": "mpyq", "revision": READER_REVISION, "sha256": READER_SHA256},
        "compiler": compiler, "map_standalone_native": "not_run", "campaign_native": "not_run",
        "windowsClientBuild": None, "observedMilestone": "none",
        "runnerStatus": "native_runner_unavailable", "diagnosis": "diagnosis_unconfirmed",
        "positiveControl": {"status": "unavailable", "requires": "known-working 3.0 Lua W3X, hash and native provenance; JASS fixtures do not qualify"},
        "negativeControl": {"file": "corrupt-control.w3x", "sha256": sha256(corrupted), "native": "not_run"},
        "releaseCandidate": False, "playerTestRequested": False,
    }
    output.mkdir(parents=True)
    (output / filename).write_bytes(target)
    (output / "corrupt-control.w3x").write_bytes(corrupted)
    for name in ("wgc_local_adapter.py", "windows_diagnostic_job.py"):
        shutil.copyfile(Path(__file__).with_name(name), output / name)
    (output / "diagnostic.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    (output / "SHA256SUMS.txt").write_text(f"{map_sha}  {filename}\n{sha256(corrupted)}  corrupt-control.w3x\n")
    shutil.copyfile(Path(__file__).with_name("WGC_DIAGNOSTIC.md"), output / "README.md")
    if campaign.read_bytes() != original or (output / filename).read_bytes() != target:
        raise ValueError("source/staged bytes changed during extraction")
    return result


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--campaign", type=Path, required=True)
    p.add_argument("--sha256", required=True)
    p.add_argument("--reader", type=Path, required=True)
    p.add_argument("--map", required=True, help="exact internal manifest path")
    p.add_argument("--build-evidence", type=Path)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    result = prepare(a.campaign, a.sha256, a.reader, a.output, a.map, a.build_evidence)
    print(json.dumps({k: result[k] for k in ("w3nSha256", "w3xSha256", "runnerStatus", "map_standalone_native", "campaign_native")}))
