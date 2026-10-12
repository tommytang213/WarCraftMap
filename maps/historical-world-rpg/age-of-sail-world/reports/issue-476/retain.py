"""Retain final local evidence after validate.py and framework validation pass."""
import gzip
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

OUT = Path(__file__).resolve().parent
PROJECT = OUT.parents[1]
REPO = PROJECT.parents[2]
BUILD = PROJECT / '_build/issue476-navigation'
FRAMEWORK = PROJECT.parent / 'conformance-campaign/_build'


def compress(source, name):
    value = source.read_bytes()
    (OUT / name).write_bytes(gzip.compress(value, mtime=0))
    return dict(file=name, sha256=hashlib.sha256(value).hexdigest())


def main():
    records = []
    for group in ('navigation', 'remaining', 'rpg'):
        root = PROJECT / ('_build/issue476-' + group)
        for file in ('results.json', 'execution.log'):
            records.append(compress(root / 'evidence' / file, group + '-' + file + '.gz'))
        records.append(compress(root / 'typecheck.log', group + '-typecheck.log.gz'))
    shutil.copyfile(BUILD / 'packaged-guidance.json', OUT / 'packaged-guidance.json')
    records.append(compress(FRAMEWORK / 'conformance-report.json', 'framework-conformance.json.gz'))
    for root, prefix in [(FRAMEWORK, 'framework-original'), (FRAMEWORK / 'mutation/campaign/_build', 'framework-mutated')]:
        for file, suffix in [('results.json', 'results.json.gz'), ('execution.log', 'execution.log.gz')]:
            records.append(compress(root / 'wurst-tests' / file, prefix + '-' + suffix))
    suites = {}
    for suffix, count in [('python-quests', 30), ('python-systems', 58), ('trace-tests-final', 49),
                          ('release-tests', 10), ('campaign-quests', 7)]:
        path = REPO / '_build' / ('issue476-' + suffix + '.log')
        log = path.read_text()
        assert re.search(rf'Ran {count} tests? in .*\n\nOK\b', log), path
        suites[suffix] = dict(passed=count, **compress(path, suffix + '.log.gz'))
    for suffix in ('framework-final', 'traceability', 'boundary', 'release-audit'):
        records.append(compress(REPO / '_build' / ('issue476-' + suffix + '.log'), suffix + '.log.gz'))
    subprocess.run([sys.executable, str(OUT / 'report.py')], check=True)
    scoped = json.loads((OUT / 'scoped-traceability.json').read_text())
    result = dict(format='warcraftmap_issue476_validation_v1', sourceIdentity=scoped['sourceIdentity'],
                  outcome='pass', wurst=scoped['executionSummary'], pythonSuites=suites,
                  pythonTotal=sum(suite['passed'] for suite in suites.values()),
                  toolchain=json.loads((BUILD / 'evidence/results.json').read_text())['compiler'],
                  standardLibraryRevision=subprocess.check_output(
                      ['git', '-C', str(REPO / '_build/issue476-tools/wurst-stdlib'), 'rev-parse', 'HEAD'], text=True).strip(),
                  transcriptHashes=records, nativeClient='not_run', releaseReady=False,
                  environment='Pinned cached compiler/Java copied from a stopped container without worktree mounts; validation ran locally with cached standard library. No global tooling changes.',
                  commands=dict(execution='python3 reports/issue-476/validate.py --grill <local-offline-grill> --group GROUP --build-dir _build/issue476-GROUP (GROUP=navigation,remaining,rpg; --package on navigation)',
                                framework='PATH=<local-offline-grill-directory>:$PATH python3 ../_shared/tooling/validate_framework_fixture.py ../conformance-campaign',
                                traceability='python3 tooling/requirement_traceability_audit.py --write --check'))
    (OUT / 'validation.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')


if __name__ == '__main__':
    main()
