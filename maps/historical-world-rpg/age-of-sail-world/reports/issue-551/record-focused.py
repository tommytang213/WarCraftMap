"""Check pinned focused transcripts and retain their honest development scope."""
from pathlib import Path
import gzip
import json
import re
import sys

project = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project.parent / '_shared/tooling'))
from wurst_execution import (parse_results, PINNED_COMPILER_SHA256, PINNED_IMAGE,
                             FORMAT, sha, canonical, verify_evidence)
from integration_evidence import (source_identity, observed_probes, load_contract,
                                  verify_execution_coverage)
from trade_finance import AUCTION_PROBES, REQUIRED_TESTS, AUCTION_TESTS, verified_bindings

folder = Path(__file__).resolve().parent
root = project / '_build/issue-551'
identity = json.loads((root / 'source-identity.json').read_text())
assert source_identity(project, identity['sourceRevision']) == identity


def record(label, build, filename):
    expected = json.loads((build / 'expected.json').read_text())
    inputs = json.loads((build / 'inputs.json').read_text())
    raw = (folder / filename).read_bytes()
    log = raw.decode()
    rows, errors = parse_results(log, expected)
    assert not errors, errors
    assert all(row['status'] == 'pass' for row in rows)
    assert 'Typecheck succeeded.' in log
    assert PINNED_COMPILER_SHA256 + '  /home/wurstuser/.wurst/wurst-compiler/wurstscript.jar' in log
    for name, digest in inputs.items():
        assert sha((build / 'compile' / name).read_bytes()) == digest, name
        assert len(re.findall(r'^' + re.escape(name) + r': OK$', log, re.M)) == 2, name
    result = dict(format='warcraftmap_focused_wurst_v1', status='pass', sourceIdentity=identity,
                  pinnedImage=PINNED_IMAGE, compilerSha256=PINNED_COMPILER_SHA256,
                  discovered=len(expected), succeeded=len(rows), tests=rows, errors=errors,
                  inputs=inputs, inputSetSha256=sha(canonical(inputs)), logSha256=sha(raw),
                  typecheck='pass', fullSuiteReleaseEvidence=False, transcript=filename + '.gz',
                  isolation='Network disabled; read-only source mount; UID/GID 1001; private container /tmp builds.',
                  standardLibrary='Cached upstream source dependency only; no predecessor implementation or artifacts.')
    if label == 'focused':
        contract = load_contract(project)
        probes = observed_probes(log, rows, contract)
        names = {row['id'].rsplit(':', 1)[-1] for row in rows if row['id'].startswith('wurst/TradeFinanceTests.wurst:')}
        assert REQUIRED_TESTS | AUCTION_TESTS <= names
        assert AUCTION_PROBES <= set(probes['wurst/TradeFinanceTests.wurst:auctionOnlyRegisteredPurchaseAndSaleMatchControlsAndConserveAuthority'])
        result['productionProbes'] = probes
        # The existing transcript verifier accepts these exact selected tests.
        # The integration verifier must reject this incomplete full discovery.
        report = dict(format=FORMAT, status='pass', executionStatus='completed',
                      sourceRevision=identity['sourceRevision'], sourceIdentity=identity,
                      expected=expected, tests=rows, errors=[], returnCode=0,
                      inputs=inputs, inputSetSha256=sha(canonical(inputs)), logSha256=sha(raw),
                      discovered=len(expected), succeeded=len(rows),
                      compiler={'sha256': PINNED_COMPILER_SHA256},
                      productionCoverage={'contractSha256': sha(canonical(contract)), 'tests': probes})
        verify_evidence(report, raw, identity['sourceRevision'])
        try:
            verify_execution_coverage(report, raw, project, identity['sourceRevision'])
        except ValueError as error:
            assert 'discovery does not match current source tests' in str(error), str(error)
            result['fullSuiteRejection'] = str(error)
        else:
            raise AssertionError('Focused execution must not close release bindings')
        assert verified_bindings(project, report, raw, identity['sourceRevision']) == set()
    (folder / (label + '-results.json.gz')).write_bytes(gzip.compress(
        (json.dumps(result, indent=2, sort_keys=True) + '\n').encode(), mtime=0))
    (folder / (filename + '.gz')).write_bytes(gzip.compress(raw, mtime=0))
    return len(rows)


wurst = record('focused', root, 'pinned-wurst.log')
framework = {name: record('framework-' + name, root / ('framework/' + name + '-build'),
                         'framework-' + name + '.log') for name in ('original', 'mutated')}
checks = []
for path in sorted(folder.glob('*-tests.log')):
    log = path.read_text()
    match = re.search(r'Ran (\d+) tests? in ', log)
    assert match and re.search(r'^OK$', log, re.M) and not re.search(r'^FAILED', log, re.M), path
    checks.append(dict(check=path.stem, tests=int(match[1]), status='pass'))
    path.with_suffix('.log.gz').write_bytes(gzip.compress(path.read_bytes(), mtime=0))
reports = {}
for name, filename in [('release', 'release-blocker-audit.json'), ('runtime', 'runtime-acceptance.json'),
                       ('traceability', 'traceability/requirements.json')]:
    report = json.loads((project / 'reports' / filename).read_text())
    assert all(report[k] == v for k, v in identity.items()), name
    reports[name] = dict(status=report['status'], blockers=report.get('blockerCount', report.get('unresolvedCampaignBlockers')))
assert 'OK: framework content and implementation boundary' in (folder / 'framework-boundary.log').read_text()
for path in folder.glob('*-audit.log'):
    path.with_suffix('.log.gz').write_bytes(gzip.compress(path.read_bytes(), mtime=0))
(folder / 'framework-boundary.log.gz').write_bytes(gzip.compress((folder / 'framework-boundary.log').read_bytes(), mtime=0))
summary = dict(format='warcraftmap_focused_validation_v1', status='pass', issue=551,
               sourceIdentity=identity, checks=checks, pythonTests=sum(row['tests'] for row in checks),
               wurstTests=wurst, standaloneFrameworkTests=framework, typecheck='pass', reports=reports,
               frameworkBoundary='pass', fullRepositoryValidation='deferred_to_controller',
               mainIntegration='Regenerate all three audits with fresh full-suite and packaged campaign evidence on integrated main; require exact Auction finding to disappear.',
               nativeClient='not_run', releasePromotion='blocked')
(folder / 'validation.json').write_text(json.dumps(summary, indent=2, sort_keys=True) + '\n')
print(json.dumps(summary, indent=2))
