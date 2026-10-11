#!/usr/bin/env python3
"""Retain same-source evidence without claiming unbound gameplay effects work."""
import gzip
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent / '_shared/tooling'))
from integration_evidence import source_identity
from inspect_compiled import inspect


def main():
    execution = json.loads((ROOT / '_build/wurst-tests/results.json').read_text())
    identity = source_identity(ROOT, execution['sourceRevision'])
    assert execution['status'] == 'pass', execution['errors']
    assert execution['sourceIdentity'] == identity, 'execution source mismatch'
    artifact = inspect(ROOT / '_build/release/AgeOfSailWorld.w3x')
    assert artifact['sourceIdentity'] == identity
    (OUT / 'compiled-equipment-sets.json').write_text(json.dumps(artifact, indent=2, sort_keys=True) + '\n')
    report = json.loads((ROOT / 'reports/traceability/requirements.json').read_text())
    baseline = json.loads(subprocess.check_output(['git', 'show', 'HEAD:maps/historical-world-rpg/age-of-sail-world/reports/traceability/requirements.json'], cwd=ROOT))
    unrelated = lambda r: [row for row in r['blockers'] if row['id'] != 'ROAD-0053.01']
    assert unrelated(baseline) == unrelated(report), 'unrelated blockers changed'
    tests = [row for row in execution['tests'] if Path(row['id'].split(':')[0]).name in
             {'EquipmentSetTests.wurst', 'EquipmentSetVectorsTests.wurst', 'CharacterEquipmentTests.wurst'} or
             row['id'].endswith(':rejectedLoadRetainsEquipmentContributionsOnSurvivingObjects')]
    assert all(row['status'] == 'pass' for row in tests)
    for name in ('generatedAkanTiersResolveThroughRegisteredEquipmentActions',
                 'replacingOneTypedSetLayerPreservesOtherWearersSetsAndModifiers',
                 'legacyLoadoutsRebuildAllSetIdentitiesWithoutPersistingBonuses',
                 'rejectedLoadRetainsEquipmentContributionsOnSurvivingObjects'):
        assert any(row['id'].endswith(':' + name) for row in tests), name
    assert sum('equipmentSetParity_' in row['id'] for row in tests) == 4
    scoped = {'format': 'warcraftmap_issue459_scoped_traceability_v1', 'sourceIdentity': identity,
              'scope': 'Equipment-set definition retention, wearer resolution and typed projection delivery only.',
              'requirement': 'ROAD-0053.01', 'executedTests': tests,
              'remainingBlockers': [row for row in report['blockers'] if row['id'] == 'ROAD-0053.01'],
              'sourceInventory': {'incomingPublicationBlockers': baseline['blockerCount'],
                                  'publicationBlockers': report['blockerCount'],
                                  'unrelatedBlockerCount': len(unrelated(report)), 'unrelatedBlockersUnchanged': True},
              'compiledDefinitions': 'compiled-equipment-sets.json',
              'gameplayEffects': 'blocked_pending_gameplay_effect_bindings',
              'nativeLaunch': 'blocked_pending_real_forsaken_kingdom_launch_smoke', 'releaseReady': False}
    (OUT / 'scoped-traceability.json').write_text(json.dumps(scoped, indent=2, sort_keys=True) + '\n')
    retained = []
    def retain(path, name):
        value = path.read_bytes()
        target = OUT / (name + '.gz')
        target.write_bytes(gzip.compress(value, mtime=0))
        retained.append({'path': target.name, 'sha256': hashlib.sha256(target.read_bytes()).hexdigest(),
                         'uncompressedSha256': hashlib.sha256(value).hexdigest()})
    retain(ROOT / '_build/wurst-tests/results.json', 'wurst-results.json')
    retain(ROOT / '_build/wurst-tests/execution.log', 'wurst-execution.log')
    for label in ('python-final', 'framework-final', 'diagnostic-final', 'traceability', 'trace-tests'):
        retain(ROOT / f'_build/issue459-{label}.log', label + '.log')
    python_log = (ROOT / '_build/issue459-python-final.log').read_text()
    python = re.search(r'Ran (\d+) tests in ([\d.]+)s\s+OK\b', python_log)
    assert python, 'Python checks did not pass'
    trace_tests = re.search(r'Ran (\d+) tests in ([\d.]+)s\s+OK\b',
                           (ROOT / '_build/issue459-trace-tests.log').read_text())
    assert trace_tests, 'Traceability checks did not pass after the mapping correction'
    build_log = (ROOT / '_build/issue459-diagnostic-final.log').read_text()
    assert 'errors: 0' in build_log and 'Map built.' in build_log
    framework_root = ROOT.parent / 'conformance-campaign/_build'
    framework = json.loads((framework_root / 'conformance-report.json').read_text())
    assert framework['status'] == 'pass'
    for relative, digest in framework['frameworkSources'].items():
        assert hashlib.sha256((ROOT.parent / '_shared' / relative).read_bytes()).hexdigest() == digest
    retain(framework_root / 'conformance-report.json', 'framework-conformance.json')
    for label, path in [('original', framework_root), ('mutated', framework_root / 'mutation/campaign/_build')]:
        results = json.loads((path / 'wurst-tests/results.json').read_text())
        assert results['status'] == 'pass'
        retain(path / 'wurst-tests/results.json', f'framework-{label}-results.json')
        retain(path / 'wurst-tests/execution.log', f'framework-{label}-execution.log')
    validation = {'format': 'warcraftmap_issue459_validation_v1', 'issue': 459, 'sourceIdentity': identity,
                  'implementationStatus': 'ready_for_repository_validation',
                  'pinnedWurst': {'status': 'pass', 'tests': len(execution['tests']), 'compiler': execution['compiler']},
                  'python': {'status': 'pass', 'tests': int(python[1]), 'seconds': float(python[2])},
                  'traceability': {'status': 'pass', 'tests': int(trace_tests[1]), 'seconds': float(trace_tests[2])},
                  'typecheck': 'pass', 'framework': {'status': 'pass', 'frameworkSourcesUnchanged': True},
                  'compiledDefinitions': artifact, 'durableContract': 'RPG v6 unchanged; no saved bonus records or schema migration.',
                  'gameplayEffects': 'blocked_pending_gameplay_effect_bindings', 'nativeClient': 'not_run',
                  'releaseReady': False, 'playerQARequested': False,
                  'containerUsage': 'Unstarted container extraction only, no mounts or network; all validation ran as host user.',
                  'authoritativeFinalValidation': 'Outer worker runs configured repository validation.', 'retainedEvidence': retained}
    (OUT / 'validation.json').write_text(json.dumps(validation, indent=2, sort_keys=True) + '\n')
    print(f'Retained {len(tests)} equipment tests, {len(execution["tests"])} complete Wurst tests and same-source compiled definitions.')


if __name__ == '__main__':
    main()
