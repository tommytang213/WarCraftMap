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
FAILED_TRANSITION_ARTIFACTS = {
    "pr530_full17": "ca03705c83fa714e2799f3be42f109d993d96c39334885b7974d6417f6ae31da",
    "pr536_hidden_chapters": "9309320cdb4ef9c978a7b338d2a4230b6a6b5fb407f43ef8fe0dd379d5f0c58e",
    "pr536_selector_as_region": "31ae2c32d2a2201e3b029ec552c08f9f411c8ae830c3a20e7e81cbd90f9b33e6",
}
LAUNCH_PROFILE = "launch"
HANDOFF_PROFILE = "root-basename-handoff"


def reject_failed_digest(digest: str) -> None:
    if digest in {FAILING_SHA256, PREVIOUS_FAILING_SHA256, *FAILED_TRANSITION_ARTIFACTS.values()}:
        raise ValueError("diagnostic must not repeat the failing campaign bytes")


def inspect_root_basename_handoff(config, bootstrap_lua: bytes) -> dict:
    """Cross-check actual compiled selector literals; never claim native execution.

    inspect_campaign has already checked the same configured paths against the
    archived W3F tables, MPQ member set and nested-map checksums. The existing
    compiled-bootstrap inspector checks the ChangeLevel call and entry points.
    Literal presence below is static evidence, not control-flow reachability.
    """
    from runtime_acceptance import verify_compiled_bootstrap
    from warcraft_lua_startup import _tokens

    if any("/" in item.package_path or "\\" in item.package_path for item in config.maps):
        raise ValueError("handoff diagnostic requires root-basename campaign paths")
    destination = next((item for item in config.maps if item.id == "europe_central_east"), None)
    if destination is None or destination.bootstrap:
        raise ValueError("handoff diagnostic has no Austria destination map")
    compiled = verify_compiled_bootstrap(bootstrap_lua)
    if compiled["status"] != "pass":
        raise ValueError("handoff bootstrap inspection failed: " + "; ".join(compiled["failures"]))
    tokens = _tokens(bootstrap_lua.decode("utf-8"))
    literals = {token[1:-1] for token in tokens
                if len(token) >= 2 and token[0] in "\"'" and token[-1] == token[0]}
    if not {"austria", destination.id, destination.package_path}.issubset(literals):
        raise ValueError("compiled selector is missing the Austria root destination literals")
    if any(value in literals for item in config.maps
           for value in ("Maps/" + item.package_path, "Maps\\\\" + item.package_path)):
        raise ValueError("compiled selector retains a prefixed campaign destination")
    return {"status": "pass", "evidenceLevel": "compiled_text_static_heuristic",
            "scope": "configured root paths, inspected W3F/MPQ, bootstrap native call and destination literals; no reachability or native-execution proof",
            "command": "/origin choose austria", "destinationMapId": destination.id,
            "destinationPackagePath": destination.package_path,
            "requiredMilestone": "destination terrain AND a player-controlled unit"}


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
    reject_failed_digest(digest)
    profile = result.get("diagnosticProfile", LAUNCH_PROFILE)
    if profile not in (LAUNCH_PROFILE, HANDOFF_PROFILE):
        raise ValueError("unknown diagnostic profile")
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
    observation = (
        "At the origin selector, enter exactly /origin choose austria. If a Victory\n"
        "screen appears, click Continue once. Success requires visible destination\n"
        "terrain AND a player-controlled unit that responds to a movement order.\n"
        "Origin selection, Victory/Continue, or an Opening map/Played log entry alone\n"
        "does not establish successful regional gameplay. If still black after two\n"
        "minutes, record the failure and whether you had to force-quit. Do not repeat\n"
        "the unchanged candidate. Keep the installed hash and exact client build.\n"
        "This candidate tests consistent root-basename paths; native causality is\n"
        "unconfirmed. The hidden-chapter and duplicate-selector controls already\n"
        "failed. The duplicate-selector control shared internal map identity, so\n"
        "its failure did not conclusively exclude regional initialization.\n"
        if profile == HANDOFF_PROFILE else
        "Record the exact client build and whether origin selection opens. A process or\n"
        "a War3Log Played entry is not gameplay success. Keep the hash with the result.\n"
    )
    (output / "LAUNCH-SMOKE-ONLY.txt").write_text(
        f"DIAGNOSTIC {result['diagnosticId']} - NOT A RELEASE CANDIDATE\n"
        f"Installed file: {relative}\n"
        f"Source revision: {result['sourceIdentity']['sourceRevision']}\n"
        f"Source tree SHA-256: {result['sourceIdentity']['sourceTreeSha256']}\n"
        f"Campaign SHA-256: {digest}\n"
        "Native campaign acceptance remains FAILED; these bytes have NOT RUN in Warcraft.\n"
        "Original startup crashes: smoke #3 on 3.0.0 build 24268; smoke #2 on 3.0.1 build 24342.\n"
        "Later diagnostics opened the selector but stayed black after choosing Austria.\n"
        "Diagnostic filename identity is not a crash repair. No player retest is requested.\n"
        "Only test after a reviewed, materially changed candidate and a specific hypothesis.\n\n"
        "For that future single test, close Warcraft, keep only ONE diagnostic W3N in\n"
        "Documents/Warcraft III/Campaigns, and copy the versioned filename shown above.\n"
        "The menu/editor title is still Age of Sail: The World; the filename does not\n"
        "change that label. Menu-title editing is deferred to keep every archive byte intact.\n"
        "Verify the installed file with Get-FileHash -Algorithm SHA256. Then open\n"
        "Single Player > Custom Campaigns > Age of Sail: The World > Begin the Campaign.\n"
        + observation +
        "Do not save in World Editor or upload private crash data. All release gates remain.\n")
    return result


