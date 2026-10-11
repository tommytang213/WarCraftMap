#!/usr/bin/env python3
"""Retain scoped validation without closing compound progression obligations."""
import gzip
import hashlib
import json
import re
from pathlib import Path
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
    (OUT / 'compiled-allocations.json').write_text(json.dumps(artifact, indent=2, sort_keys=True) + '\n')
    report = json.loads((ROOT / 'reports/traceability/requirements.json').read_text())
    baseline = json.loads(subprocess.check_output(['git', 'show', 'HEAD:maps/historical-world-rpg/age-of-sail-world/reports/traceability/requirements.json'], cwd=ROOT))
    affected = {'REQ-0091.02', 'REQ-0092.01', 'ROAD-0051.01'}
    unrelated = lambda r: [b for b in r['blockers'] if b['id'] not in affected]
    assert unrelated(baseline) == unrelated(report), 'unrelated blockers changed'
    tests = [t for t in execution['tests'] if Path(t['id'].split(':')[0]).name in {'HeroAllocationTests.wurst', 'HeroAllocationVectorsTests.wurst'}]
    assert len(tests) == 12 and all(t['status'] == 'pass' for t in tests)
    mappings = json.loads((ROOT / 'scenario/traceability/mappings.json').read_text())['requirements']
    scoped = {'format': 'warcraftmap_issue457_scoped_traceability_v1', 'sourceIdentity': identity,
              'scope': 'Allocation and selected entitlements only.', 'allocationTests': tests,
              'diagnosticArtifact': 'compiled-allocations.json',
              'requirements': [{'id': ident, 'scope': mappings[ident]['scope'],
                                'remainingBlockers': [b for b in report['blockers'] if b['id'] == ident]}
                               for ident in sorted(affected)],
              'sourceInventory': {'incomingPublicationBlockers': baseline['blockerCount'],
                                  'publicationBlockers': report['blockerCount'],
                                  'unrelatedBlockerCount': len(unrelated(report)),
                                  'unrelatedBlockersUnchanged': True},
              'abilityEffects': 'blocked_pending_consumers', 'nativeClient': 'not_run', 'releaseReady': False}
    (OUT / 'scoped-traceability.json').write_text(json.dumps(scoped, indent=2, sort_keys=True) + '\n')
    retained = []
    def retain(source, name):
        value = source.read_bytes()
        target = OUT / (name + '.gz')
        target.write_bytes(gzip.compress(value, mtime=0))
        retained.append({'path': target.name, 'sha256': hashlib.sha256(target.read_bytes()).hexdigest(),
                         'uncompressedSha256': hashlib.sha256(value).hexdigest()})
    retain(ROOT / '_build/wurst-tests/results.json', 'wurst-results.json')
    retain(ROOT / '_build/wurst-tests/execution.log', 'wurst-execution.log')
    for name, file in [('targeted-python.log', ROOT / '_build/issue457-python.log'),
                       ('traceability-tests.log', ROOT / '_build/issue457-trace-tests.log'),
                       ('source-traceability.log', ROOT / '_build/issue457-traceability-final.log'),
                       ('diagnostic-build.log', ROOT / '_build/issue457-build.log'),
                       ('focused-python.log', ROOT / '_build/issue457-focused-python.log'),
                       ('framework.log', ROOT / '_build/issue457-framework.log')]:
        retain(Path(file), name)
    python = {}
    for label, log in [('targeted', ROOT / '_build/issue457-python.log'),
                       ('traceability', ROOT / '_build/issue457-trace-tests.log'),
                       ('focused', ROOT / '_build/issue457-focused-python.log')]:
        text = log.read_text()
        match = re.search(r'Ran (\d+) tests in ([\d.]+)s\s+OK\b', text)
        assert match, f'{label} Python tests did not pass'
        python[label] = {'status': 'pass', 'tests': int(match[1]), 'seconds': float(match[2])}
    typecheck = ROOT / '_build/compile/_build/issue457-grill-typecheck.log'
    assert 'errors: 0' in typecheck.read_text()
    retain(typecheck, 'wurst-typecheck.log')
    retain(ROOT / '_build/issue457-framework-boundary.log', 'framework-boundary.log')
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
    validation = {'format': 'warcraftmap_issue457_validation_v1', 'issue': 457,
                  'sourceIdentity': identity, 'implementationStatus': 'ready_for_repository_validation',
                  'pinnedWurst': {'status': 'pass', 'tests': len(execution['tests']), 'compiler': execution['compiler']},
                  'python': python, 'typecheck': 'pass',
                  'diagnosticArtifact': artifact, 'framework': {'status': 'pass', 'frameworkSourcesUnchanged': True},
                  'durableContract': 'RPG v6 unchanged; existing supported legacy migrations retained without point grants, charges or refunds.',
                  'nativeClient': 'not_run', 'abilityEffects': 'blocked_pending_consumers',
                  'releaseReady': False, 'playerQARequested': False,
                  'containerUsage': 'Pinned toolchain extraction only, no host mounts or network; validation ran as host user.',
                  'authoritativeFinalValidation': 'Outer worker runs configured repository validation.',
                  'retainedEvidence': retained}
    (OUT / 'validation.json').write_text(json.dumps(validation, indent=2, sort_keys=True) + '\n')
    print(f"Retained {len(tests)} allocation tests, {len(execution['tests'])} complete Wurst tests and same-source diagnostic artifact.")


if __name__ == '__main__':
    main()
