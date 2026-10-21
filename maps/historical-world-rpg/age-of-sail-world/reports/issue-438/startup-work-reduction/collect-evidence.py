#!/usr/bin/env python3
"""Retain scoped source/build/model evidence; no player artifact or native claim."""
from datetime import datetime, timezone
from pathlib import Path
import gzip
import hashlib
import json
import shutil

BASE = Path('/workspace/scratch/243ebc79fa0a')
WORK = BASE / 'validation-536/continue-fix'
PROJECT = BASE / 'WarCraftMap/maps/historical-world-rpg/age-of-sail-world'
OUT = PROJECT / 'reports/issue-438/startup-work-reduction'
REVISION = '264b34c9a0762bdadda377fb10cb44a63af33052'
SOURCE = 'b69fd4f0100a2a9f5f5e4c266e4e68ee3e35af3dc5be91d010be9b325e97b62d'
ENCODINGS = {}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def copy(source, destination=None, compress=False):
    source = Path(source)
    destination = destination or source.relative_to(WORK).as_posix()
    target = OUT / destination
    assert source.is_file() and not source.is_symlink(), source
    assert not target.exists(), target
    target.parent.mkdir(parents=True, exist_ok=True)
    original = source.read_bytes()
    target.write_bytes(gzip.compress(original, compresslevel=9, mtime=0) if compress else original)
    ENCODINGS[destination] = 'gzip_mtime_0' if compress else 'identity'


def copy_existing(directory, names):
    for name in names:
        source = WORK / directory / name
        if source.is_file():
            copy(source)


