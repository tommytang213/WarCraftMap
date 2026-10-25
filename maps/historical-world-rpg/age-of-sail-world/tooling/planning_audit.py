#!/usr/bin/env python3
"""Regenerate the planner's closure evidence without rewriting tracked reports.

Compiler execution and campaign packaging stay in the normal validation lane.
Available evidence is verified by each audit; missing/stale artifacts fail closed.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT.parent / "_shared/tooling"))
from integration_evidence import source_identity
from execution_transport import read_bundle
from wurst_execution import PINNED_COMPILER_SHA256, canonical, sha
import release_blocker_audit
import requirement_traceability_audit
import runtime_acceptance

REPORTS = {"release": "reports/release-blocker-audit.json",
           "runtime": "reports/runtime-acceptance.json",
           "traceability": "reports/traceability/requirements.json"}

# Reconcile these existing consumer findings after shared execution is available.
# These identities select observations, never grant bindings or waive a verifier.
COMPARISONS = {
    "agriculture": (
        "AGRARIAN-IMPROVEMENT-BUILDING-GRANARY",
        "AGRARIAN-IMPROVEMENT-POLICY-LAND-TENURE-REFORM",
        "AGRICULTURAL-MECHANIZATION-POLICY-ENCLOSURE",
        "AGRICULTURAL-SOCIETIES-POLICY-PROGRESSION-AGRICULTURAL-SOCIETIES"),
    "civicLandAuction": (
        "ABOLITIONIST-PUBLIC-SPHERE-POLICY-PROGRESSION-ABOLITIONIST-PUBLIC-SPHERE",
        "ANATOMY-AND-MEDICINE-ABILITY-EPIDEMIC-CONTROL",
        "ARQUEBUS-VOLLEY-DRILL-MODIFIER-PROGRESSION-ARQUEBUS-VOLLEY-DRILL",
        "ARTILLERY-OFFICES-POLICY-PROGRESSION-ARTILLERY-OFFICES",
        "ARTILLERY-TRAIN-MODIFIER-PROGRESSION-ARTILLERY-TRAIN",
        "BAYONET-SYSTEM-MODIFIER-PROGRESSION-BAYONET-SYSTEM",
        "AUCTION-MARKETS-MODIFIER-PROGRESSION-AUCTION-MARKETS"),
}


def inspect_execution(revision, directory=None):
    """Use the transport verifier for both controller reuse and audit ingestion."""
    directory = Path(directory) if directory is not None else PROJECT / "_build/wurst-tests"
    result = {"directory": str(directory), "valid": False,
              "sourceIdentity": source_identity(PROJECT, revision),
              "compilerSha256": PINNED_COMPILER_SHA256}
    try:
        execution, transcript = read_bundle(directory, PROJECT, revision)
    except (OSError, ValueError, RuntimeError, KeyError, TypeError, AttributeError) as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
        return result, None, None
    result.update(valid=True, evidenceSha256=sha(canonical(execution)))
    return result, execution, transcript


def regenerate(revision, directory=None):
    result = {"revision": revision, "regenerated": True, "reports": {}}
    result["execution"], execution, transcript = inspect_execution(revision, directory)
    identity = result["execution"]["sourceIdentity"]
    config = json.loads((PROJECT / "physical-maps.json").read_text())
    campaign = PROJECT / config["outputDirectory"] / (config["campaign"]["fileName"] + ".w3n")
    campaign = campaign if campaign.is_file() else None
    audits = {
        "release": lambda: release_blocker_audit.build_report(
            execution=execution, execution_log=transcript, revision=revision, campaign=campaign),
        "runtime": lambda: runtime_acceptance.audit_acceptance(
            execution=execution, execution_log=transcript, revision=revision, campaign=campaign),
        "traceability": lambda: requirement_traceability_audit.build_report(campaign, execution, transcript, revision),
    }
    for name, relative in REPORTS.items():
        entry = result["reports"][name] = {}
        try:
            entry["recorded"] = json.loads((PROJECT / relative).read_text())
        except (OSError, ValueError):
            entry["recorded"] = None
        try:
            entry["report"] = audits[name]()
        except Exception as exc:
            # Preserve independent findings even when another audit crashes.
            entry["error"] = f"{type(exc).__name__}: {exc}"
    if source_identity(PROJECT, revision) != identity:
        result["regenerated"] = False
    result["sourceIdentity"] = identity
    release = result["reports"]["release"].get("report", {})
    findings = release.get("findings")
    verified = (result["regenerated"] and result["execution"]["valid"] and isinstance(findings, list))
    remaining = {row["id"] for row in findings} if isinstance(findings, list) else set()
    unavailable = ("source_changed" if not result["regenerated"] else
                   "execution_unavailable" if not result["execution"]["valid"] else "audit_unavailable")
    result["consumerComparisons"] = {
        group: {"release:RESEARCH-UNBOUND-" + suffix:
                ("remaining" if "RESEARCH-UNBOUND-" + suffix in remaining else "absent")
                if verified else unavailable
                for suffix in suffixes}
        for group, suffixes in COMPARISONS.items()}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--evidence-directory", type=Path)
    parser.add_argument("--execution-only", action="store_true")
    args = parser.parse_args()
    result = (inspect_execution(args.source_revision, args.evidence_directory)[0] if args.execution_only
              else regenerate(args.source_revision, args.evidence_directory))
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
