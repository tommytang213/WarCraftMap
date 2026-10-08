#!/usr/bin/env python3
"""Verify issue 415 adapter receipts against the current source and diagnostic W3N."""
import argparse
import json
from pathlib import Path
import re
import sys

PROJECT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(PROJECT / 'tooling'), str(PROJECT.parent / '_shared/tooling')]
import requirement_traceability_audit as scenario
import requirement_traceability as trace
import runtime_acceptance as runtime
from integration_evidence import source_identity
from wurst_execution import source_revision


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--artifact', type=Path, required=True)
    parser.add_argument('--execution-dir', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--source-revision')
    args = parser.parse_args()
    required = {'REQ-0208.01', 'REQ-0209.01', 'REQ-0209.02', 'REQ-0210.01',
                'REQ-0211.01', 'REQ-0211.02', 'REQ-0212.01', 'REQ-0212.02',
                'REQ-0213.01', 'REQ-0214.01'}
    dependency = 'DEP-god-controller-reconstruction'
    revision = source_revision(PROJECT, args.source_revision)
    execution = trace.load(args.execution_dir / 'results.json')
    transcript = (args.execution_dir / 'execution.log').read_bytes()
    report = scenario.build_report(args.artifact, execution, transcript, revision)
    scenario.write_report(report, args.output_dir / 'requirement-traceability')
    assert not report['executionErrors'], report['executionErrors']
    rows = [row for row in report['requirements'] if row['id'] in required]
    assert {row['id'] for row in rows} == required
    assert all(row['status'] == 'pass' for row in rows), [
        (row['id'], row['blockerClasses']) for row in rows]
    edge = next(row for row in report['dependencies'] if row['id'] == dependency)
    assert edge['status'] == 'pass', edge
    assert not report['candidateReady'] and report['blockerCount'] > 0
    acceptance = runtime.audit_acceptance(execution=execution, execution_log=transcript,
                                         revision=revision, campaign=args.artifact)
    for level in ('runtimeIntegration', 'builtArtifact'):
        assert acceptance['evidenceLevels'][level]['status'] == 'pass', acceptance['evidenceLevels'][level]
    maps = [{**row, 'bootstrap': row.get('bootstrap', False)} for row in
            json.loads((PROJECT / 'physical-maps.json').read_text())['physicalMaps']]
    _, payloads, errors = trace.inspect_artifact(args.artifact, maps)
    assert not errors, errors
    compiled = {}
    events = ('EVENT_PLAYER_UNIT_CHANGE_OWNER', 'EVENT_PLAYER_UNIT_SUMMON',
              'EVENT_PLAYER_UNIT_TRAIN_FINISH', 'EVENT_PLAYER_UNIT_CONSTRUCT_FINISH')
    for physical in maps:
        if physical.get('bootstrap'):
            continue
        calls = trace.compiled_calls(payloads[physical['id']])
        registrations = {}
        for event in events:
            matches = [call for call in calls if re.match(
                r'dispatch_GodModeNatives_registerPlayerEvent\([^\n]*,\s*'
                + event + r'(?:,|\))', call)]
            assert len(matches) == 1, (physical['id'], event, matches)
            assert 'PlayerGodMode_lifecycle' in matches[0]
            registrations[event] = matches[0]
        for registration in ('registerEnter', 'registerSweep'):
            matches = [call for call in calls if call.startswith(
                'dispatch_GodModeNatives_' + registration + '(')]
            assert len(matches) == 1, (physical['id'], registration, matches)
            assert 'PlayerGodMode_lifecycle' in matches[0]
            registrations[registration] = matches[0]
        compiled[physical['id']] = registrations
    receipts = [json.loads(line.removeprefix('TRACEABILITY '))
                for line in transcript.decode().splitlines() if line.startswith('TRACEABILITY ')]
    receipts = [row for row in receipts if row['requirement'] in required | {dependency}]
    assert len(receipts) == 44
    assert {(row['requirement'], row['case']) for row in receipts} == {
        (requirement, case) for requirement in required | {dependency}
        for case in ('success', 'failure', 'stale', 'replay')}
    result = {
        **source_identity(PROJECT, revision), 'status': 'pass',
        'requirements': [{'id': row['id'], 'status': row['status']} for row in rows],
        'dependency': {'id': dependency, 'status': edge['status']},
        'receipts': len(receipts), 'candidateReady': False,
        'remainingPublicationBlockers': report['blockerCount'],
        'artifactSha256': report['artifact']['sha256'],
        'compiledRegistrations': compiled,
        'releaseStatus': 'blocked_pending_real_forsaken_kingdom_launch_smoke',
        'realClientExecuted': False,
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / 'scoped-evidence.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    (args.output_dir / 'runtime-acceptance.json').write_text(json.dumps(acceptance, indent=2, sort_keys=True) + '\n')
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
