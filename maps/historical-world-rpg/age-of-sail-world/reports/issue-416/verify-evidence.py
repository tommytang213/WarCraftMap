#!/usr/bin/env python3
"""Check issue 416 against current sources, executed adapters and exact W3N bytes."""
import argparse
import json
from pathlib import Path
import sys

PROJECT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(PROJECT / 'tooling'), str(PROJECT.parent / '_shared/tooling')]
import requirement_traceability_audit as scenario
import requirement_traceability as trace
from integration_evidence import source_identity
from wurst_execution import source_revision


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--artifact', type=Path, required=True)
    parser.add_argument('--execution-dir', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--source-revision')
    args = parser.parse_args()
    revision = source_revision(PROJECT, args.source_revision)
    execution = trace.load(args.execution_dir / 'results.json')
    transcript = (args.execution_dir / 'execution.log').read_bytes()
    report = scenario.build_report(args.artifact, execution, transcript, revision)
    scenario.write_report(report, args.output_dir / 'requirement-traceability')
    assert not report['executionErrors'], report['executionErrors']
    required = {'REQ-0181.01', 'REQ-0181.02'}
    rows = [r for r in report['requirements'] if r['id'] in required]
    assert {r['id'] for r in rows} == required
    assert all(r['status'] == 'pass' for r in rows), [(r['id'], r['blockerClasses']) for r in rows]
    catalogues = {r['id']: r for r in report['catalogues']}
    world = trace.load(PROJECT / 'scenario/world/world.json')
    expected = {r['id'] for r in world['settlements']}
    profiles = trace.load(PROJECT / 'scenario/integration/release-scale-settlements.json')['settlements']
    abstract = sorted(r['settlementId'] for r in profiles if r['gameplayRoles']['physicalMap']['modelId'] == 'abstract_regional_projection')
    assert len(abstract) == 33
    for name in ('settlements', 'markets'):
        row = catalogues[name]
        assert row['status'] == 'pass', row['failures']
        assert row['sourceCount'] == row['packagedUniqueCount'] == len(expected)
        assert all(m['compiledCount'] == len(expected) for m in row['maps'])
    policies = catalogues['settlements']['projectionPolicy']
    assert policies['status'] == 'pass', policies
    assert {r['id'] for r in policies['policies']} == expected
    assert all(not r['projectMilitary'] for r in policies['policies'] if r['id'] in abstract)
    receipts = [json.loads(line.removeprefix('TRACEABILITY ')) for line in transcript.decode().splitlines() if line.startswith('TRACEABILITY ')]
    receipts = [r for r in receipts if r['requirement'] in required]
    assert len(receipts) == 8
    assert {(r['requirement'], r['case']) for r in receipts} == {(r, c) for r in required for c in ('success', 'failure', 'stale', 'replay')}
    assert not report['candidateReady'] and report['blockerCount'] > 0
    result = {**source_identity(PROJECT, revision), 'status': 'pass',
              'artifactSha256': report['artifact']['sha256'],
              'authoritySettlementCount': len(expected), 'marketSettlementCount': len(expected),
              'restoredAbstractSettlementIds': abstract, 'projectionPolicy': policies,
              'requirements': [{'id': r['id'], 'status': r['status']} for r in rows],
              'receipts': len(receipts), 'candidateReady': False,
              'remainingPublicationBlockers': report['blockerCount'],
              'releaseStatus': 'blocked_pending_real_forsaken_kingdom_launch_smoke',
              'realClientExecuted': False}
    (args.output_dir / 'scoped-evidence.json').write_text(json.dumps(result, indent=2, sort_keys=True)+'\n')
    print('PASS: all authored settlements and markets, deliberate projection policy, and both scoped requirements; unrelated blockers retained')


if __name__ == '__main__':
    main()
