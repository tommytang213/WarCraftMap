#!/usr/bin/env python3
"""Verify this issue's obligations against the current exact diagnostic W3N.

Run after package_campaign.py. This preserves the complete release-blocker
report and never converts scoped readiness into candidate publication readiness.
"""
import json
from pathlib import Path
import sys

PROJECT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT / 'tooling'))
sys.path.insert(0, str(PROJECT.parent / '_shared/tooling'))
import requirement_traceability_audit as scenario
import requirement_traceability as trace
import runtime_acceptance as runtime
from integration_evidence import source_identity
from wurst_execution import source_revision

ids = {'REQ-0203.01', 'REQ-0204.01', 'REQ-0205.01', 'REQ-0205.02', 'REQ-0206.01', 'REQ-0207.01'}
revision = source_revision(PROJECT)
artifact = PROJECT / '_build/release/AgeOfSailWorldCampaign.w3n'
execution = trace.load(PROJECT / '_build/wurst-tests/results.json')
transcript = (PROJECT / '_build/wurst-tests/execution.log').read_bytes()
report = scenario.audit_final(artifact, execution, transcript, revision)
assert not report['executionErrors'], report['executionErrors']
rows = [row for row in report['requirements'] if row['id'] in ids]
assert {row['id'] for row in rows} == ids
assert all(row['status'] == 'pass' for row in rows), [(r['id'], r['blockerClasses']) for r in rows]
assert not report['candidateReady'] and report['blockerCount'] > 0
assert not any(row['id'] in ids for row in report['blockers'])
acceptance = runtime.audit_acceptance(execution=execution, execution_log=transcript,
                                     revision=revision, campaign=artifact)
for level in ('runtimeIntegration', 'builtArtifact'):
    assert acceptance['evidenceLevels'][level]['status'] == 'pass', acceptance['evidenceLevels'][level]
output = PROJECT / '_build/release/issue-411-scoped-evidence.json'
result = {**source_identity(PROJECT, revision), 'scope': sorted(ids),
          'status': 'pass', 'artifactSha256': report['artifact']['sha256'],
          'artifactBytes': artifact.stat().st_size,
          'scopedBlockers': [], 'candidateReady': report['candidateReady'],
          'remainingBlockerCount': report['blockerCount'],
          'remainingBlockerClasses': report['blockerClasses'],
          'pinnedTestsPassed': execution['succeeded'],
          'compilerSha256': execution['compiler']['sha256'],
          'transcriptSha256': execution['logSha256'],
          'inputSetSha256': execution['inputSetSha256'],
          'receipts': [json.loads(line.removeprefix('TRACEABILITY '))
                       for line in transcript.decode().splitlines() if line.startswith('TRACEABILITY ')]}
result['receipts'] = [row for row in result['receipts'] if row['requirement'] in ids]
assert len(result['receipts']) == 24
assert {(row['requirement'], row['case']) for row in result['receipts']} == {
    (requirement, case) for requirement in ids for case in ('success', 'failure', 'stale', 'replay')}
output.write_bytes(trace.canonical(result))
(PROJECT / '_build/release/issue-411-runtime-acceptance.json').write_bytes(trace.canonical(acceptance))
print(json.dumps({key: result[key] for key in ('status', 'scope', 'artifactSha256', 'pinnedTestsPassed', 'remainingBlockerCount')}, indent=2))