def main():
    assert not OUT.exists(), 'Preserve previous report pack'
    receipt = json.loads((WORK / 'full-wurst-tests/run-receipt.json').read_text())
    assert receipt['status'] == 'pass' and receipt['succeeded'] == receipt['discovered'] == 671
    assert receipt['sourceIdentity'] == {'sourceRevision': REVISION, 'sourceTreeSha256': SOURCE}
    combined = json.loads((WORK / 'europe-combined-retry/build-result.json').read_text())
    assert combined['status'] == 'pass' and combined['sourceIdentityAtAssembly'] == receipt['sourceIdentity']
    comparison = json.loads((WORK / 'compiled-combined-comparison/comparison.json').read_text())
    assert comparison['status'] == 'pass_under_explicit_models' and comparison['nativeStatus'] == 'not_run'
    OUT.mkdir(parents=True)
    for name in [
        'source-review.json', 'restored-toolchain.json', 'capture-stage-runner-binding.json',
        'frozen-pathing-restoration.json', 'build-one-europe-capture-stage.py',
        'build-one-europe.py', 'build-one-europe-combined-retry.py',
        'compare-compiled-startup.py', 'compare-combined-startup.py',
        'run-authority-focused-tests.py', 'run-authority-focused-tests-attempt2.py',
        'run-authority-focused-tests-attempt3.py',
        'run-military-focused-tests-attempt1.py', 'run-military-focused-tests-attempt2.py',
        'run-military-focused-tests-attempt3.py', 'run-military-focused-tests-attempt4.py',
        'run-full-wurst-tests.py', 'refresh-source-reports.py', 'collect-evidence.py',
        'verify-evidence.py', 'write-review-summary.py', 'verification-summary.json', 'README.md',
    ]:
        copy(WORK / name)
    for directory in ['authority-focused', 'authority-focused-attempt2', 'authority-focused-attempt3',
                      'military-focused-attempt1', 'military-focused-attempt2',
                      'military-focused-attempt3', 'military-focused-attempt4']:
        copy_existing(directory, ['focused-context.json', 'results.json', 'execution.log'])
    for directory in ['europe-baseline-setup-failure', 'europe-baseline', 'europe-revised',
                      'europe-combined', 'europe-combined-retry']:
        copy_existing(directory, ['build-result.json', 'build-runner.py', 'typecheck.log', 'build.log',
                                  'inputs-before.json', 'inputs-after.json', 'dependency-before.json',
                                  'resource-failure-observation.json', 'runtime/build-identity.json'])
    for directory in ['compiled-comparison', 'compiled-comparison-attempt2', 'compiled-combined-comparison']:
        copy_existing(directory, ['comparison.json', 'baseline-payload-ascii-inspection.json'])
        for side in ['baseline', 'revised']:
            copy_existing(directory + '/' + side + '/frozen',
                          ['result.json', 'late-startup-stubs.lua', 'probe-lua54-initialization.py'])
            copy_existing(directory + '/' + side + '/observer',
                          ['startup-and-first-callbacks.json', 'observe-startup.lua', 'observe-startup.py',
                           *[f'cache-write-{i}.txt.gz' for i in range(1, 5)]])
    copy_existing('observer-parse-once', ['observe-startup.lua', 'variant.json'])
    for source in sorted((WORK / 'source-checks').iterdir()):
        if source.is_file():
            copy(source)
    for source in sorted((WORK / 'full-wurst-tests').iterdir()):
        if not source.is_file():
            continue
        if source.name == 'execution.log':
            copy(source, 'full-wurst-tests/execution.log.gz', compress=True)
        elif source.suffix == '.json':
            copy(source)
    copy(WORK / 'full-wurst-driver.log', 'full-wurst-tests/run.log')
    for name in ['ScenarioData', 'ScenarioSettings', 'ConformanceData']:
        copy(WORK / f'full-wurst-tests/compile/wurst/{name}.wurst',
             f'full-wurst-tests/generated/{name}.wurst.gz', compress=True)
    copy(PROJECT.parent / '_shared/tooling/wurst_execution.py', 'common/wurst_execution.py')
    copy(PROJECT / 'reports/issue-438/trade-startup/probe-lua54-initialization.py', 'common/probe-lua54-initialization.py')
    copy(PROJECT / 'reports/issue-438/trade-startup/late-startup-stubs.lua', 'common/late-startup-stubs.lua')
    copy(PROJECT / 'reports/issue-438/native-boundary-repair/owner-native-observation.json', 'previous-native-observation.json')
    files = []
    for path in sorted(OUT.rglob('*')):
        if not path.is_file():
            continue
        relative = path.relative_to(OUT).as_posix()
        packaged = path.read_bytes()
        encoding = ENCODINGS[relative]
        original = gzip.decompress(packaged) if encoding == 'gzip_mtime_0' else packaged
        files.append({'file': relative, 'encoding': encoding,
                      'packagedBytes': len(packaged), 'packagedSha256': sha(packaged),
                      'originalBytes': len(original), 'originalSha256': sha(original)})
    manifest = {
        'format': 'startup_work_reduction_evidence_v1',
        'status': 'complete_source_evidence_native_not_run',
        'baselineRevision': REVISION, 'sourceIdentity': receipt['sourceIdentity'],
        'createdAt': datetime.now(timezone.utc).isoformat(),
        'nativeStatus': 'not_run', 'nativeHangResolution': 'not_established',
        'playerArtifactProduced': False,
        'compiledPaths': {'baseline': 'europe-baseline', 'captureOnly': 'europe-revised',
                          'combined': 'europe-combined-retry',
                          'captureComparison': 'compiled-comparison-attempt2',
                          'combinedComparison': 'compiled-combined-comparison'},
        'retentionScope': 'Exact selected receipts, raw transcripts, immutable compiler/input manifests, generated fixture save bodies, and reproduction scripts. Raw map archives and 16 MB compiled Lua files are represented by bound compiler/archive receipts, not re-extracted by the verifier.',
        'files': files,
    }
    (OUT / 'manifest.json').write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'path': str(OUT), 'files': len(files), 'packagedBytes': sum(x['packagedBytes'] for x in files),
                      'manifestSha256': sha((OUT / 'manifest.json').read_bytes())}, sort_keys=True))


if __name__ == '__main__':
    main()
