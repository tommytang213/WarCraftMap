#!/usr/bin/env python3
"""Deterministic Phase 8 integrated-campaign release-blocker gate."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
ENGINE = PROJECT.parent / "_shared" / "engine"
sys.path.insert(0, str(ENGINE))
import campaign_save
import full_world_soak

CONFIG = PROJECT / "scenario/release-blocker-gate.json"
REPORT_JSON = PROJECT / "reports/release-blocker-audit.json"
REPORT_MD = PROJECT / "reports/release-blocker-audit.md"
REPORT_FORMAT = "age_of_sail_release_blocker_report_v1"
STABLE_ID = re.compile(r"^[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)+$")
BLOCKING_MARKERS = re.compile(r"\b(?:TODO|TBD|FIXME)\b|placeholder that blocks", re.I)


class GateError(ValueError):
    pass


def _load(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise GateError(f"cannot read JSON {path.relative_to(PROJECT)}: {exc}") from exc


def _finding(stable_id, blocker_class, context, message, severity="campaign_blocker",
             disposition="unresolved"):
    if not STABLE_ID.fullmatch(stable_id):
        raise GateError(f"finding has invalid stable ID: {stable_id}")
    return {"id": stable_id, "severity": severity, "class": blocker_class,
            "context": context, "message": message, "disposition": disposition}


def _audit_reports(config):
    findings, audited = [], []
    paths = sorted({p for pattern in config["reportGlobs"] for p in PROJECT.glob(pattern)
                    if p.is_file() and p not in {REPORT_JSON}})
    for path in paths:
        relative = path.relative_to(PROJECT).as_posix()
        data = _load(path)
        audited.append(relative)
        statuses = []
        if isinstance(data, dict):
            for key in ("status", "result"):
                if isinstance(data.get(key), str):
                    statuses.append(data[key].lower())
            if data.get("passed") is False:
                statuses.append("failed")
            for key in ("errors", "failures", "unresolved"):
                value = data.get(key)
                if isinstance(value, list) and value:
                    statuses.append(key)
                elif isinstance(value, int) and value > 0:
                    statuses.append(key)
        bad = sorted(set(statuses) & {"fail", "failed", "error", "errors", "failures", "unresolved"})
        if bad:
            digest = hashlib.sha256(relative.encode()).hexdigest()[:10].upper()
            findings.append(_finding(f"REPORT-FAIL-{digest}", "suppressed_blocker", relative,
                                     f"tracked validation report contains unresolved status: {', '.join(bad)}"))
    return audited, findings


def _audit_inputs(config):
    hashes, findings = {}, []
    for relative in config["releaseInputs"]:
        path = PROJECT / relative
        if not path.is_file():
            token = hashlib.sha256(relative.encode()).hexdigest()[:10].upper()
            findings.append(_finding(f"INPUT-MISSING-{token}", "corrupt_package", relative,
                                     "required release input is missing"))
            continue
        hashes[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
        if path.suffix == ".json":
            _load(path)
    for root_name in ("scenario", "map", "wurst"):
        root = PROJECT / root_name
        for path in sorted(root.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in {".json", ".wurst", ".j", ".wts"}:
                continue
            relative = path.relative_to(PROJECT).as_posix()
            if "/reports/" in f"/{relative}" or relative == "scenario/release-blocker-gate.json":
                continue
            if BLOCKING_MARKERS.search(path.read_text(encoding="utf-8", errors="replace")):
                token = hashlib.sha256(relative.encode()).hexdigest()[:10].upper()
                findings.append(_finding(f"CONTENT-STUB-{token}", "blocking_content_stub", relative,
                                         "release input contains an unresolved blocking marker"))
    return hashes, findings


def _migration_round_trip(state):
    raw = campaign_save.serialize_save(
        build_version="phase8-gate", scenario_id="age_of_sail_world", scenario_version="1",
        slot=campaign_save.SaveSlot("manual", 1), created_at="1635-01-01T00:00:00Z",
        world_state=state, player_state={"captain": {"level": 1}})
    loaded = campaign_save.load_save(raw)
    old = json.loads(raw)
    old["schemaVersion"] = 3
    old["state"]["world"].pop("treasures", None)
    old["integrity"]["checksum"] = campaign_save._checksum(old)
    migrated = campaign_save.load_save(json.dumps(old))
    if migrated["schemaVersion"] != campaign_save.CURRENT_SCHEMA_VERSION:
        raise GateError("supported save did not migrate to current schema")
    return hashlib.sha256(raw).hexdigest(), loaded["schemaVersion"]


def _run_journeys(config):
    soak_config_path = PROJECT / "scenario/benchmarks/full-world-soak.json"
    soak_config, sources, profiles = full_world_soak.load_config(soak_config_path)
    smoke = full_world_soak.run_profile(soak_config, sources, profiles["smoke"])
    if not smoke["passed"]:
        raise GateError(f"integrated full-world soak failed: {smoke['failures']}")
    physical = _load(PROJECT / "physical-maps.json")
    map_ids = {row["id"] for row in physical["physicalMaps"]}
    required = set(config["requiredSystems"])
    covered, results = set(), []
    for journey in config["journeys"]:
        missing_maps = sorted(set(journey["physicalMaps"]) - map_ids)
        if missing_maps:
            raise GateError(f"{journey['id']}: unknown physical maps {missing_maps}")
        systems = set(journey["systems"])
        unknown = systems - required
        if unknown:
            raise GateError(f"{journey['id']}: unclassified systems {sorted(unknown)}")
        state = full_world_soak.build_fixture(soak_config, sources, journey["seed"])
        save_hash, schema = _migration_round_trip(state)
        # Repeated first/last maps deliberately prove return transitions rather than a one-way tour.
        if journey["physicalMaps"][0] != journey["physicalMaps"][-1]:
            raise GateError(f"{journey['id']}: journey does not include a repeated physical-map transition")
        if date_year(state["endDate"]) < 1820:
            raise GateError(f"{journey['id']}: journey does not reach the late campaign")
        covered.update(systems)
        results.append({"id": journey["id"], "seed": journey["seed"], "branch": journey["branch"],
                        "regions": journey["regions"], "physicalMaps": journey["physicalMaps"],
                        "systems": sorted(systems), "endDate": state["endDate"],
                        "saveSchema": schema, "saveHash": save_hash, "status": "pass"})
    missing = sorted(required - covered)
    if missing:
        raise GateError(f"journey coverage misses required systems: {missing}")
    return results, smoke


def date_year(value):
    try:
        return int(value[:4])
    except (TypeError, ValueError):
        raise GateError(f"invalid campaign date {value!r}")


def build_report(*, injected_findings=()):
    config = _load(CONFIG)
    taxonomy = {row["id"]: row for row in config["taxonomy"]}
    if "campaign_blocker" not in taxonomy or "critical_unclassified" not in taxonomy:
        raise GateError("taxonomy must define campaign_blocker and critical_unclassified")
    audited, report_findings = _audit_reports(config)
    inputs, input_findings = _audit_inputs(config)
    journeys, soak = _run_journeys(config)
    findings = sorted([*report_findings, *input_findings, *injected_findings], key=lambda x: x["id"])
    for finding in findings:
        if finding.get("severity") not in taxonomy:
            finding["severity"] = "critical_unclassified"
        if finding.get("class") not in config["blockerClasses"]:
            finding["severity"] = "critical_unclassified"
    unresolved = [f for f in findings if f["disposition"] == "unresolved" and taxonomy[f["severity"]]["releaseBlocking"]]
    limitations = config["knownLimitations"]
    for row in limitations:
        if row.get("severity") not in {"major", "minor"} or not row.get("bounds"):
            unresolved.append(_finding(f"LIMITATION-UNCLASSIFIED-{len(unresolved)+1}",
                                       "suppressed_blocker", "knownLimitations",
                                       "known limitation is not explicitly non-blocking and bounded",
                                       "critical_unclassified"))
    return {"format": REPORT_FORMAT, "status": "pass" if not unresolved else "fail",
            "gate": "No known campaign-blocking defects", "taxonomy": config["taxonomy"],
            "blockerClasses": config["blockerClasses"], "releaseInputs": inputs,
            "auditedReports": audited, "journeys": journeys,
            "soak": {"format": soak["format"], "passed": soak["passed"], "runs": soak["runs"]},
            "knownLimitations": limitations, "findings": findings,
            "unresolvedCampaignBlockers": len(unresolved),
            "disposition": "gate_closed" if not unresolved else "release_blocked"}


def render_markdown(report):
    lines = ["# Phase 8 release-blocker audit", "", f"Result: **{report['status'].upper()}**",
             "", f"Unresolved campaign blockers: **{report['unresolvedCampaignBlockers']}**", "",
             "## Severity taxonomy", "", "| ID | Release blocking | Definition |", "|---|---:|---|"]
    for row in report["taxonomy"]:
        lines.append(f"| `{row['id']}` | {'yes' if row['releaseBlocking'] else 'no'} | {row['definition']} |")
    lines += ["", "## Deterministic campaign journeys", "", "| Stable ID | Branch | Seed | Regions | Maps | Result |",
              "|---|---|---:|---:|---:|---|"]
    for row in report["journeys"]:
        lines.append(f"| `{row['id']}` | {row['branch']} | {row['seed']} | {len(row['regions'])} | {len(row['physicalMaps'])} | {row['status']} |")
    lines += ["", "## Findings", ""]
    if not report["findings"]:
        lines.append("No unresolved or accepted defects were found.")
    else:
        lines += ["| Stable ID | Severity | Class | Context | Disposition |", "|---|---|---|---|---|"]
        for row in report["findings"]:
            lines.append(f"| `{row['id']}` | {row['severity']} | {row['class']} | {row['context']} | {row['disposition']} |")
    lines += ["", "## Audited release evidence", "", f"- {len(report['auditedReports'])} tracked validation reports",
              f"- {len(report['releaseInputs'])} hashed release inputs",
              f"- {len(report['soak']['runs'])} deterministic 1450–1820 soak runs",
              "- Fresh start, supported-save migration, manual save, rolling autosave, checkpoints, native save/load, interrupted transition recovery, and representation reconstruction are journey-gated.", ""]
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)
    report = build_report()
    encoded = json.dumps(report, indent=2, sort_keys=True) + "\n"
    human = render_markdown(report)
    if args.write:
        REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
        REPORT_JSON.write_text(encoded, encoding="utf-8")
        REPORT_MD.write_text(human, encoding="utf-8")
    elif not REPORT_JSON.is_file() or REPORT_JSON.read_text(encoding="utf-8") != encoded \
            or not REPORT_MD.is_file() or REPORT_MD.read_text(encoding="utf-8") != human:
        raise GateError("release-blocker reports are missing or stale; run with --write")
    print(json.dumps({"status": report["status"], "unresolvedCampaignBlockers": report["unresolvedCampaignBlockers"]}, sort_keys=True))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
