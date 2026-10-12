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
BUILD = PROJECT / '_build/issue476-all'
FRAMEWORK = PROJECT.parent / 'conformance-campaign/_build'


def compress(source, name):
    value = source.read_bytes()
    (OUT / name).write_bytes(gzip.compress(value, mtime=0))
    return dict(file=name, sha256=hashlib.sha256(value).hexdigest())


def repair_coverage():
    """Verify that the smaller tested intervals still cover the full catalogue."""
    source = (PROJECT / 'wurst/WarcraftRpgRuntimeTests.wurst').read_text()
    batches = [tuple(map(int, match)) for match in re.findall(
        r'@test function generatedTreasures\w+\(\)\s+(?:(?://[^\n]*\n)\s*)*'
        r'generatedBatchRoundTrips\("treasures", (\d+), (\d+)\)', source)]
    assert sorted(batches) == [(part, 14) for part in range(14)], batches
    generated = json.loads((BUILD / 'generated/scenario-runtime.json').read_text())
    treasures = len(generated['treasureResolutionCatalog']['treasures'])
    intervals = [set(range(treasures * part // parts, treasures * (part + 1) // parts))
                 for part, parts in sorted(batches)]
    assert set.union(*intervals) == set(range(treasures))
    assert sum(map(len, intervals)) == treasures
    return dict(failure='Three generated treasure round-trip tests exceeded the pinned 20-second per-test limit in the full 544-test run.',
                previousSucceeded=541, previousDiscovered=544,
                treasureRecords=treasures, treasureBatchesBefore=4, treasureBatchesAfter=len(batches),
                treasureBatchSizes=[len(rows | {0}) for rows in intervals],
                allGeneratedRecordsCovered=True, restorePassesPerBatch=2,
                fixtureCleanup='Destroy discarded and completed fixture-owned definitions; retain the borrowed generated interaction catalogue.',
                batchOnlyAttempt='Smaller batches without cleanup still timed out and exhausted the 6 GB interpreter heap; historical logs are retained separately.',
                productionCodeChanged=False, saveFormatsChanged=False, authoredContentChanged=False,
                compilerTimeoutChanged=False, testDecoratorsFiltered=False, officialReleaseGatesChanged=False)


def main():
    records = []
    for group in ('all',):
        root = PROJECT / ('_build/issue476-' + group)
        for file in ('results.json', 'execution.log'):
            records.append(compress(root / 'evidence' / file, group + '-' + file + '.gz'))
        records.append(compress(root / 'typecheck.log', group + '-typecheck.log.gz'))
    for suffix in ('results.json', 'execution.log'):
        name = 'batch14-before-cleanup-' + suffix + '.gz'
        value = gzip.decompress((OUT / name).read_bytes())
        records.append(dict(file=name, sha256=hashlib.sha256(value).hexdigest()))
    shutil.copyfile(BUILD / 'packaged-guidance.json', OUT / 'packaged-guidance.json')
    records.append(compress(FRAMEWORK / 'conformance-report.json', 'framework-conformance.json.gz'))
    for root, prefix in [(FRAMEWORK, 'framework-original'), (FRAMEWORK / 'mutation/campaign/_build', 'framework-mutated')]:
        for file, suffix in [('results.json', 'results.json.gz'), ('execution.log', 'execution.log.gz')]:
            records.append(compress(root / 'wurst-tests' / file, prefix + '-' + suffix))
    suites = {}
    for suffix in ('python-quests', 'python-systems', 'trace-tests-final',
                   'release-tests', 'campaign-quests', 'treasure-repair'):
        path = REPO / '_build' / ('issue476-' + suffix + '.log')
        log = path.read_text()
        match = re.search(r'Ran (\d+) tests? in .*\n\nOK\b', log)
        assert match, path
        suites[suffix] = dict(passed=int(match[1]), **compress(path, suffix + '.log.gz'))
    for suffix in ('framework-final', 'traceability', 'boundary', 'release-audit'):
        records.append(compress(REPO / '_build' / ('issue476-' + suffix + '.log'), suffix + '.log.gz'))
    subprocess.run([sys.executable, str(OUT / 'report.py')], check=True)
    scoped = json.loads((OUT / 'scoped-traceability.json').read_text())
    result = dict(format='warcraftmap_issue476_validation_v1', sourceIdentity=scoped['sourceIdentity'],
                  outcome='pass', repair=repair_coverage(), wurst=scoped['executionSummary'], pythonSuites=suites,
                  pythonTotal=sum(suite['passed'] for suite in suites.values()),
                  toolchain=json.loads((BUILD / 'evidence/results.json').read_text())['compiler'],
                  standardLibraryRevision=subprocess.check_output(
                      ['git', '-C', str(REPO / '_build/issue476-tools/wurst-stdlib'), 'rev-parse', 'HEAD'], text=True).strip(),
                  transcriptHashes=records, nativeClient='not_run', releaseReady=False,
                  environment='Existing worktree-local pinned compiler/Java and cached standard library. No containers, global tooling changes or services used during validation repair.',
                  commands=dict(execution='python3 reports/issue-476/validate.py --grill <local-offline-grill> --group all --build-dir _build/issue476-all --package',
                                framework='PATH=<local-offline-grill-directory>:$PATH python3 ../_shared/tooling/validate_framework_fixture.py ../conformance-campaign',
                                traceability='python3 tooling/requirement_traceability_audit.py --write --check'))
    (OUT / 'validation.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')


if __name__ == '__main__':
    main()
