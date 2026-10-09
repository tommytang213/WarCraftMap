#!/usr/bin/env python3
"""Stage an inspected diagnostic campaign; never grant release/native approval."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
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

FAILING_SHA256 = "4f2f9cf8ca56f81aaeca524f257ae15e273c2366e52adfaa1eafdf5b996ff9ad"
PREVIOUS_FAILING_SHA256 = "d6651b77a48a3c7c1b4916a204676b506a380f77a4496fbadd417697e8d87abc"


def build_id(identity: dict, digest: str, run_id=None, attempt=None) -> str:
    """Reproducible identity for Actions and dirty/local source trees."""
    revision, tree = identity["sourceRevision"], identity["sourceTreeSha256"]
    for value, length in ((revision, 40), (tree, 64), (digest, 64)):
        if not re.fullmatch(r"[0-9a-f]{%d}" % length, value):
            raise ValueError("invalid diagnostic source/content identity")
    if (run_id is None) != (attempt is None):
        raise ValueError("Actions identity requires both run ID and attempt")
    for value in (run_id, attempt):
        if value is not None and not re.fullmatch(r"[1-9][0-9]{0,19}", str(value)):
            raise ValueError("invalid Actions run ID or attempt")
    origin = "local" if run_id is None else f"r{run_id}-a{attempt}"
    return f"smoke-{origin}-g{revision[:12]}-t{tree[:12]}-h{digest[:12]}"


def publish(campaign: Path, output: Path, result: dict) -> dict:
    """Copy exact bytes only. Never reserialize W3F or any nested W3X."""
    if output.exists() and any(output.iterdir()):
        raise ValueError("diagnostic output must be empty; do not mix installed versions")
    digest = result["campaignSha256"]
    if result["diagnosticId"] != build_id(result["sourceIdentity"], digest,
                                         result["buildRun"]["id"], result["buildRun"]["attempt"]):
        raise ValueError("diagnostic identity mismatch before staging")
    if hashlib.sha256(campaign.read_bytes()).hexdigest() != digest:
        raise ValueError("campaign changed after inspection")
    relative = f"Campaigns/AgeOfSailWorldCampaign-{result['diagnosticId']}.w3n"
    result["installedCampaignPath"] = relative
    output.mkdir(parents=True, exist_ok=True)
    target = output / relative
    target.parent.mkdir(exist_ok=True)
    shutil.copyfile(campaign, target)
    if hashlib.sha256(target.read_bytes()).hexdigest() != digest:
        raise ValueError("staged campaign hash mismatch")
    (output / "SHA256SUMS.txt").write_text(f"{digest}  {relative}\n")
    (output / "SOURCE_REVISION.txt").write_text(result["sourceIdentity"]["sourceRevision"] + "\n")
    (output / "launch-smoke.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    (output / "LAUNCH-SMOKE-ONLY.txt").write_text(
        f"DIAGNOSTIC {result['diagnosticId']} - NOT A RELEASE CANDIDATE\n"
        f"Installed file: {relative}\n"
        f"Source revision: {result['sourceIdentity']['sourceRevision']}\n"
        f"Source tree SHA-256: {result['sourceIdentity']['sourceTreeSha256']}\n"
        f"Campaign SHA-256: {digest}\n"
        "Native campaign launch remains FAILED; these bytes have NOT RUN in Warcraft.\n"
        "Smoke #3 failed on 3.0.0 build 24268; smoke #2 failed on 3.0.1 build 24342.\n"
        "Diagnostic filename identity is not a crash repair. No player retest is requested.\n"
        "Only test after a reviewed, materially changed candidate and a specific hypothesis.\n\n"
        "For that future single test, close Warcraft, keep only ONE diagnostic W3N in\n"
        "Documents/Warcraft III/Campaigns, and copy the versioned filename shown above.\n"
        "The menu/editor title is still Age of Sail: The World; the filename does not\n"
        "change that label. Menu-title editing is deferred to keep every archive byte intact.\n"
        "Verify the installed file with Get-FileHash -Algorithm SHA256. Then open\n"
        "Single Player > Custom Campaigns > Age of Sail: The World > Begin the Campaign.\n"
        "Record the exact client build and whether origin selection opens. A process or\n"
        "a War3Log Played entry is not gameplay success. Keep the hash with the result.\n"
        "Do not save in World Editor or upload private crash data. All release gates remain.\n")
    return result


def verify_staged(output: Path, revision: str) -> dict:
    """Post-copy/upload-input gate, using the actual installed filename."""
    result = json.loads((output / "launch-smoke.json").read_text())
    if result["sourceIdentity"]["sourceRevision"] != revision:
        raise ValueError("staged source revision mismatch")
    ident = result["diagnosticId"]
    if ident != build_id(result["sourceIdentity"], result["campaignSha256"],
                         result["buildRun"]["id"], result["buildRun"]["attempt"]):
        raise ValueError("staged build identity mismatch")
    relative = f"Campaigns/AgeOfSailWorldCampaign-{ident}.w3n"
    if result["installedCampaignPath"] != relative:
        raise ValueError("staged installed filename mismatch")
    if sorted(p.relative_to(output).as_posix() for p in (output / "Campaigns").iterdir()) != [relative]:
        raise ValueError("unexpected installed campaign files")
    target = output / relative
    if target.is_symlink() or hashlib.sha256(target.read_bytes()).hexdigest() != result["campaignSha256"]:
        raise ValueError("staged campaign hash mismatch")
    if (output / "SHA256SUMS.txt").read_text() != f"{result['campaignSha256']}  {relative}\n":
        raise ValueError("staged checksum filename/hash mismatch")
    if (output / "SOURCE_REVISION.txt").read_text() != revision + "\n":
        raise ValueError("staged revision file mismatch")
    return result


def stage(campaign: Path, execution: Path, output: Path, revision: str, *, run_id=None, attempt=None) -> dict:
    digest = hashlib.sha256(campaign.read_bytes()).hexdigest()
    if digest in (FAILING_SHA256, PREVIOUS_FAILING_SHA256):
        raise ValueError("diagnostic must not repeat the failing campaign bytes")
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
    result = {
        "diagnosticId": build_id(identity, digest, run_id, attempt), "sourceIdentity": identity,
        "buildRun": {"id": run_id, "attempt": attempt},
        "campaignSha256": digest, "reproductionSha256": FAILING_SHA256,
        "changes": [], "diagnosis": "diagnosis_unconfirmed", "playerTestRequested": False,
        "purpose": "Versioned diagnostic identity and static evidence; no verified native repair.",
        "archiveTransformation": "none; byte-identical copy including W3F and every nested W3X",
        "menuTitle": "Age of Sail: The World", "menuTitlePatched": False,
        "staticValidation": {"status": "pass", "maps": entries},
        "wurstInterpreter": {"status": "pass", "tests": report["succeeded"],
                             "compiler": report["compiler"]},
        "nativeClient": {"version": "3.0.0", "build": 24268,
                         "reproduction": "failed", "revisedArtifact": "not_run",
                         "previousReproduction": {"version": "3.0.1", "build": 24342, "status": "failed"}},
        "map_standalone_native": "not_run", "campaign_native": "not_run",
        "real_client_launch": "failed",
        "releaseStatus": "blocked_pending_real_forsaken_kingdom_launch_smoke",
        "remainingDiscriminator": "See reports/issue-438: qualify a local WGC runner with controls before a single exact-selector standalone comparison. Full retail campaign acceptance remains mandatory.",
        "releaseCandidate": False,
    }
    publish(campaign, output, result)
    for name in ("results.json", "execution.log"):
        shutil.copyfile(execution / name, output / ("wurst-" + name))
    verify_staged(output, revision)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--campaign", type=Path, default=PROJECT / "_build/release/AgeOfSailWorldCampaign.w3n")
    parser.add_argument("--execution", type=Path, default=PROJECT / "_build/wurst-tests")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--run-id", default=os.environ.get("GITHUB_RUN_ID"))
    parser.add_argument("--run-attempt", default=os.environ.get("GITHUB_RUN_ATTEMPT"))
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    result = (verify_staged(args.output, args.source_revision) if args.verify_only else
              stage(args.campaign, args.execution, args.output, args.source_revision,
                    run_id=args.run_id, attempt=args.run_attempt))
    print(f"{result['installedCampaignPath']}: {result['campaignSha256']}; native launch FAILED; candidate NOT RUN")
