#!/usr/bin/env python3
"""Verify executed exact layers and same-source compiled tradition definitions."""
import argparse
import json
from pathlib import Path
import re
import sys
import tempfile

PROJECT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(PROJECT / 'tooling'), str(PROJECT.parent / '_shared/tooling')]
import requirement_traceability_audit as scenario
import requirement_traceability as trace
from integration_evidence import source_identity, verify_execution_coverage
from resolution_oracle import verify_vectors
from warcraft_campaign import MpqReader
from wurst_execution import source_revision

RESOLUTION = ('REQ-0155.02', 'REQ-0156.01', 'REQ-0156.02', 'REQ-0157.02',
              'REQ-0160.01', 'REQ-0160.02', 'REQ-0161.01', 'REQ-0162.01',
              'REQ-0163.01', 'REQ-0163.02')
EARNED = ('ROAD-0052.01', 'REQ-0154.01', 'REQ-0158.01', 'REQ-0164.01')
PENDING = ('REQ-0154.02', 'REQ-0155.01', 'REQ-0157.01', 'REQ-0158.02',
           'REQ-0158.03', 'REQ-0159.01')


def compiled_definitions(script, definitions):
    calls = trace.lua_calls(script)
    # Inspect real compiled call expressions: comments, strings, declarations
    # and the copied runtime JSON cannot establish executable definitions.
    found = {}
    for method, count in (('coefficient', 3), ('milestone', 5)):
        pattern = re.compile(r'\b[\w.]*TraditionDefinition[\w]*' + method +
                             r'[\w]*\s*\(\s*[^,]+,\s*' +
                             r',\s*'.join([r'("(?:\\.|[^"\\])*")'] * count) +
                             # The pinned stacktrace option appends diagnostic
                             # context after the authored constructor arguments.
                             r'(?:,\s*"when calling ' + method + r' in [^"\\]*")?\s*\)')
        found[method] = {tuple(json.loads(arg) for arg in match.groups())
                         for call in calls if (match := pattern.fullmatch(call))}
    expected_coefficients = {(c['attributeId'], str(c['numerator']), str(c['denominator']))
                             for t in definitions['traditions'] for c in t['coefficients']}
    expected_milestones = {(m['id'], str(m['threshold']), m['effect']['effectId'],
                           m['effect']['mode'], m['effect']['replacesEffectId'] or '')
                          for t in definitions['traditions'] for m in t['milestones']}
    assert found['coefficient'] == expected_coefficients, found
    assert found['milestone'] == expected_milestones, found
    return {key: sorted(rows) for key, rows in found.items()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--artifact', type=Path, required=True)
    parser.add_argument('--execution-dir', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    revision = source_revision(PROJECT)
    identity = source_identity(PROJECT, revision)
    execution = trace.load(args.execution_dir / 'results.json')
    transcript = (args.execution_dir / 'execution.log').read_bytes()
    coverage = verify_execution_coverage(execution, transcript, PROJECT, revision)
    assert coverage['military_tradition_resolution']
    report = scenario.build_report(args.artifact, execution, transcript, revision)
    scenario.write_report(report, args.output_dir / 'requirement-traceability')
    assert not report['executionErrors'], report['executionErrors']
    requirements = {row['id']: row for row in report['requirements']}
    for ident in RESOLUTION + EARNED:
        assert requirements[ident]['status'] == 'pass', requirements[ident]
    assert all(requirements[ident]['status'] != 'pass' for ident in PENDING)
    assert not report['candidateReady'] and report['blockerCount'] > 0
    definitions = trace.load(PROJECT / 'scenario/military-traditions.json')
    vectors = verify_vectors(definitions, transcript.decode())
    archive = MpqReader(args.artifact)
    checked = {}
    blockers = []
    with tempfile.TemporaryDirectory(dir=args.output_dir) as temporary:
        for physical in trace.load(PROJECT / 'physical-maps.json')['physicalMaps']:
            if physical.get('bootstrap'):
                continue
            path = Path(temporary) / (physical['id'] + '.w3x')
            path.write_bytes(archive.read(physical['packagePath']))
            nested = MpqReader(path)
            assert json.loads(nested.read('runtime/build-identity.json')) == identity
            runtime = json.loads(nested.read('runtime/scenario-runtime.json'))
            assert runtime['militaryTraditions'] == definitions
            blockers = runtime['militaryTraditionIntegrationBlockers']
            assert len(blockers) == sum(len(t['coefficients']) + len(t['milestones']) for t in definitions['traditions'])
            checked[physical['id']] = compiled_definitions(nested.read('war3map.lua').decode(), definitions)
    required_tests = {
        'installedLandCallbacksDeliverExactResolvedLayers', 'installedNavalCallbacksDeliverExactResolvedLayers',
        'everyMilestoneBoundaryKeepsAdjacentContinuousProgression',
        'resolvedLayersFollowControlCategoriesActivationAndInspection',
        'milestoneReplacementRetainsUnrelatedEarlierEffectsAndExactGrowth',
        'nativeTypedLayerReplacementKeepsUnrelatedModifiersAndLoadCheckpoint',
        'exactRationalValuesKeepSignsFractionsAndExpandableCoefficients',
        'milestoneThresholdsBeyondNativePrecisionRemainDistinct',
        'earnedTraditionAndConsumedLossesSurviveFreshCampaignAndFailedRestore',
        'everyLegacyMilitaryIntegerVersionMigratesThroughFreshCampaignCodec',
        'malformedExactExperienceIsRejectedByCampaignLoadBeforeMutation',
    }
    assert required_tests <= {row['id'].rsplit(':', 1)[1] for row in execution['tests'] if row['status'] == 'pass'}
    result = {**identity, 'status': 'pass', 'scope': 'exact typed resolution, delivery, inspection and reconstruction',
              'requirements': RESOLUTION + EARNED, 'remainingObligations': PENDING,
              'artifactSha256': report['artifact']['sha256'], 'executionLogSha256': execution['logSha256'],
              'productionJourneys': coverage['military_tradition_resolution'],
              'compiledDefinitionsByMap': checked, **vectors,
              'gameplayConsumerBlockers': blockers, 'requiredTests': sorted(required_tests),
              'militarySchemaVersion': 8, 'supportedMilitaryVersions': list(range(1, 9)),
              'headlessTraditionSchemaVersion': 2, 'supportedCampaignVersions': list(range(1, 10)),
              'remainingPublicationBlockers': report['blockerCount'], 'candidateReady': False,
              'realClientExecuted': False, 'releaseCandidate': False,
              'releaseStatus': 'blocked_pending_real_forsaken_kingdom_launch_smoke'}
    (args.output_dir / 'scoped-evidence.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print('PASS: executed rational oracle, typed lifecycle and same-source compiled definitions; gameplay consumers and native launch remain open')


if __name__ == '__main__':
    main()
