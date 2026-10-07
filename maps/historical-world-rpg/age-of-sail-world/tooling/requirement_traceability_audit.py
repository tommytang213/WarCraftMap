#!/usr/bin/env python3
"""Generate the exhaustive requirement report; only --check permits known gaps."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT.parent / "_shared/tooling"))
import requirement_traceability as trace

DIRECTORY = PROJECT / "scenario/traceability"
REPORT = PROJECT / "reports/traceability/requirements"


def build_report(artifact=None, evidence=None, transcript=None, revision=""):
    ledger = trace.load(DIRECTORY / "requirements.json")
    mappings = trace.load(DIRECTORY / "mappings.json")
    catalogues = trace.load(DIRECTORY / "catalogues.json")
    physical = trace.load(PROJECT / "physical-maps.json")["physicalMaps"]
    maps = [{"id": row["id"], "packagePath": row["packagePath"],
             "bootstrap": row.get("bootstrap", False), "_self": [row["id"]],
             **row["assignments"]} for row in physical]
    return trace.audit(PROJECT, ledger, mappings, catalogues, maps, artifact=artifact,
                       evidence=evidence, transcript=transcript, revision=revision,
                       authority_documents=("docs/DESIGN_LOCK.md", "docs/ROADMAP.md"))


def write_report(report, base=REPORT):
    base.parent.mkdir(parents=True, exist_ok=True)
    base.with_suffix(".json").write_bytes(trace.canonical(report))
    base.with_suffix(".md").write_text(trace.render_markdown(report))


def validate_final(artifact, evidence, transcript, revision):
    report = build_report(artifact, evidence, transcript, revision)
    # Always retain the complete census/byte composition, including failed RCs.
    write_report(report, PROJECT / "_build/release/requirement-traceability")
    trace.require_ready(report)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", type=Path)
    parser.add_argument("--execution", type=Path)
    parser.add_argument("--transcript", type=Path)
    parser.add_argument("--source-revision", default="")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--check", action="store_true", help="validate ledger/report freshness, allowing explicitly reported release blockers")
    parser.add_argument("--output", type=Path, default=REPORT)
    args = parser.parse_args(argv)
    report = build_report(args.artifact, trace.load(args.execution) if args.execution else None,
                          args.transcript.read_bytes() if args.transcript else None, args.source_revision)
    if args.write:
        write_report(report, args.output)
    if args.check:
        expected = {".json": trace.canonical(report), ".md": trace.render_markdown(report).encode()}
        for suffix, value in expected.items():
            path = args.output.with_suffix(suffix)
            if not path.is_file() or path.read_bytes() != value:
                raise ValueError(f"stale requirement report: {path}")
        if any(row["class"] in {"authority-drift", "invalid-mapping"} for row in report["blockers"]):
            raise ValueError("requirement inventory is incomplete or mappings are invalid")
    else:
        trace.require_ready(report)
    print(f"Traceability: {len(report['requirements'])} obligations; {report['blockerCount']} publication blockers")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, OSError, KeyError) as error:
        print(error, file=sys.stderr)
        raise SystemExit(1)
