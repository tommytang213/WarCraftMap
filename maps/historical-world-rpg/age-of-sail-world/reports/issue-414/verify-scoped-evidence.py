#!/usr/bin/env python3
"""Verify issue #414 receipts and compiled evidence against the current source."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

PROJECT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT / 'tooling'))
from requirement_traceability_audit import build_report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--artifact', type=Path, default=PROJECT / '_build/release/AgeOfSailWorldCampaign.w3n')
    parser.add_argument('--execution', type=Path, default=PROJECT / '_build/wurst-tests/results.json')
    parser.add_argument('--transcript', type=Path, default=PROJECT / '_build/wurst-tests/execution.log')
    args = parser.parse_args()
    revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=PROJECT, text=True).strip()
    evidence = json.loads(args.execution.read_text())
    report = build_report(args.artifact, evidence, args.transcript.read_bytes(), revision)
    scope = {f'REQ-{number:04}.01' for number in range(191, 203)}
    scoped = {
        'scope': sorted(scope),
        'sourceIdentity': evidence['sourceIdentity'],
        'requirements': [row for row in report['requirements'] if row['id'] in scope],
        'blockers': [row for row in report['blockers'] if row['id'] in scope],
        'outOfScopeBlockerCount': sum(row['id'] not in scope for row in report['blockers']),
    }
    destination = Path(__file__).with_name('scoped-traceability.json')
    destination.write_text(json.dumps(scoped, indent=2, sort_keys=True) + '\n')
    if scoped['blockers'] or len(scoped['requirements']) != 12:
        raise SystemExit('Issue #414 scope has missing evidence; see ' + str(destination))
    print('PASS: all 12 unstuck obligations have current production receipts and compiled artifact evidence.')


if __name__ == '__main__':
    main()