def verify_staged(output: Path, revision: str) -> dict:
    """Post-copy/upload-input gate, using the actual installed filename."""
    result = json.loads((output / "launch-smoke.json").read_text())
    reject_failed_digest(result["campaignSha256"])
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


def stage(campaign: Path, execution: Path, output: Path, revision: str, *, run_id=None, attempt=None,
          profile=LAUNCH_PROFILE) -> dict:
    if profile not in (LAUNCH_PROFILE, HANDOFF_PROFILE):
        raise ValueError("unknown diagnostic profile")
    digest = hashlib.sha256(campaign.read_bytes()).hexdigest()
    reject_failed_digest(digest)
    identity = source_identity(PROJECT, revision)
    config = load_campaign_config(PROJECT / "physical-maps.json")
    base = load_config(config.map_config_path)
    report = json.loads((execution / "results.json").read_text())
    log = (execution / "execution.log").read_bytes()
    verify_execution_coverage(report, log, PROJECT, revision)
    inspect_campaign(config, campaign)
    reader = MpqReader(campaign)
    entries = []
    bootstrap_lua = b""
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
            lua = nested.read("war3map.lua")
            if physical.bootstrap:
                bootstrap_lua = lua
            entries.append({"id": physical.id, "path": physical.package_path,
                            "sha256": hashlib.sha256(payload).hexdigest(),
                            "luaSha256": hashlib.sha256(lua).hexdigest(),
                            "w3iFormat": info["format"], "producerVersion": info["gameVersion"],
                            "startupContract": "pass"})
    result = {
        "diagnosticId": build_id(identity, digest, run_id, attempt), "sourceIdentity": identity,
        "buildRun": {"id": run_id, "attempt": attempt},
        "diagnosticProfile": profile,
        "campaignSha256": digest, "reproductionSha256": FAILING_SHA256,
        "failedTransitionArtifacts": [{"id": name, "sha256": value, "destinationGameplay": "failed"}
                                      for name, value in FAILED_TRANSITION_ARTIFACTS.items()],
        "latestTransitionObservation": {"selectorLaunch": "pass", "destinationOpenAttempt": "observed",
            "postHandoffDisplay": "black_>120s", "processExit": "owner_force_quit",
            "destinationLuaInitialized": "unknown", "duplicateSelectorIdentityCaveat": True},
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
        "remainingDiscriminator": "A reviewed, materially changed candidate and one targeted manual retail check; full native campaign acceptance remains mandatory.",
        "releaseCandidate": False,
    }
    if profile == HANDOFF_PROFILE:
        transition = inspect_root_basename_handoff(config, bootstrap_lua)
        result["staticValidation"]["transitionPath"] = transition
        result["changes"] = ["root-basename map destinations consistent across authored paths, W3F and MPQ; hidden regional chapters retained"]
        result["purpose"] = "Test the root-basename path hypothesis for the failed selector-to-Austria transition; native cause is unconfirmed."
        result["remainingDiscriminator"] = "After review, one manual /origin choose austria transition must load destination terrain AND a player-controlled unit; Victory/Continue alone is not success."
        result["origin_to_region_native"] = "not_run"
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
    parser.add_argument("--profile", choices=(LAUNCH_PROFILE, HANDOFF_PROFILE), default=LAUNCH_PROFILE)
    args = parser.parse_args()
    result = (verify_staged(args.output, args.source_revision) if args.verify_only else
              stage(args.campaign, args.execution, args.output, args.source_revision,
                    run_id=args.run_id, attempt=args.run_attempt, profile=args.profile))
    print(f"{result['installedCampaignPath']}: {result['campaignSha256']}; native launch FAILED; candidate NOT RUN")
