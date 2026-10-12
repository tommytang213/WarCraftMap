#!/usr/bin/env python3
"""Retain scoped evidence without clearing broader consumer/release blockers."""
import gzip
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

PROJECT = Path(__file__).resolve().parents[2]
REPO = PROJECT.parents[2]
REPORT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT.parent / '_shared/tooling'))
from integration_evidence import source_identity
from wurst_execution import PINNED_COMPILER_SHA256


def write(name, value):
    (REPORT / name).write_text(json.dumps(value, sort_keys=True, indent=2) + '\n')


def main():
    execution_root = PROJECT / '_build/issue470-verified'
    execution = json.loads((execution_root / 'results.json').read_text())
    compiled = json.loads((REPORT / 'compiled-items.json').read_text())
    framework = json.loads((PROJECT.parent / 'conformance-campaign/_build/conformance-report.json').read_text())
    identity = source_identity(PROJECT, execution['sourceRevision'])
    assert execution['sourceIdentity'] == compiled['sourceIdentity'] == identity
    assert execution['status'] == compiled['status'] == framework['status'] == 'pass'
    assert execution['succeeded'] == execution['discovered'] and not execution['errors']
    assert execution['compiler']['sha256'] == PINNED_COMPILER_SHA256
    current_path = PROJECT / 'reports/traceability/requirements.json'
    baseline = json.loads(subprocess.check_output(['git', 'show', 'HEAD:' + str(current_path.relative_to(REPO))], cwd=REPO))
    current = json.loads(current_path.read_text())
    parents = [f'REQ-{n:04}' for n in range(71, 78)] + ['ROAD-0133']
    ids = {row['id'] for row in current['requirements'] if row['parent'] in parents}
    unrelated = lambda report: sorted(json.dumps(row, sort_keys=True) for row in report['blockers'] if row['id'] not in ids)
    assert unrelated(baseline) == unrelated(current), 'unrelated publication blockers changed'
    write('scoped-traceability.json', {
        'sourceIdentity': identity,
        'scope': 'Complete item definition retention, wearer comparison and typed equipment delivery only.',
        'status': 'pass', 'obligations': sorted(ids),
        'execution': {'discovered': execution['discovered'], 'succeeded': execution['succeeded']},
        'compiledDefinitions': {key: compiled[key] for key in ('items', 'majorStats', 'effectIds', 'conditionalDescriptors', 'negativeControls')},
        'downstream': {
            'itemGameplayConsumers': 'blocked_pending_item_gameplay_bindings',
            'conditionalActivation': 'blocked_pending_condition_consumers',
            'setGameplayConsumers': 'blocked_pending_gameplay_effect_bindings',
            'availabilityIntegration': 'Retained requirements do not close merchant/context integrations.',
            'nativeClient': 'blocked_pending_real_forsaken_kingdom_launch_smoke',
        },
        'sourceInventory': {'incomingPublicationBlockers': baseline['blockerCount'],
                            'publicationBlockers': current['blockerCount'],
                            'unrelatedBlockerCount': len(unrelated(current)), 'unrelatedBlockersUnchanged': True},
        'remainingParentObligationBlockers': [row for row in current['blockers'] if row['id'] in ids],
        'releaseReady': False,
    })
    logs = REPO / '_build/issue-470'
    paths = [execution_root / 'execution.log', execution_root / 'results.json']
    paths += [logs / name for name in ('equipment-python.log', 'item-definitions-python.log', 'inventory.log',
              'persistence.log', 'campaign-save-python.log', 'framework-python.log', 'packaging-python.log',
              'traceability.log', 'traceability-tests.log', 'framework-pinned.log', 'artifact-verified.log')]
    retained = {}
    python_tests = {}
    for path in paths:
        value = path.read_bytes()
        if path.name in {'equipment-python.log', 'item-definitions-python.log', 'inventory.log', 'persistence.log',
                         'campaign-save-python.log', 'framework-python.log', 'packaging-python.log', 'traceability-tests.log'}:
            passed = re.search(rb'Ran ([1-9][0-9]*) tests? in [^\n]+\n\nOK(?:\n|$)', value)
            assert passed, f'passing Python test summary is missing: {path}'
            python_tests[path.name] = int(passed[1])
        destination = REPORT / (path.name + '.gz')
        destination.write_bytes(gzip.compress(value, mtime=0))
        retained[destination.name] = {'uncompressedSha256': hashlib.sha256(value).hexdigest(),
                                      'archiveSha256': hashlib.sha256(destination.read_bytes()).hexdigest()}
    write('validation.json', {
        'status': 'pass', 'sourceIdentity': identity, 'compiler': execution['compiler'],
        'wurst': {'discovered': execution['discovered'], 'succeeded': execution['succeeded']},
        'pythonTests': python_tests,
        'framework': {'status': framework['status'], 'originalArchiveSha256': framework['originalArchiveSha256'],
                      'mutatedArchiveSha256': framework['mutatedArchiveSha256']},
        'compiledDefinitions': compiled, 'retainedEvidence': retained,
        'nativeClient': 'not_run', 'releaseReady': False,
    })


if __name__ == '__main__':
    main()
