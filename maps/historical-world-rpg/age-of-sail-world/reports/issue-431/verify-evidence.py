#!/usr/bin/env python3
"""Bind historical-research receipts and compiled registrations to current inputs."""
import argparse
from decimal import Decimal
import json
from pathlib import Path
import re
import sys

PROJECT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(PROJECT / 'tooling'), str(PROJECT.parent / '_shared/tooling')]
import requirement_traceability_audit as scenario
import requirement_traceability as trace
from integration_evidence import source_identity
from wurst_execution import source_revision
from package_wurst_map import research_time_cost


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--artifact', type=Path, required=True)
    parser.add_argument('--execution-dir', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--source-revision')
    args = parser.parse_args()
    revision = source_revision(PROJECT, args.source_revision)
    identity = source_identity(PROJECT, revision)
    evidence = trace.load(args.execution_dir / 'results.json')
    transcript = (args.execution_dir / 'execution.log').read_bytes()
    report = scenario.build_report(args.artifact, evidence, transcript, revision)
    scenario.write_report(report, args.output_dir / 'requirement-traceability')
    assert not report['executionErrors'], report['executionErrors']
    scoped = {'REQ-0037.01', 'REQ-0038.01'}
    rows = [row for row in report['requirements'] if row['id'] in scoped]
    assert {row['id'] for row in rows} == scoped
    assert all(row['status'] == 'pass' for row in rows), [
        (row['id'], row['blockerClasses']) for row in rows]
    # Costing is only one part of the broad technology/institutions roadmap item.
    road = next(row for row in report['requirements'] if row['id'] == 'ROAD-0045.01')
    assert road['status'] == 'fail'
    dependency = next(row for row in report['dependencies'] if row['id'] == 'DEP-clock-research')
    assert dependency['status'] == 'fail'
    maps = [{**row, 'bootstrap': row.get('bootstrap', False)} for row in
            trace.load(PROJECT / 'physical-maps.json')['physicalMaps']]
    _, payloads, errors = trace.inspect_artifact(args.artifact, maps)
    assert not errors, errors
    registrations = {}
    world = json.loads((PROJECT / 'scenario/world/world.json').read_text(), parse_float=Decimal)
    expected = {row['id']: research_time_cost(row['timeCost'], row['id'])
                for row in world['technologies'] + world['institutions']}
    cost_definitions = {}
    patterns = rows[0]['mapping']['artifact']['callPatterns']
    for physical in maps:
        packaged_identity = json.loads(payloads[physical['id']]['members']['runtime/build-identity.json'])
        assert packaged_identity == identity, (physical['id'], packaged_identity, identity)
        if physical['bootstrap']:
            continue
        calls = trace.compiled_calls(payloads[physical['id']])
        registrations[physical['id']] = {}
        for pattern in patterns:
            matches = [call for call in calls if re.match(pattern, call)]
            assert matches, (physical['id'], pattern)
            registrations[physical['id']][pattern] = {'count': len(matches), 'example': matches[0]}
        # The pinned optimizer inlines constructors. Check real literal field
        # assignments, excluding declarations, comments and quoted diagnostics.
        fragments = trace.compiled_fragments(payloads[physical['id']])
        found = {}
        ident = variable = None
        fields = ('historicalYear', 'baseCost', 'aheadOfTimeCostMultiplier', 'additionalMultiplierPerYearAhead')
        for fragment in fragments:
            match = re.fullmatch(r'RuntimeTechnology_id_storage\[([^\]]+)\]\s*=\s*("[^"]+")\s*', fragment)
            if match:
                variable, ident = match[1], json.loads(match[2])
                assert ident not in found, (physical['id'], ident)
                found[ident] = {}
            if ident is not None:
                for field in fields:
                    match = re.fullmatch(r'RuntimeTechnology_' + field + r'_storage\[' + re.escape(variable)
                                         + r'\]\s*=\s*("[^"]+"|-?\d+)\s*', fragment)
                    if match:
                        assert field not in found[ident], (physical['id'], ident, field)
                        found[ident][field] = json.loads(match[1])
        actual = {ident: tuple(values[field] for field in fields) for ident, values in found.items()}
        assert actual == expected, physical['id']
        cost_definitions[physical['id']] = {'technologies': len(world['technologies']),
                                           'institutions': len(world['institutions']),
                                           'completeAuthoredTimeCosts': len(actual)}
    for catalogue in ('technologies', 'institutions'):
        row = next(row for row in report['catalogues'] if row['id'] == catalogue)
        assert row['status'] == 'pass', row['failures']
    receipts = [json.loads(line.removeprefix('TRACEABILITY '))
                for line in transcript.decode().splitlines() if line.startswith('TRACEABILITY ')]
    receipts = [row for row in receipts if row['requirement'] in scoped | {'ROAD-0045.01'}]
    assert len(receipts) == 12
    assert {(row['requirement'], row['case']) for row in receipts} == {
        (requirement, case) for requirement in scoped | {'ROAD-0045.01'}
        for case in ('success', 'failure', 'stale', 'replay')}
    assert not report['candidateReady'] and report['blockerCount'] > 0
    result = {**identity, 'status': 'pass',
              'artifactSha256': report['artifact']['sha256'],
              'requirements': [{'id': row['id'], 'status': row['status']} for row in rows],
              'roadmapScope': 'ROAD-0045 historical-cost correction only; broader integration remains blocked',
              'receipts': len(receipts), 'compiledRegistrations': registrations,
              'compiledCostDefinitions': cost_definitions,
              'candidateReady': False, 'remainingPublicationBlockers': report['blockerCount'],
              'releaseStatus': 'blocked_pending_real_forsaken_kingdom_launch_smoke',
              'realClientExecuted': False}
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / 'scoped-evidence.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print('PASS: historical research receipts, generated catalogues and compiled registrations; unrelated blockers retained')


if __name__ == '__main__':
    main()
