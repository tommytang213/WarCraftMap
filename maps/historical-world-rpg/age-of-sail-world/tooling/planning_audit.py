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
import release_blocker_audit
import requirement_traceability_audit
import runtime_acceptance

REPORTS = {"release": "reports/release-blocker-audit.json",
           "runtime": "reports/runtime-acceptance.json",
           "traceability": "reports/traceability/requirements.json"}


def regenerate(revision):
    identity = source_identity(PROJECT, revision)
    result = {"revision": revision, "regenerated": True, "reports": {}}
    execution_path = PROJECT / "_build/wurst-tests/results.json"
    transcript_path = execution_path.with_name("execution.log")
    try:
        execution = json.loads(execution_path.read_text())
        transcript = transcript_path.read_bytes()
    except (OSError, ValueError):
        execution, transcript = None, None
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
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-revision", required=True)
    args = parser.parse_args()
    print(json.dumps(regenerate(args.source_revision), sort_keys=True))


if __name__ == "__main__":
    main()
