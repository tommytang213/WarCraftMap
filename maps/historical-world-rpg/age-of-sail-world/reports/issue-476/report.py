"""Verify source-bound execution/package/framework evidence and write scoped status."""
import gzip
import json
from pathlib import Path
import sys

OUT = Path(__file__).resolve().parent
PROJECT = OUT.parents[1]
SHARED = PROJECT.parent / '_shared'
sys.path[:0] = [str(SHARED / 'tooling'), str(PROJECT / 'tooling'), str(OUT)]
from integration_evidence import source_identity, verify_execution_coverage
from requirement_traceability_audit import build_report
from validate_framework_fixture import source_hashes
from wurst_execution import verify_evidence
from parity import verify_transcript

GROUPS = ('all',)


def executions():
    """Require one complete run through the repository's production verifier.

    No test-decorator filtering or merged partial transcripts: the same verifier
    used by release validation binds every discovered test and production probe
    to current authored inputs and the pinned compiler.
    """
    report = json.loads(gzip.decompress((OUT / 'all-results.json.gz').read_bytes()))
    log = gzip.decompress((OUT / 'all-execution.log.gz').read_bytes())
    coverage = verify_execution_coverage(report, log, PROJECT, report['sourceRevision'])
    summary = {key: report[key] for key in ('discovered', 'succeeded', 'status')}
    summary['strategy'] = 'single complete suite with unchanged test decorators and compiler timeout'
    return [report], [log], report['tests'], coverage, summary


def main():
    reports, transcripts, tests, coverage, summary = executions()
    execution, log = reports[0], transcripts[0]
    revision = execution['sourceRevision']
    verify_evidence(execution, log, revision)
    identity = source_identity(PROJECT, revision)
    assert execution['sourceIdentity'] == identity, 'execution is stale'
    assert all(coverage.values()), 'a configured production journey was not executed'
    vectors = verify_transcript(log.decode())
    package = json.loads((OUT / 'packaged-guidance.json').read_text())
    assert package['sourceIdentity'] == identity, 'package is stale'
    assert package['generatedDefinitionsMatch'] and package['localMarkerNative'] and package['showOnMapRegistration'] and package['compiledGuidanceDefinitionsMatch']
    framework = json.loads(gzip.decompress((OUT / 'framework-conformance.json.gz').read_bytes()))
    assert framework['status'] == 'pass' and framework['frameworkSources'] == source_hashes(SHARED)
    for prefix in ('framework-original', 'framework-mutated'):
        result = json.loads(gzip.decompress((OUT / (prefix + '-results.json.gz')).read_bytes()))
        transcript = gzip.decompress((OUT / (prefix + '-execution.log.gz')).read_bytes())
        verify_evidence(result, transcript, revision)
    parents = {f'REQ-028{x}' for x in range(1, 7)} | {'REQ-0295', 'ROAD-0064'}
    trace = build_report()
    navigation_tests = [row for row in tests if 'QuestNavigationTests.wurst:' in row['id']]
    assert len(navigation_tests) == 10 and all(row['status'] == 'pass' for row in navigation_tests)
    report = dict(
        format='warcraftmap_issue476_quest_navigation_v1', sourceIdentity=identity,
        status='pass', scope='Active-stage and return guidance: exact, region-only, hidden and earned settlement precision.',
        authority='Existing RPG journal tracking/progress and schema-10 discovery knowledge; focus and local effects are disposable projections. No durable format change.',
        entryPoints=['/accept QUEST', '/interact LOCATION', '/queststage QUEST STAGE', '/track QUEST',
                     '/showonmap QUEST', '/turnin QUEST HERO', '/map close', '/save N', '/load N'],
        productionTests=navigation_tests, headlessParityVectors=vectors,
        executionSummary=summary,
        executionGroups={group: {key: result[key] for key in ('discovered', 'succeeded', 'status')}
                         for group, result in zip(GROUPS, reports)},
        productionEntryCoverage=dict(systems=len(coverage), missing=[], questNavigation=coverage['quest_navigation']),
        packagedEvidence=package, frameworkStatus=framework['status'],
        requirementScope=sorted(parents),
        closedPortions=[
            dict(id='REQ-0281.01', scope='Authored active-objective and return stable IDs drive derived focus; giver/turn-in definitions stay authoritative.'),
            dict(id='REQ-0282.01', scope='Separate registered/documented Show on Map and Track actions validate availability before mutation or pause.'),
            dict(id='REQ-0283.01', scope='Scoped exact or region-only regional focus without ordinary unknown-region authorization or unrelated reveals.'),
            dict(id='REQ-0285.01', scope='Replaceable exact local marker only on the loaded physical party map.'),
            dict(id='REQ-0286.01', scope='Retain authored return guidance until validated, successful turn-in; restoration does not replay rewards.'),
            dict(id='REQ-0295.01', scope='Party positions, orders, discovery and remote-command context/rights remain unchanged.'),
            dict(id='ROAD-0064.01', scope='Connect current journal presentation and active tracking to exact/regional map and local marker adapters.')],
        broaderRequirements=[row for row in trace['requirements'] if row['parent'] in parents],
        remainingBlockers=[
            'REQ-0284: discovered-transition route breadcrumbs remain downstream.',
            'Production quest clue acquisition and bounded approximate search-area rendering remain downstream; unsupported approximate actions fail closed.',
            'Earned exact knowledge for non-settlement points awaits its discovery authority.',
            'Custom frame presentation (#440) and broader ROAD-0064 journal obligations remain deferred.',
            'Native Warcraft launch (#438), native save/travel validation and broader regional campaign/release gates remain unresolved.'],
        nativeClient='not_run', releaseReady=False)
    (OUT / 'scoped-traceability.json').write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
    print(f'Quest navigation: {len(navigation_tests)} live tests, {len(vectors)} differential vectors, {summary["succeeded"]} Wurst tests; downstream/native blockers retained')


if __name__ == '__main__':
    main()
