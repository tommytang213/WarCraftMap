#!/usr/bin/env python3
"""Stage an inspected diagnostic campaign; never grant release/native approval."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT.parent / "_shared/tooling"))
from integration_evidence import source_identity, verify_execution_coverage
from package_wurst_campaign import load_campaign_config, inspect_campaign, _inspect_physical_map
from package_wurst_map import _inspect, load_config
from warcraft_campaign import MpqReader
from warcraft_map_info import parse_w3i

DIAGNOSTIC = "LAUNCH-425-LIGHTING-1"
FAILING_SHA256 = "d6651b77a48a3c7c1b4916a204676b506a380f77a4496fbadd417697e8d87abc"


def stage(campaign: Path, execution: Path, output: Path, revision: str) -> dict:
    identity = source_identity(PROJECT, revision)
    config = load_campaign_config(PROJECT / "physical-maps.json")
    base = load_config(config.map_config_path)
    report = json.loads((execution / "results.json").read_text())
    log = (execution / "execution.log").read_bytes()
    verify_execution_coverage(report, log, PROJECT, revision)
    inspect_campaign(config, campaign)
    reader = MpqReader(campaign)
    entries = []
    with tempfile.TemporaryDirectory(prefix="launch-smoke-", dir=campaign.parent) as directory:
        for physical in config.maps:
            payload = reader.read(physical.package_path)
            archive = Path(directory) / (physical.id + ".w3x")
            archive.write_bytes(payload)
            # Re-read the exact nested bytes, including the compiled startup.
            _inspect(base, archive, archive.parent, physical.terrain_ids)
            _inspect_physical_map(physical, archive)
            nested = MpqReader(archive)
            if json.loads(nested.read("runtime/build-identity.json")) != identity:
                raise ValueError(f"stale diagnostic source identity: {physical.id}")
            info = parse_w3i(nested.read("war3map.w3i"))
            entries.append({"id": physical.id, "path": physical.package_path,
                            "sha256": hashlib.sha256(payload).hexdigest(),
                            "luaSha256": hashlib.sha256(nested.read("war3map.lua")).hexdigest(),
                            "w3iFormat": info["format"], "producerVersion": info["gameVersion"],
                            "startupContract": "pass"})
    digest = hashlib.sha256(campaign.read_bytes()).hexdigest()
    if digest == FAILING_SHA256:
        raise ValueError("diagnostic must not repeat the failing campaign bytes")
    result = {
        "diagnosticId": DIAGNOSTIC, "sourceIdentity": identity,
        "campaignSha256": digest, "reproductionSha256": FAILING_SHA256,
        "changes": ["Initialize stock terrain and unit day/night models before InitBlizzard in source main."],
        "purpose": "Test the missing lighting initialization hypothesis; its relationship to the native null read is unconfirmed.",
        "staticValidation": {"status": "pass", "maps": entries},
        "wurstInterpreter": {"status": "pass", "tests": report["succeeded"],
                             "compiler": report["compiler"]},
        "nativeClient": {"version": "3.0.1", "build": 24342,
                         "reproduction": "failed", "revisedArtifact": "not_revalidated"},
        "releaseStatus": "blocked_pending_real_forsaken_kingdom_launch_smoke",
        "remainingDiscriminator": "Launch these revised bytes on Warcraft III 3.0.1 build 24342 and establish whether origin selection opens. If the same crash persists, correlate its exception offset and original context before changing another startup input.",
        "releaseCandidate": False,
    }
    output.mkdir(parents=True, exist_ok=True)
    target = output / "Campaigns/AgeOfSailWorldCampaign.w3n"
    target.parent.mkdir(exist_ok=True)
    shutil.copyfile(campaign, target)
    (output / "SHA256SUMS.txt").write_text(f"{digest}  Campaigns/AgeOfSailWorldCampaign.w3n\n")
    (output / "SOURCE_REVISION.txt").write_text(revision + "\n")
    (output / "launch-smoke.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    (output / "LAUNCH-SMOKE-ONLY.txt").write_text(
        f"DIAGNOSTIC {DIAGNOSTIC} - NOT A RELEASE CANDIDATE\n"
        f"Source revision: {revision}\nSource tree SHA-256: {identity['sourceTreeSha256']}\n"
        f"Campaign SHA-256: {digest}\n"
        "Observed failing client: Warcraft III 3.0.1 build 24342.\n"
        "Changed: initialize terrain/unit lighting before InitBlizzard.\n"
        "Native crash causality remains unconfirmed; CI does not execute Warcraft.\n"
        "Real-client status: original FAILED; revised artifact NOT REVALIDATED.\n\n"
        "For the single final launch comparison, close Warcraft III and replace the installed\n"
        "Campaigns/AgeOfSailWorldCampaign.w3n with these bytes. Open Single Player >\n"
        "Custom Campaigns > Age of Sail: The World > Begin the Campaign.\n"
        "The acceptance boundary is origin selection opening on build 24342.\n"
        "Keep this identity and SHA256SUMS.txt with the result; do not upload raw crash data publicly.\n"
        "Official release gates and the outstanding real-client acceptance remain in force.\n")
    for name in ("results.json", "execution.log"):
        shutil.copyfile(execution / name, output / ("wurst-" + name))
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--campaign", type=Path, default=PROJECT / "_build/release/AgeOfSailWorldCampaign.w3n")
    parser.add_argument("--execution", type=Path, default=PROJECT / "_build/wurst-tests")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source-revision", required=True)
    args = parser.parse_args()
    result = stage(args.campaign, args.execution, args.output, args.source_revision)
    print(f"{result['diagnosticId']}: {result['campaignSha256']}; native launch NOT REVALIDATED")
