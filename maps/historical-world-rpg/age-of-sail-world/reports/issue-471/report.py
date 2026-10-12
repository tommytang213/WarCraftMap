"""Verify same-source visit knowledge evidence and retain downstream blockers."""
import gzip
import json
from pathlib import Path
import sys

PROJECT = Path(__file__).resolve().parents[2]
SHARED = PROJECT.parent / '_shared'
sys.path[:0] = [str(SHARED / 'tooling'), str(PROJECT / 'tooling')]
from integration_evidence import source_identity
from map_knowledge import knowledge_catalog
from requirement_traceability_audit import build_report
from validate_framework_fixture import source_hashes
from wurst_execution import verify_evidence

out = Path(__file__).parent
execution = json.loads(gzip.decompress((out / 'wurst-results.json.gz').read_bytes()))
log = gzip.decompress((out / 'wurst-execution.log.gz').read_bytes())
verify_evidence(execution, log, execution['sourceRevision'])
identity = source_identity(PROJECT, execution['sourceRevision'])
assert execution['sourceIdentity'] == identity, 'execution is stale'
artifact = json.loads((out / 'packaged-knowledge.json').read_text())
assert artifact['sourceIdentity'] == identity, 'package is stale'
assert artifact['catalogueDefinitionsMatch'] and artifact['compiledKnowledgeAndCommands']
catalog = knowledge_catalog(PROJECT)
assert artifact['settlements'] == len(catalog['settlements'])
assert artifact['regions'] == len(catalog['regions'])
framework = json.loads(gzip.decompress((out / 'framework-conformance.json.gz').read_bytes()))
assert framework['status'] == 'pass'
assert framework['frameworkSources'] == source_hashes(SHARED), 'framework is stale'
for prefix in ('framework-original', 'framework-mutated'):
    result = json.loads(gzip.decompress((out / (prefix + '-results.json.gz')).read_bytes()))
    transcript = gzip.decompress((out / (prefix + '-execution.log.gz')).read_bytes())
    verify_evidence(result, transcript, execution['sourceRevision'])

cases = {
    'validatedQuestlessVisitFeedsRegisteredFilteredMapAndExactFocus': 'Validated questless visits, named world/regional filtering, exact focus, pause ownership and unchanged party/orders/context.',
    'wrongMapDistantStaleAndMalformedInteractionsNeverInventVisits': 'Wrong-map, distant, stale, malformed and unavailable interactions reject without knowledge; aliases record canonical IDs.',
    'multipleVisitsSurviveFailedSaveFreshLoadPhysicalTravelAndReturn': 'Multiple visits, failed storage, fresh services, travel, return and preserved treasure resolution/precision.',
    'remoteCommandAndReturnPreserveKnowledgeWithoutDestinationVisitOrRights': 'Physical remote command and return preserve absent home-party coordinates and do not invent visits or command rights.',
    'legacyDiscoveryPreservesOnlyRecordedIdsAndCurrentMalformedKnowledgeRejects': 'Schemas 1–9 preserve recorded IDs; empty legacy discovery invents no visits; invalid and duplicate current records reject.',
    'lateRestorationFailureRollsBackKnowledgeAndRetainsMapPauseOwnership': 'Late reconstruction failure restores knowledge/projections and retains modal/manual pause ownership.',
}
tests = {row['id']: row for row in execution['tests']}
executed = []
for name, purpose in cases.items():
    row = tests['wurst/VisitKnowledgeTests.wurst:' + name]
    assert row['status'] == 'pass'
    executed.append(dict(**row, validates=purpose))
parents = {'REQ-0287', 'REQ-0288', 'REQ-0293', 'REQ-0294', 'ROAD-0063'}
trace = build_report()
requirements = [row for row in trace['requirements'] if row['parent'] in parents]
assert len(requirements) == 6
closed_portions = {
    'REQ-0287.01': 'Validated settlement visits, including questless interactions and local quest acceptance, persist as exact knowledge.',
    'REQ-0288.01': 'World and regional settlement listings expose only authorized knowledge; invalid requests preserve the current view.',
    'REQ-0293.01': 'General region discovery reveals neither unvisited settlements nor hidden points of interest.',
    'REQ-0294.01': 'The registered map focus action accepts known named settlements without changing party, orders or command context.',
    'ROAD-0063.01': 'Region and visited-settlement authority survives saves, fresh reconstruction, physical travel, remote command and return.',
}
report = dict(
    format='warcraftmap_issue471_visit_knowledge_v1', sourceIdentity=identity,
    visitKnowledgeStatus='pass',
    scope='Persistent region and exact visited-settlement knowledge, filtering, and registered known-settlement focus only.',
    authority='DiscoveryKnowledge in PlayableCampaignState, schema 10 discovery v1. Scenario map catalogue supplies names and membership. Command rights and RPG treasure authority remain separate.',
    entryPoints=['/interact <local-location-id>', '/turnin <quest-id> <hero-id>', '/map world', '/map <region-id>', '/map focus <settlement-id>', '/map close'],
    referenceParity='tests/test_visit_knowledge.py compares names/membership and the registered-command cases with engine/map_discovery.py; all scenario settlements are represented, including those without map geometry.',
    executedTests=executed,
    executionSummary={key: execution[key] for key in ('discovered', 'succeeded', 'status')},
    packagedDefinitions=artifact, frameworkStatus=framework['status'],
    requirementScope=sorted(parents),
    closedPortions=[dict(id=ident, status='pass', scope=scope) for ident, scope in closed_portions.items()],
    broaderRequirements=requirements,
    remainingBlockers=[
        'Quest-to-map guidance, quest return destinations and route breadcrumbs.',
        'Production clue acquisition and broader search-area/precision presentation; REQ-0288.02 remains downstream.',
        'Other treasure gameplay obligations remain open; #465 resolution and earned precision are preserved.',
        'Frame-based map UI (#440) remains deferred.',
        'Native Warcraft launch, real-client validation and final regional campaign artifact gates.'],
    nativeClient='not_run', releaseReady=False)
(out / 'scoped-traceability.json').write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
print(f'Visit knowledge scope: {len(executed)} production tests; {artifact["settlements"]} packaged settlement definitions; downstream/native blockers retained')
