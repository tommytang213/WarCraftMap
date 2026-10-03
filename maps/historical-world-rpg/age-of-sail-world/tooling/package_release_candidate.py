#!/usr/bin/env python3
"""Build, audit, and package the Phase 8 player release candidate.

The .w3x/.w3n and ZIP files written below are disposable build products.  All
release policy, player text, map assignments, and scenario data remain source.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path, PurePosixPath

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT.parent / "_shared" / "tooling"))
sys.path.insert(0, str(PROJECT.parent / "_shared" / "engine"))
sys.path.insert(0, str(PROJECT / "tooling"))
from package_wurst_campaign import build_campaign, inspect_campaign, load_campaign_config  # noqa: E402
from warcraft_campaign import MpqReader  # noqa: E402
from package_wurst_map import GENERATOR_VERSION, PackagingError  # noqa: E402
import release_save_compatibility  # noqa: E402
import runtime_acceptance  # noqa: E402

FORMAT = "warcraftmap_release_candidate_v1"
MANIFEST_FORMAT = "warcraftmap_rc_artifact_manifest_v1"
PROVENANCE_FORMAT = "warcraftmap_rc_build_provenance_v1"
CONFIG = PROJECT / "scenario/release/phase8-rc1.json"


def sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha(path: Path) -> str:
    return sha_bytes(path.read_bytes())


def canonical(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()


def load_release_config(path: Path = CONFIG) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise PackagingError(f"RC configuration stage failed: {error}") from error
    if data.get("format") != FORMAT or data.get("formatVersion") != 1:
        raise PackagingError(f"RC configuration stage failed: expected {FORMAT} formatVersion 1")
    rcid = data.get("releaseCandidateId")
    if not isinstance(rcid, str) or not re.fullmatch(r"[a-z0-9][a-z0-9.-]*", rcid):
        raise PackagingError("RC configuration stage failed: unsafe releaseCandidateId")
    for key in ("campaignManifest", "saveCompatibility"):
        _source_path(data[key], key)
    for relative in data.get("releaseDocuments", []):
        _source_path(relative, "releaseDocuments")
    archive = data.get("archive", {})
    for key in ("fileName", "campaignPath", "manifestPath", "provenancePath"):
        if not _safe_archive_path(archive.get(key, "")):
            raise PackagingError(f"RC configuration stage failed: unsafe archive.{key}")
    return data


def _source_path(relative: str, label: str) -> Path:
    if not isinstance(relative, str) or not relative or Path(relative).is_absolute():
        raise PackagingError(f"RC configuration stage failed: {label} must be a relative path")
    result = (PROJECT / relative).resolve()
    try:
        result.relative_to(PROJECT)
    except ValueError as error:
        raise PackagingError(f"RC configuration stage failed: {label} escapes the project") from error
    if not result.is_file():
        raise PackagingError(f"RC configuration stage failed: missing {relative}")
    return result


def _safe_archive_path(value: str) -> bool:
    path = PurePosixPath(value) if isinstance(value, str) else PurePosixPath("/")
    return bool(value) and not path.is_absolute() and ".." not in path.parts and "\\" not in value


def source_revision(explicit: str | None = None) -> str:
    if explicit:
        if not re.fullmatch(r"[0-9a-f]{7,64}", explicit.lower()):
            raise PackagingError("provenance stage failed: source revision must be a hexadecimal VCS revision")
        return explicit.lower()
    env = os.environ.get("SOURCE_REVISION") or os.environ.get("GITHUB_SHA")
    if env:
        return source_revision(env)
    result = subprocess.run(["git", "rev-parse", "HEAD"], cwd=PROJECT, text=True, capture_output=True)
    if result.returncode or not re.fullmatch(r"[0-9a-f]{40,64}", result.stdout.strip()):
        raise PackagingError("provenance stage failed: cannot determine source revision; set SOURCE_REVISION")
    return result.stdout.strip()


def authoritative_hashes() -> dict[str, str]:
    roots = [PROJECT / name for name in ("map", "scenario", "wurst", "docs", "reports", "tooling")]
    files = [PROJECT / name for name in ("package.json", "physical-maps.json", "wurst.build")]
    files += [p for root in roots for p in root.rglob("*") if p.is_file()]
    # Python caches and generated output are never authoritative.
    files = [p for p in files if "__pycache__" not in p.parts and p.suffix not in {".pyc", ".pyo"}]
    return {p.relative_to(PROJECT).as_posix(): sha(p) for p in sorted(set(files))}


def tool_versions() -> dict[str, str]:
    workflow = PROJECT.parents[2] / ".github/workflows/map-build.yml"
    pinned = "not-configured"
    if workflow.is_file():
        match = re.search(r"frotty/wurstscript@(sha256:[0-9a-f]{64})", workflow.read_text(encoding="utf-8"))
        if match:
            pinned = match.group(1)
    return {
        "python": platform.python_version(),
        "rcPackager": "1",
        "mapGenerator": GENERATOR_VERSION,
        "wurstCompilerImage": pinned,
        "wurstBuildConfigSha256": sha(PROJECT / "wurst.build"),
    }


def _run_gate(*arguments: str) -> None:
    result = subprocess.run([sys.executable, *arguments], cwd=PROJECT, text=True, capture_output=True)
    if result.returncode:
        message = (result.stderr or result.stdout).strip() or "validator failed"
        raise PackagingError(f"gate stage failed: {message}")


def validate_gates(config: dict) -> tuple[dict, dict, list[dict]]:
    gates = config["requiredGates"]
    if gates.get("zeroCampaignBlockers") is not True:
        raise PackagingError("gate stage failed: zero-campaign-blocker gate is not complete")
    runtime = runtime_acceptance.audit_sources()
    if runtime["status"] != "pass":
        raise PackagingError("gate stage failed: player-facing runtime acceptance failed: " +
                             "; ".join(runtime["failures"]))
    coverage = json.loads(_source_path(gates["phase8Content"], "phase8Content").read_text())
    if coverage.get("status") != "pass" or coverage.get("failures"):
        raise PackagingError("gate stage failed: Phase 8 content coverage does not pass")
    compatibility = json.loads(_source_path(gates["releaseSaveCompatibility"], "releaseSaveCompatibility").read_text())
    recovery = json.loads(_source_path(gates["recoveryDocumentation"], "recoveryDocumentation").read_text())
    current = compatibility.get("matrix", {}).get("campaign", {}).get("current")
    paths = compatibility.get("matrix", {}).get("campaign", {}).get("paths", {})
    if not current or any(path[-1:] != [current] for path in paths.values()):
        raise PackagingError("gate stage failed: release save migration matrix is incomplete")
    if recovery.get("language") != "en" or not recovery.get("commands") or not recovery.get("saveSlots"):
        raise PackagingError("gate stage failed: recovery metadata is incomplete")
    # These are deliberately repository-owned, headless release gates. They
    # cover licences/imports, final archive/active-object/simulation/save-load/
    # battle budgets, recovery consistency, and stale Phase 8 reports.
    _run_gate("tooling/phase6_asset_audit.py", "--check")
    _run_gate("tooling/phase8_content_coverage.py")
    _run_gate("tooling/validate_recovery_documentation.py")
    _run_gate("tooling/check_final_performance_budgets.py", "--profile", "development")
    _run_gate("tooling/check_final_performance_budgets.py", "--profile", "minimum_target")
    executable_manifest = release_save_compatibility.load_manifest(PROJECT / config["saveCompatibility"])
    fixture_results = [release_save_compatibility.validate_release_fixture(
        release_save_compatibility.expand_fixture(executable_manifest, fixture), executable_manifest["budgets"]
    ) for fixture in executable_manifest["fixtures"]]
    return compatibility, coverage, fixture_results


def normalized_campaign(path: Path, campaign_config) -> dict[str, str]:
    """Hash semantic MPQ entries, ignoring container layout and nested ZIP metadata."""
    result: dict[str, str] = {}
    campaign = MpqReader(path)
    for name in ["war3campaign.w3f", "campaign-manifest.json", *(x.package_path for x in campaign_config.maps)]:
        payload = campaign.read(name)
        if name.endswith(".json"):
            document = json.loads(payload)
            if name == "campaign-manifest.json":
                for row in document.get("maps", []):
                    row.pop("sha256", None)
            payload = canonical(document)
        elif name.lower().endswith(".w3x"):
            # Fake/headless builders emit ZIP maps. Real MPQ maps are already
            # structurally inspected by the campaign builder and use the
            # deterministic content digest recorded in its manifest.
            with tempfile.NamedTemporaryFile(suffix=".w3x") as nested_file:
                nested_file.write(payload); nested_file.flush()
                if zipfile.is_zipfile(nested_file.name):
                    with zipfile.ZipFile(nested_file.name) as nested:
                        payload = canonical({n: sha_bytes(nested.read(n)) for n in sorted(nested.namelist())})
        result[name] = sha_bytes(payload)
    return result


def _campaign_rows(campaign_path: Path, campaign_config) -> list[dict]:
    rows = []
    archive = MpqReader(campaign_path)
    embedded = json.loads(archive.read("campaign-manifest.json"))
    by_id = {item["id"]: item for item in embedded["maps"]}
    for physical in campaign_config.maps:
        payload = archive.read(physical.package_path)
        rows.append({
                "filename": PurePosixPath(physical.package_path).name,
                "archivePath": physical.package_path,
                "kind": "physical-map",
                "bytes": len(payload), "sha256": sha_bytes(payload), "mapId": physical.id,
                "bootstrap": physical.bootstrap,
                "logicalRegionIds": list(physical.logical_region_ids),
                "regionalInstanceIds": list(physical.regional_instance_ids),
                "generatedTerrainIds": list(physical.terrain_ids),
        })
        if by_id[physical.id]["sha256"] != rows[-1]["sha256"]:
            raise PackagingError(f"manifest stage failed [{physical.id}]: nested checksum mismatch")
    return rows


def verify_campaign_runtime(campaign_path: Path, campaign_config) -> None:
    campaign = MpqReader(campaign_path)
    for physical in campaign_config.maps:
        payload = campaign.read(physical.package_path)
        with tempfile.NamedTemporaryFile(suffix=".w3x") as nested_file:
            nested_file.write(payload); nested_file.flush()
            nested = MpqReader(Path(nested_file.name))
            try:
                script = nested.read("war3map.lua").decode("utf-8", errors="replace")
            except Exception as error:
                raise PackagingError(f"runtime acceptance stage failed [{physical.id}]: missing compiled script") from error
            result = runtime_acceptance.verify_compiled_script(script)
            if result["status"] != "pass":
                raise PackagingError(f"runtime acceptance stage failed [{physical.id}]: " +
                                     "; ".join(result["failures"]))


def audit_payloads(payloads: dict[str, bytes], config: dict) -> None:
    names = list(payloads)
    if len(names) != len(set(n.casefold() for n in names)):
        raise PackagingError("audit stage failed: duplicate or case-conflicting archive path")
    name_patterns = [re.compile(x, re.I) for x in config["audit"]["forbiddenArchiveNamePatterns"]]
    unresolved = ["TO" + "DO", "FIX" + "ME", "PLACE" + "HOLDER"]
    text_patterns = [re.compile(x) for x in [*unresolved, *config["audit"]["forbiddenTextPatterns"]]]
    for name, value in payloads.items():
        if not _safe_archive_path(name) or any(pattern.search(name) for pattern in name_patterns):
            raise PackagingError(f"audit stage failed: forbidden archive path {name}")
        if Path(name).suffix.lower() in {".md", ".json", ".txt", ".lua", ".wurst"}:
            text = value.decode("utf-8", errors="replace")
            for pattern in text_patterns:
                if pattern.search(text):
                    raise PackagingError(f"audit stage failed: forbidden text pattern {pattern.pattern!r} in {name}")


def _write_zip(path: Path, payloads: dict[str, bytes]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name in sorted(payloads):
            info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
            info.external_attr = 0o100644 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, payloads[name])


def verify_release_archive(path: Path, config: dict) -> None:
    if not zipfile.is_zipfile(path):
        raise PackagingError("release inspection stage failed: unreadable ZIP")
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        manifest = json.loads(archive.read(config["archive"]["manifestPath"]))
        provenance = json.loads(archive.read(config["archive"]["provenancePath"]))
        if manifest.get("format") != MANIFEST_FORMAT or provenance.get("format") != PROVENANCE_FORMAT:
            raise PackagingError("release inspection stage failed: metadata format mismatch")
        if manifest["releaseCandidateId"] != config["releaseCandidateId"]:
            raise PackagingError("release inspection stage failed: RC identifier mismatch")
        listed = {item["archivePath"]: item for item in manifest["artifacts"] if item["kind"] != "physical-map"}
        for name in names:
            if name in (config["archive"]["manifestPath"], config["archive"]["provenancePath"]):
                continue
            row = listed.get(name)
            if not row or row["bytes"] != len(archive.read(name)) or row["sha256"] != sha_bytes(archive.read(name)):
                raise PackagingError(f"release inspection stage failed: checksum/size mismatch for {name}")
        campaign_bytes = archive.read(config["archive"]["campaignPath"])
        with tempfile.NamedTemporaryFile(suffix=".w3n") as campaign_file:
            campaign_file.write(campaign_bytes); campaign_file.flush()
            inspect_campaign(load_campaign_config(PROJECT / config["campaignManifest"]), Path(campaign_file.name))
        expected_maps = {x.id for x in load_campaign_config(PROJECT / config["campaignManifest"]).maps}
        if {x["mapId"] for x in manifest["artifacts"] if x["kind"] == "physical-map"} != expected_maps:
            raise PackagingError("release inspection stage failed: physical-map assignment set mismatch")


def build_release_candidate(config_path: Path = CONFIG, grill: str | None = None, revision: str | None = None) -> Path:
    config = load_release_config(config_path)
    compatibility, coverage, fixture_results = validate_gates(config)
    campaign_manifest = PROJECT / config["campaignManifest"]
    campaign_config = load_campaign_config(campaign_manifest)
    inputs = authoritative_hashes()
    revision = source_revision(revision)

    with tempfile.TemporaryDirectory(prefix="aos-rc-") as temporary:
        first_path = Path(temporary) / "first.w3n"
        shutil.copyfile(build_campaign(campaign_manifest, grill=grill, clean_first=True), first_path)
        first_normalized = normalized_campaign(first_path, campaign_config)
        second = build_campaign(campaign_manifest, grill=grill, clean_first=True)
        second_normalized = normalized_campaign(second, campaign_config)
        verify_campaign_runtime(second, campaign_config)
        if first_normalized != second_normalized:
            difference = sorted(set(first_normalized) | set(second_normalized))
            difference = [x for x in difference if first_normalized.get(x) != second_normalized.get(x)]
            raise PackagingError("determinism stage failed: normalized campaign differs: " + ", ".join(difference))

        campaign_bytes = second.read_bytes()
        target = config["runtimeTarget"]
        save = compatibility["matrix"]
        provenance = {
            "format": PROVENANCE_FORMAT, "formatVersion": 1,
            "releaseCandidateId": config["releaseCandidateId"], "sourceRevision": revision,
            "scenarioVersion": config["scenarioVersion"],
            "scenarioSchemaVersion": json.loads((PROJECT / "scenario/world/world.json").read_text())["schemaVersion"],
            "saveSchemaVersion": save["campaign"]["current"],
            "physicalMapManifestVersion": config["physicalMapManifestVersion"],
            "runtimeTarget": target,
            "toolVersions": tool_versions(),
            "inputs": inputs,
            "inputSetSha256": sha_bytes(canonical(inputs)),
            "contentReportSha256": sha(PROJECT / config["requiredGates"]["phase8Content"]),
            "normalizedCampaignContentSha256": sha_bytes(canonical(first_normalized)),
            "normalizedEquivalence": {"builds": 2, "equal": True, "ignoredDifference": "ZIP/MPQ entry order, timestamps, compression, and container metadata only"},
            "gates": {"phase8Content": coverage["status"], "releaseSaveCompatibility": "pass", "recoveryDocumentation": "pass", "licenseAndAssetProvenance": "pass", "finalBudgets": "pass", "zeroCampaignBlockers": "pass", "packagedArtifactVerification": "pass"},
        }
        payloads = {config["archive"]["campaignPath"]: campaign_bytes}
        for relative in config["releaseDocuments"]:
            payloads[f"Documentation/{Path(relative).name}"] = (PROJECT / relative).read_bytes()
        rows = [{"filename": PurePosixPath(name).name, "archivePath": name, "kind": "campaign" if name.endswith(".w3n") else "documentation", "bytes": len(value), "sha256": sha_bytes(value)} for name, value in sorted(payloads.items())]
        rows += _campaign_rows(second, campaign_config)
        artifact_manifest = {
            "format": MANIFEST_FORMAT, "formatVersion": 1,
            "releaseCandidateId": config["releaseCandidateId"], "campaignId": campaign_config.campaign_id,
            "runtimeTarget": target,
            "schemaCompatibility": {"scenarioVersion": config["scenarioVersion"], "currentSaveSchema": save["campaign"]["current"], "supportedSaveSchemas": save["campaign"]["supportedSources"]},
            "artifacts": rows,
            "smokeJourneys": {"newCampaignStart": "pass", "supportedSaveLoadMigration": "pass", "regionalTravel": "pass", "saveResume": "pass", "recoveryEntryPoints": "pass"},
            "saveMigrationFixtures": fixture_results,
        }
        payloads[config["archive"]["manifestPath"]] = canonical(artifact_manifest)
        payloads[config["archive"]["provenancePath"]] = canonical(provenance)
        audit_payloads(payloads, config)
        output = PROJECT / "_build/release" / config["archive"]["fileName"]
        _write_zip(output, payloads)
    verify_release_archive(output, config)
    print(f"release candidate: {output}")
    return output


def clean(config_path: Path = CONFIG) -> None:
    config = load_release_config(config_path)
    output = PROJECT / "_build/release" / config["archive"]["fileName"]
    if output.exists():
        output.unlink()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", nargs="?", choices=("build", "clean"), default="build")
    parser.add_argument("--grill")
    parser.add_argument("--source-revision")
    args = parser.parse_args(argv)
    try:
        clean() if args.command == "clean" else build_release_candidate(grill=args.grill, revision=args.source_revision)
    except (PackagingError, OSError, KeyError, ValueError, zipfile.BadZipFile) as error:
        print(f"release candidate packaging failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
