#!/usr/bin/env python3
"""Build, audit, and package the current player release candidate.

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
import struct
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
from wurst_execution import WurstExecutionError, verify_evidence  # noqa: E402
from integration_evidence import source_identity  # noqa: E402
import release_save_compatibility  # noqa: E402
import runtime_acceptance  # noqa: E402
import requirement_traceability_audit as traceability  # noqa: E402

FORMAT = "warcraftmap_release_candidate_v1"
MANIFEST_FORMAT = "warcraftmap_rc_artifact_manifest_v1"
PROVENANCE_FORMAT = "warcraftmap_rc_build_provenance_v1"
CONFIG = PROJECT / "scenario/release/phase9-rc1.json"
PUBLICATION_BLOCKED_EXIT = 3


class CandidatePublicationBlocked(PackagingError):
    """A validated final build has reported traceability gaps; no ZIP is published."""


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
    if not isinstance(data, dict) or data.get("format") != FORMAT or data.get("formatVersion") != 1:
        raise PackagingError(f"RC configuration stage failed: expected {FORMAT} formatVersion 1")
    for key in ("requiredGates", "archive", "runtimeTarget", "audit"):
        if not isinstance(data.get(key), dict):
            raise PackagingError(f"RC configuration stage failed: {key} must be a JSON object")
    rcid = data.get("releaseCandidateId")
    if not isinstance(rcid, str) or not re.fullmatch(r"[a-z0-9][a-z0-9.-]*", rcid):
        raise PackagingError("RC configuration stage failed: unsafe releaseCandidateId")
    for key in ("campaignManifest", "saveCompatibility"):
        _source_path(data.get(key), key)
    documents = data.get("releaseDocuments")
    if not isinstance(documents, list):
        raise PackagingError("RC configuration stage failed: releaseDocuments must be a list")
    for relative in documents:
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
        if not re.fullmatch(r"[0-9a-f]{40}", explicit.lower()):
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
    roots = [PROJECT / name for name in ("map", "scenario", "wurst", "wurst-bootstrap", "docs", "reports", "tooling")]
    files = [PROJECT / name for name in ("package.json", "physical-maps.json", "wurst.build", "wurst_run.args")]
    files += [p for root in roots for p in root.rglob("*") if p.is_file()]
    # Python caches and generated output are never authoritative.
    files = [p for p in files if "__pycache__" not in p.parts and p.suffix not in {".pyc", ".pyo"}]
    result = {p.relative_to(PROJECT).as_posix(): sha(p) for p in sorted(set(files))}
    for root in (PROJECT.parent / "_shared/engine", PROJECT.parent / "_shared/tooling"):
        for path in sorted(root.rglob("*.py")):
            result["../" + path.relative_to(PROJECT.parent).as_posix()] = sha(path)
    return result


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


def validate_gates(config: dict) -> tuple[dict, dict, dict, list[dict]]:
    gates = config["requiredGates"]
    if gates.get("zeroCampaignBlockers") is not True:
        raise PackagingError("gate stage failed: zero-campaign-blocker gate is not complete")
    runtime = runtime_acceptance.audit_sources()
    if runtime["evidenceLevels"]["sourceStatic"]["status"] != "pass":
        raise PackagingError("gate stage failed: player-facing runtime acceptance failed: " +
                             "; ".join(runtime["failures"]))
    coverage = json.loads(_source_path(gates["phase8Content"], "phase8Content").read_text())
    if coverage.get("status") != "pass" or coverage.get("failures"):
        raise PackagingError("gate stage failed: Phase 8 content coverage does not pass")
    runtime_report = json.loads(_source_path(gates["runtimeAcceptance"], "runtimeAcceptance").read_text())
    if runtime_report != runtime:
        raise PackagingError("gate stage failed: runtime-acceptance report is stale")
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
    # The integration/blocker gate runs after building, with the interpreter
    # transcript and the exact campaign. A checked-in source-only report cannot
    # authorize publication, even when its static checks all pass.
    executable_manifest = release_save_compatibility.load_manifest(PROJECT / config["saveCompatibility"])
    fixture_results = [release_save_compatibility.validate_release_fixture(
        release_save_compatibility.expand_fixture(executable_manifest, fixture), executable_manifest["budgets"]
    ) for fixture in executable_manifest["fixtures"]]
    return compatibility, coverage, runtime_report, fixture_results


def normalized_map(path: Path) -> dict[str, str]:
    """Hash decoded file contents, not ZIP/MPQ container representation."""
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as archive:
            return {name: sha_bytes(archive.read(name)) for name in sorted(archive.namelist())}
    try:
        archive = MpqReader(path)
        members = archive.members()
        members.pop("(listfile)")  # Enumeration/order is represented by the keys.
        attributes = members.pop("(attributes)", None)
        if attributes is not None:
            # StormLib attributes v100 contains derived CRC/MD5 and file times.
            # Hash every actual member ourselves; ignore only these container
            # attributes, never patch flags or an unrecognized metadata layout.
            version, flags = struct.unpack_from("<II", attributes)
            row_size = (4 if flags & 1 else 0) + (8 if flags & 2 else 0) + (16 if flags & 4 else 0)
            sizes = {8 + count * row_size for count in (len(archive.blocks), len(archive.blocks) - 1)}
            if version != 100 or flags & ~7 or len(attributes) not in sizes:
                raise ValueError("unsupported MPQ attributes layout")
        return {name: sha_bytes(value) for name, value in sorted(members.items())}
    except (KeyError, ValueError, struct.error) as error:
        raise PackagingError(f"determinism stage failed: cannot enumerate map content: {error}") from error


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
            with tempfile.NamedTemporaryFile(suffix=".w3x") as nested_file:
                nested_file.write(payload); nested_file.flush()
                payload = canonical(normalized_map(Path(nested_file.name)))
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


def verify_campaign_runtime(campaign_path: Path, campaign_config, *, revision=None, source_tree_sha256=None) -> dict:
    # Inspect the campaign browser metadata and nested checksums as well as
    # its maps. Runtime acceptance can invoke this outside the ZIP packager.
    if (not isinstance(revision, str) or not re.fullmatch(r"[0-9a-f]{40}", revision) or
            not isinstance(source_tree_sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", source_tree_sha256)):
        raise PackagingError("artifact verification requires a full source revision and source-content digest")
    before = sha(campaign_path)
    inspect_campaign(campaign_config, campaign_path)
    campaign = MpqReader(campaign_path)
    inspected = []
    configured = {item.id: item for item in campaign_config.maps}
    package_by_id = {item.id: item.package_path for item in campaign_config.maps}
    all_origins = None
    boundary_ids = set()
    for physical in campaign_config.maps:
        payload = campaign.read(physical.package_path)
        with tempfile.NamedTemporaryFile(suffix=".w3x") as nested_file:
            nested_file.write(payload); nested_file.flush()
            try:
                result = runtime_acceptance.inspect_built_map(
                    Path(nested_file.name), physical.id, physical.bootstrap)
            except Exception as error:
                raise PackagingError(f"runtime acceptance stage failed [{physical.id}]: cannot inspect built map: {error}") from error
            if result["status"] != "pass":
                raise PackagingError(f"runtime acceptance stage failed [{physical.id}]: " +
                                     "; ".join(result["failures"]))
            inspected.append(result)
            result["artifactSha256"] = sha_bytes(payload)
            result["sourceRevision"] = revision
            identity = json.loads(runtime_acceptance._archive_read(Path(nested_file.name), "runtime/build-identity.json"))
            if identity != {"sourceRevision": revision, "sourceTreeSha256": source_tree_sha256}:
                raise PackagingError(f"artifact source identity mismatch [{physical.id}]")
            result["sourceTreeSha256"] = source_tree_sha256
            runtime = json.loads(runtime_acceptance._archive_read(Path(nested_file.name), "runtime/scenario-runtime.json"))
            physical_manifest = json.loads(runtime_acceptance._archive_read(Path(nested_file.name), "runtime/physical-map.json"))
            physical_runtime = runtime.get("physicalMap", {})
            if (physical_runtime.get("id") != physical.id or
                    physical_runtime.get("packagePath") != physical.package_path or
                    physical_runtime.get("logicalRegionIds") != list(physical.logical_region_ids) or
                    physical_runtime.get("regionalInstanceIds") != list(physical.regional_instance_ids)):
                raise PackagingError(f"runtime acceptance stage failed [{physical.id}]: packaged assignment metadata differs from physical-maps.json")
            origins = runtime.get("newCampaignOrigins")
            if not isinstance(origins, list) or not origins:
                raise PackagingError(f"runtime acceptance stage failed [{physical.id}]: origin selection is absent")
            if all_origins is None:
                all_origins = origins
            elif origins != all_origins:
                raise PackagingError(f"runtime acceptance stage failed [{physical.id}]: origin selection differs across maps")
            for origin in origins:
                start = origin.get("startingLocation", {})
                if start.get("physicalMapId") not in configured or not start.get("regionalInstanceId") or not start.get("settlementId"):
                    raise PackagingError(f"runtime acceptance stage failed [{physical.id}]: invalid origin destination")
            for boundary in runtime.get("physicalBoundaries", []):
                if boundary.get("sourceMapId") != physical.id:
                    raise PackagingError(f"runtime acceptance stage failed [{physical.id}]: transition has the wrong source map")
                destination = boundary.get("destinationMapId")
                if destination not in configured or boundary.get("destinationPackagePath") != package_by_id[destination]:
                    raise PackagingError(f"runtime acceptance stage failed [{physical.id}]: transition destination is invalid")
                transform = boundary.get("arrivalTransform", {})
                if set(transform) != {"reverse", "scale", "offset"}:
                    raise PackagingError(f"runtime acceptance stage failed [{physical.id}]: transition arrival transform is incomplete")
                boundary_ids.add(boundary.get("id"))
            expected_settlements = {row["id"] for row in runtime.get("settlementDefinitions", [])}
            represented = {row["id"] for row in physical_manifest.get("objects", {}).get("settlements", [])}
            if not physical.bootstrap and (expected_settlements != represented or physical_manifest.get("objects", {}).get("spawnCount") != 1):
                raise PackagingError(f"runtime acceptance stage failed [{physical.id}]: settlement or spawn representations are incomplete")
    ids = [row["mapId"] for row in inspected]
    if len(ids) != len(set(ids)) or sum(bool(row["bootstrap"]) for row in inspected) != 1:
        raise PackagingError("runtime acceptance stage failed: physical identities/bootstrap are invalid")
    regional = [row for row in inspected if not row["bootstrap"]]
    if not regional:
        raise PackagingError("runtime acceptance stage failed: bootstrap has no packaged destination")
    if len(regional) > 1 and len({(row["terrainSha256"], row["pathingSha256"]) for row in regional}) == 1:
        raise PackagingError("runtime acceptance stage failed: regional maps are identical placeholders")
    configured_boundaries = {item.id for item in campaign_config.boundaries}
    if boundary_ids != configured_boundaries:
        raise PackagingError("runtime acceptance stage failed: packaged transition set differs from physical-boundaries.json")
    if sha(campaign_path) != before:
        raise PackagingError("campaign artifact changed during verification")
    return {"status": "pass", "maps": inspected, "origins": len(all_origins or []), "failures": [],
            "evidenceLevel": "built_artifact_verification",
            "evidenceLevels": ["binary_structure", "packaged_data_consistency", "compiled_text_static_heuristic"],
            "executionStatus": "completed", "runtimeExecutionStatus": "not_run",
            "sourceRevision": revision, "sourceTreeSha256": source_tree_sha256,
            "artifactSha256": before,
            "transitions": len(boundary_ids), "systems": sorted(runtime_acceptance.MANDATORY_SYSTEMS)}


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
        def metadata(name):
            try:
                value = json.loads(archive.read(name))
            except (KeyError, ValueError) as error:
                raise PackagingError(f"release inspection stage failed: missing or invalid metadata: {name}") from error
            if not isinstance(value, dict):
                raise PackagingError(f"release inspection stage failed: metadata must be a JSON object: {name}")
            return value

        manifest = metadata(config["archive"]["manifestPath"])
        provenance = metadata(config["archive"]["provenancePath"])
        if manifest.get("format") != MANIFEST_FORMAT or provenance.get("format") != PROVENANCE_FORMAT:
            raise PackagingError("release inspection stage failed: metadata format mismatch")
        if manifest.get("releaseCandidateId") != config["releaseCandidateId"]:
            raise PackagingError("release inspection stage failed: RC identifier mismatch")
        revision = provenance.get("sourceRevision")
        if (not isinstance(revision, str) or not re.fullmatch(r"[0-9a-f]{40}", revision) or
                manifest.get("sourceRevision") != revision):
            raise PackagingError("release inspection stage failed: source revision mismatch")
        compatibility = manifest.get("schemaCompatibility")
        if (not isinstance(compatibility, dict) or
                compatibility.get("supportedSaveSchemas") != release_save_compatibility.compatibility_matrix()["campaign"]["supportedSources"]):
            raise PackagingError("release inspection stage failed: save-schema contract mismatch")
        artifacts = manifest.get("artifacts")
        if (not isinstance(artifacts, list) or not artifacts or any(
                not isinstance(row, dict) or not isinstance(row.get("kind"), str) or
                not isinstance(row.get("archivePath"), str) or not _safe_archive_path(row["archivePath"]) or
                type(row.get("bytes")) is not int or row["bytes"] < 0 or
                not isinstance(row.get("sha256"), str) or not re.fullmatch(r"[0-9a-f]{64}", row["sha256"]) or
                (row["kind"] == "physical-map" and not isinstance(row.get("mapId"), str))
                for row in artifacts)):
            raise PackagingError("release inspection stage failed: malformed artifact metadata")
        payload_rows = [item for item in manifest["artifacts"] if item["kind"] != "physical-map"]
        listed = {item["archivePath"]: item for item in payload_rows}
        metadata_names = {config["archive"]["manifestPath"], config["archive"]["provenancePath"]}
        if (len(names) != len(set(names)) or len(payload_rows) != len(listed) or
                set(names) != set(listed) | metadata_names):
            raise PackagingError("release inspection stage failed: archive and manifest member sets differ or contain duplicates")
        for name in names:
            if name in (config["archive"]["manifestPath"], config["archive"]["provenancePath"]):
                continue
            row = listed.get(name)
            if not row or row["bytes"] != len(archive.read(name)) or row["sha256"] != sha_bytes(archive.read(name)):
                raise PackagingError(f"release inspection stage failed: checksum/size mismatch for {name}")
        campaign_bytes = archive.read(config["archive"]["campaignPath"])
        with tempfile.NamedTemporaryFile(suffix=".w3n") as campaign_file:
            campaign_file.write(campaign_bytes); campaign_file.flush()
            campaign_config = load_campaign_config(PROJECT / config["campaignManifest"])
            inspect_campaign(campaign_config, Path(campaign_file.name))
            # Recheck the extracted upload payload, not only the pre-ZIP build.
            identity = source_identity(PROJECT, revision)
            verify_campaign_runtime(Path(campaign_file.name), campaign_config, revision=revision,
                                    source_tree_sha256=identity["sourceTreeSha256"])
            actual_maps = _campaign_rows(Path(campaign_file.name), campaign_config)
            recorded_maps = [item for item in manifest["artifacts"] if item["kind"] == "physical-map"]
            if sorted(recorded_maps, key=lambda row: row["mapId"]) != sorted(actual_maps, key=lambda row: row["mapId"]):
                raise PackagingError("release inspection stage failed: physical-map metadata/checksums differ from the uploaded campaign")
            # Keep the extracted W3N alive through acceptance revalidation.
            try:
                execution = json.loads(archive.read("Metadata/wurst-execution.json"))
                execution_log = archive.read("Metadata/wurst-execution.log")
                verify_evidence(execution, execution_log, provenance["sourceRevision"])
                gates = provenance.get("gates")
                if not isinstance(gates, dict) or gates.get("wurstExecution") != "pass":
                    raise WurstExecutionError("release provenance omits required execution gate")
            except (KeyError, ValueError, WurstExecutionError) as error:
                raise PackagingError(f"release inspection stage failed: Wurst execution evidence: {error}") from error
            current = runtime_acceptance.audit_acceptance(
                execution=execution, execution_log=execution_log, revision=provenance["sourceRevision"],
                campaign=Path(campaign_file.name))
            require_candidate_ready(current)
            for gate in ("runtimeAcceptance", "packagedArtifactVerification", "zeroCampaignBlockers"):
                if gates.get(gate) != "pass":
                    raise PackagingError(f"release inspection stage failed: required {gate} gate is incomplete")
            try:
                recorded_runtime = json.loads(archive.read("Metadata/runtime-acceptance.json"))
                recorded_blocker = json.loads(archive.read("Metadata/release-blocker-audit.json"))
            except (KeyError, ValueError) as error:
                raise PackagingError("release inspection stage failed: acceptance evidence is missing or invalid") from error
            if (recorded_runtime != current or
                    manifest.get("artifactValidation") != current["evidenceLevels"]["builtArtifact"] or
                    provenance.get("sourceIdentity") != source_identity(PROJECT, provenance["sourceRevision"])):
                raise PackagingError("release inspection stage failed: stale or incomplete acceptance evidence")
            from release_blocker_audit import build_report
            blocker = build_report(execution=execution, execution_log=execution_log,
                                   revision=provenance["sourceRevision"], campaign=Path(campaign_file.name))
            if blocker["status"] != "pass" or not blocker["candidateReady"] or recorded_blocker != blocker:
                raise PackagingError("release inspection stage failed: release blocker evidence does not pass")

            # Recompute from the exact W3N extracted from the upload ZIP. A saved
            # passing flag, source-tree census or checksummed-but-stale report is
            # insufficient to authorize publication.
            try:
                trace_report = traceability.validate_final(
                    Path(campaign_file.name), execution, execution_log, provenance["sourceRevision"])
                if (json.loads(archive.read("Metadata/requirement-traceability.json")) != trace_report or
                        gates.get("requirementTraceability") != "pass"):
                    raise ValueError("stale or missing requirement traceability evidence")
            except (KeyError, ValueError) as error:
                raise PackagingError(f"release inspection stage failed: {error}") from error


def require_candidate_ready(report):
    try:
        runtime_acceptance.finalize(report)
    except runtime_acceptance.RuntimeAcceptanceError as error:
        raise PackagingError(f"automated candidate acceptance failed: {error}") from error
    if report["status"] != "pass" or not report["candidateReady"]:
        raise PackagingError("automated candidate acceptance failed: " + "; ".join(report["failures"]))


def build_release_candidate(config_path: Path = CONFIG, grill: str | None = None, revision: str | None = None) -> Path:
    config = load_release_config(config_path)
    # Do not leave a previous candidate at the publication path after a failed
    # attempt. Diagnostic W3N packaging remains available independently.
    clean(config_path)
    for suffix in (".json", ".md"):
        (PROJECT / "_build/release/requirement-traceability").with_suffix(suffix).unlink(missing_ok=True)
    source_trace = traceability.build_report()
    traceability.write_report(source_trace, PROJECT / "_build/requirement-traceability-source")
    if any(row["class"] in {"authority-drift", "invalid-mapping"} for row in source_trace["blockers"]):
        raise PackagingError("requirement traceability inventory is incomplete or invalid")
    try:
        return _build_release_candidate(config, grill, revision)
    finally:
        # Both campaign builds clean _build. Restore this attempt's source
        # diagnostics even when compilation fails before a final W3N exists.
        traceability.write_report(source_trace, PROJECT / "_build/requirement-traceability-source")


def _build_release_candidate(config: dict, grill: str | None, revision: str | None) -> Path:
    compatibility, coverage, runtime_report, fixture_results = validate_gates(config)
    campaign_manifest = PROJECT / config["campaignManifest"]
    campaign_config = load_campaign_config(campaign_manifest)
    inputs = authoritative_hashes()
    revision = source_revision(revision)
    identity = source_identity(PROJECT, revision)

    with tempfile.TemporaryDirectory(prefix="aos-rc-") as temporary:
        first_path = Path(temporary) / "first.w3n"
        shutil.copyfile(build_campaign(campaign_manifest, grill=grill, clean_first=True, revision=revision), first_path)
        first_normalized = normalized_campaign(first_path, campaign_config)
        second = build_campaign(campaign_manifest, grill=grill, clean_first=True, revision=revision)
        campaign_bytes = second.read_bytes()
        execution_dir = PROJECT / "_build/wurst-tests"
        try:
            execution_bytes = (execution_dir / "results.json").read_bytes()
            execution_log = (execution_dir / "execution.log").read_bytes()
            verify_evidence(json.loads(execution_bytes), execution_log, revision)
        except (OSError, ValueError, WurstExecutionError) as error:
            raise PackagingError(f"Wurst execution stage failed: {error}") from error
        trace_report = traceability.audit_final(second, json.loads(execution_bytes), execution_log, revision)
        # Retain the exhaustive final-artifact report before narrower legacy
        # checks can stop this attempt on their first missing system marker.
        second_normalized = normalized_campaign(second, campaign_config)
        if first_normalized != second_normalized:
            difference = sorted(set(first_normalized) | set(second_normalized))
            difference = [x for x in difference if first_normalized.get(x) != second_normalized.get(x)]
            raise PackagingError("determinism stage failed: normalized campaign differs: " + ", ".join(difference))
        # A blocked publication is an expected audit result, but must never
        # disguise a broken build, stale execution or invalid inventory in CI.
        if trace_report["executionErrors"] or any(
                row["class"] in {"authority-drift", "invalid-mapping"} for row in trace_report["blockers"]):
            raise PackagingError("requirement traceability inventory or execution evidence is invalid")
        runtime_report = runtime_acceptance.audit_acceptance(
            execution=json.loads(execution_bytes), execution_log=execution_log, revision=revision, campaign=second)
        require_candidate_ready(runtime_report)
        artifact_validation = runtime_report["evidenceLevels"]["builtArtifact"]
        from release_blocker_audit import build_report
        blocker_report = build_report(execution=json.loads(execution_bytes), execution_log=execution_log,
                                      revision=revision, campaign=second)
        if blocker_report["status"] != "pass" or not blocker_report["candidateReady"]:
            raise PackagingError("gate stage failed: release-blocker audit does not pass")
        if source_identity(PROJECT, revision) != identity:
            raise PackagingError("authoritative sources changed during candidate build")
        try:
            traceability.trace.require_ready(trace_report)
        except ValueError as error:
            raise CandidatePublicationBlocked(str(error)) from error
        target = config["runtimeTarget"]
        save = compatibility["matrix"]
        provenance = {
            "format": PROVENANCE_FORMAT, "formatVersion": 1,
            "releaseCandidateId": config["releaseCandidateId"], "sourceRevision": revision,
            "sourceIdentity": identity,
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
            "normalizedCampaignEntries": first_normalized,
            "normalizedEquivalence": {"builds": 2, "equal": True, "ignoredDifference": "ZIP/MPQ entry order, timestamps, compression, and container metadata only"},
            "releaseStatus": config.get("releaseStatus", "blocked_pending_human_launch_smoke_test"),
            "requiredHumanValidation": config.get("requiredHumanValidation"),
            "gates": {"phase8Content": coverage["status"], "runtimeAcceptance": runtime_report["status"], "releaseSaveCompatibility": "pass", "recoveryDocumentation": "pass", "licenseAndAssetProvenance": "pass", "finalBudgets": "pass", "zeroCampaignBlockers": "pass", "packagedArtifactVerification": "pass", "humanLaunchSmokeTest": "not_run_separate_manual_smoke"},
        }
        provenance["gates"]["wurstExecution"] = "pass"
        provenance["gates"]["requirementTraceability"] = "pass"
        payloads = {config["archive"]["campaignPath"]: campaign_bytes,
                    "Metadata/wurst-execution.json": execution_bytes,
                    "Metadata/wurst-execution.log": execution_log,
                    "Metadata/requirement-traceability.json": canonical(trace_report),
                    "Metadata/requirement-traceability.md": traceability.trace.render_markdown(trace_report).encode(),
                    "Metadata/runtime-acceptance.json": canonical(runtime_report),
                    "Metadata/release-blocker-audit.json": canonical(blocker_report)}
        for relative in config["releaseDocuments"]:
            payloads[f"Documentation/{Path(relative).name}"] = (PROJECT / relative).read_bytes()
        rows = [{"filename": PurePosixPath(name).name, "archivePath": name, "kind": "campaign" if name.endswith(".w3n") else "documentation", "bytes": len(value), "sha256": sha_bytes(value)} for name, value in sorted(payloads.items())]
        rows += _campaign_rows(second, campaign_config)
        artifact_manifest = {
            "format": MANIFEST_FORMAT, "formatVersion": 1,
            "releaseCandidateId": config["releaseCandidateId"], "campaignId": campaign_config.campaign_id,
            "sourceRevision": revision,
            "runtimeTarget": target,
            "schemaCompatibility": {"scenarioVersion": config["scenarioVersion"], "currentSaveSchema": save["campaign"]["current"], "supportedSaveSchemas": save["campaign"]["supportedSources"]},
            "artifacts": rows,
            "smokeJourneys": {"evidenceLevel": "real_client_execution", "status": "not_run"},
            "headlessCampaignJourneys": {"evidenceLevel": "headless_fixture_execution", "status": "pass",
                                         "executedChecks": ["full_world_soak.smoke", "campaign_save_round_trip_and_migration"],
                                         "routeExecutionStatus": "not_run", "nativeSaveExecutionStatus": "not_run",
                                         "verification": "tooling/release_blocker_audit.py"},
            "saveMigrationFixtures": fixture_results,
            "artifactValidation": artifact_validation,
        }
        payloads[config["archive"]["manifestPath"]] = canonical(artifact_manifest)
        payloads[config["archive"]["provenancePath"]] = canonical(provenance)
        audit_payloads(payloads, config)
        output = PROJECT / "_build/release" / config["archive"]["fileName"]
        publish_verified_archive(output, payloads, config)
    print(f"release candidate: {output}")
    return output


def publish_verified_archive(output: Path, payloads: dict[str, bytes], config: dict) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    # Verify the completed ZIP before atomically exposing the publication path.
    with tempfile.TemporaryDirectory(prefix=".candidate-", dir=output.parent) as directory:
        pending = Path(directory) / "candidate.zip"
        _write_zip(pending, payloads)
        verify_release_archive(pending, config)
        pending.replace(output)


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
    except CandidatePublicationBlocked as error:
        print(f"release candidate publication blocked: {error}", file=sys.stderr)
        return PUBLICATION_BLOCKED_EXIT
    except (PackagingError, OSError, KeyError, ValueError, zipfile.BadZipFile) as error:
        print(f"release candidate packaging failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
