"""Retain interrupted checks and scoped evidence without asserting gate success."""
from pathlib import Path
import hashlib, json, shutil, subprocess, sys

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent / 'WarCraftMap'
COMMIT = '791ce7f44944af124fe87400d2f1ecfa5882240b'
SOURCE = '91996f8be9079d4e0c3a3c6dd84b7b96f04f119ff38714765804052f7750c450'
PROJECT = REPO / 'maps/historical-world-rpg/age-of-sail-world'
DEST = PROJECT / 'reports/issue-438/main-594d36c-validation'
sys.path.insert(0, str(PROJECT.parent / '_shared/tooling'))
from integration_evidence import source_identity
def read(path):
    return json.loads(path.read_text())
assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=REPO, text=True).strip() == COMMIT
assert source_identity(PROJECT, COMMIT) == {'sourceRevision': COMMIT, 'sourceTreeSha256': SOURCE}
assert not DEST.exists(), 'Do not overwrite retained evidence'
first_stop = read(ROOT / 'required-attempt1/stop-reconciliation.json')
assert first_stop['status'] == 'stopped_before_completion' and not first_stop['canonicalGatePassed']
assert hashlib.sha256((ROOT / 'required-attempt1/canonical-required.log').read_bytes()).hexdigest() == first_stop['logSha256']
for attempt in (2, 3):
    receipt = read(ROOT / f'required-attempt{attempt}/receipt.json')
    assert receipt['status'] == 'interrupted' and receipt['childReconciliation']['ownedGroupStopped']
    assert hashlib.sha256((ROOT / f'required-attempt{attempt}/canonical-required.log').read_bytes()).hexdigest() == receipt['commands'][0]['logSha256']
assert receipt['commit'] == COMMIT and receipt['sourceIdentity'] == source_identity(PROJECT, COMMIT)
remaining = read(ROOT / 'remaining-checks-attempt2/receipt.json')
assert remaining['status'] == 'pass_component_checks' and remaining['testedCommit'] == COMMIT
assert remaining['sourceIdentity'] == source_identity(PROJECT, COMMIT)
assert remaining['sourceUnchanged'] and remaining['worktreeClean']
for command in remaining['commands']:
    assert command['exitCode'] == 0
    assert hashlib.sha256((ROOT / 'remaining-checks-attempt2' / command['log']).read_bytes()).hexdigest() == command['logSha256']
review = read(ROOT / 'pre-ci-review.json')
assert review['status'] == 'pass_scoped_pre_ci_review' and review['implementationCommit'] == COMMIT
assert review['sourceTreeSha256'] == SOURCE and review['blockingFindings'] == []
summary = read(ROOT / 'pre-ci-summary.json')
assert summary['implementationCommit'] == COMMIT and summary['sourceTreeSha256'] == SOURCE
assert summary['canonicalLocalGate'] == 'interrupted_after_failure' and not summary['continueFreezeVerifiedFixed']
items = {}
def add(target, source):
    assert target not in items
    items[target] = ROOT / source
for name in ('independent-source-review.json', 'independent-native-boundary-review.json',
             'startup-source-inspection.json', 'independent-diagnostic-driver-review.json',
             'pre-ci-review.json', 'pre-ci-summary.json', 'retain_pre_ci_evidence.py'):
    add(name, name)
for attempt in (1, 2, 3):
    src = f'required-attempt{attempt}'
    target = f'interrupted-attempt{attempt}'
    for name in ('receipt.json', 'canonical-required.log'):
        add(target + '/' + name, src + '/' + name)
    if attempt == 1:
        add(target + '/stop-reconciliation.json', src + '/stop-reconciliation.json')
    else:
        add(target + '/assistant-stop-request.txt', src + '/assistant-stop-request.txt')
    driver = 'run_required_checks.py' if attempt == 1 else f'run_required_checks_attempt{attempt}.py'
    add(target + '/driver.py', driver)
for name in ('receipt.json', 'test.log'):
    add('isolated-synthetic-packaging/' + name, 'packaging-failure-attempt1/' + name)
for name in ('receipt.json', 'baseline.log', 'hook.log'):
    add('diagnostic-logging/' + name, 'diagnostic-hook-check/' + name)
add('diagnostic-logging/sitecustomize.py', 'diagnostic_python/sitecustomize.py')
add('terrain-context-observation.json', 'terrain-context-observation/receipt.json')
add('source-report-refresh.json', 'report-refresh-attempt3/receipt.json')
add('remaining-checks/driver.py', 'run_remaining_checks.py')
add('remaining-checks/setup-failure.json', 'remaining-checks/receipt.json')
for path in sorted((ROOT / 'remaining-checks-attempt2').iterdir()):
    assert path.suffix in ('.json', '.log')
    add('remaining-checks/' + path.name, str(path.relative_to(ROOT)))
for name in (
    'baseline-generator.py', 'baseline.json', 'europe-profile.txt',
    'europe-baseline.json', 'africa-baseline.json', 'middle_east_india-baseline.json',
    'southeast_asia-baseline.json', 'east_asia-baseline.json',
    'americas_caribbean-baseline.json', 'pacific-baseline.json',
    'comparison.json', 'revised-profile.txt', 'focused-attempt1.json',
    'focused-attempt2.json', 'focused-attempt2.log',
    'legacy-work-negative-control.json', 'legacy-work-negative-control.log',
    'x-clipping-negative-control.json', 'comparison-revised.json',
    'rows-only-profile.txt', 'focused-attempt3.json', 'focused-attempt3.log',
    'legacy-work-negative-control-revised.json', 'legacy-work-negative-control-revised.log',
    'final-independent-review.json', 'precommit-closure-review.json',
):
    add('terrain-performance/' + name, 'terrain-performance/' + name)
assert sum(p.stat().st_size for p in items.values()) <= 8 * 1024 * 1024
manifest = {}
for name, source in items.items():
    data = source.read_bytes()
    manifest[name] = {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
DEST.mkdir()
for name, source in items.items():
    target = DEST / name
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    assert hashlib.sha256(target.read_bytes()).hexdigest() == manifest[name]['sha256']
(DEST / 'manifest.json').write_text(json.dumps({
    'format': 'pr536_main594_pre_ci_evidence_v1', 'implementationCommit': COMMIT,
    'sourceTreeSha256': SOURCE,
    'canonicalLocalGate': 'interrupted_after_failure', 'ciStatusAtCollection': 'not_started',
    'nativeStatus': 'not_run', 'continueFreezeVerifiedFixed': False,
    'scope': 'Scoped source reviews, local focused/component checks, negative controls and interrupted full-gate attempts. Not a passing full-gate or native receipt.',
    'files': manifest,
}, indent=2) + '\n')
print(json.dumps({'destination': str(DEST), 'files': len(manifest),
                  'bytes': sum(row['bytes'] for row in manifest.values()), 'nativeStatus': 'not_run'}))
