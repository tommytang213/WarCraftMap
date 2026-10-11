"""Regenerate issue #465 evidence without claiming downstream gameplay closure."""
import gzip
import json
from pathlib import Path
import sys

PROJECT = Path(__file__).resolve().parents[2]
SHARED = PROJECT.parent / '_shared'
sys.path[:0] = [str(SHARED / 'tooling'), str(PROJECT / 'tooling')]
from integration_evidence import source_identity
from requirement_traceability_audit import build_report
from wurst_execution import verify_evidence
from validate_framework_fixture import source_hashes

out = Path(__file__).parent
execution = json.loads(gzip.decompress((out / 'wurst-results.json.gz').read_bytes()))
log = gzip.decompress((out / 'wurst-execution.log.gz').read_bytes())
verify_evidence(execution, log, execution['sourceRevision'])
identity = source_identity(PROJECT, execution['sourceRevision'])
assert execution['sourceIdentity'] == identity, 'execution is stale'
artifact = json.loads((out / 'packaged-treasures.json').read_text())
assert artifact['sourceIdentity'] == identity, 'artifact is stale'
assert artifact['candidateDefinitionsMatch'] and artifact['compiledResolver']
framework = json.loads(gzip.decompress((out / 'framework-conformance.json.gz').read_bytes()))
assert framework['status'] == 'pass'
assert framework['frameworkSources'] == source_hashes(SHARED)
for prefix in ('framework-original', 'framework-mutated'):
    result = json.loads(gzip.decompress((out / (prefix + '-results.json.gz')).read_bytes()))
    transcript = gzip.decompress((out / (prefix + '-execution.log.gz')).read_bytes())
    verify_evidence(result, transcript, execution['sourceRevision'])
trace = build_report()
parents = {'ROAD-0054', 'ROAD-0105', *(f'REQ-{i:04d}' for i in range(251, 262))}
requirements = [row for row in trace['requirements'] if row['id'].split('.')[0] in parents]
executed = [row for row in execution['tests'] if row['id'].split(':')[0] in {
    'wurst/TreasureResolutionTests.wurst', 'wurst/TreasureVectorsTests.wurst',
    'wurst/RpgInteractionTests.wurst', 'wurst/CampaignStartupTests.wurst',
    'wurst/CampaignLoadTransactionTests.wurst'}]
assert executed and all(row['status'] == 'pass' for row in executed)
report = dict(format='warcraftmap_issue465_resolution_v1', sourceIdentity=identity,
              resolutionStatus='pass', executedTests=executed,
              executionSummary={key: execution[key] for key in ('discovered', 'succeeded', 'status')},
              packagedCandidateDefinitions=artifact, frameworkStatus=framework['status'],
              requirementScope=sorted(parents), requirements=requirements,
              remainingBlockers=[
                  'Production clue-acquisition adapters and approximate/narrowed search-area presentation.',
                  'Authored reward delivery, unique-reward receipts and repeatable outcome gameplay.',
                  'Guard, hazard and encounter gameplay; stored IDs do not execute these systems.',
                  'Native Warcraft launch, real-client save/travel validation and final regional campaign artifact gates.'],
              nativeClient='not_run', releaseReady=False)
(out / 'scoped-traceability.json').write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
print(f"Scoped resolution evidence: {len(executed)} passing tests; {len(requirements)} obligations retain their broader blockers")
