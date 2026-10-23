"""Validate and retain focused current-source evidence, never a full-suite claim."""
from pathlib import Path
import gzip
import json
import re
import sys

project = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project.parent / '_shared/tooling'))
from wurst_execution import parse_results, PINNED_COMPILER_SHA256, PINNED_IMAGE, sha, canonical
from integration_evidence import source_identity, observed_probes, load_contract
from civic_governance import COMPARATIVE_PATHS

folder = Path(__file__).resolve().parent
root = project / '_build/issue-548'
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
                  typecheck='pass', fullSuiteReleaseEvidence=False,
                  transcript=filename + '.gz',
                  isolation='Network disabled; read-only source; default image user UID/GID 1001; private container /tmp build.',
                  standardLibrary='Cached upstream source dependency only, hashed before and after; no predecessor implementation or execution evidence.')
    if label == 'focused':
        probes = observed_probes(log, rows, load_contract(project))
        for system, name, required in COMPARATIVE_PATHS.values():
            assert required <= set(probes['wurst/CivicGovernanceTests.wurst:' + name]), system
        result['productionProbes'] = probes
    (folder / (label + '-results.json')).write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    (folder / (filename + '.gz')).write_bytes(gzip.compress(raw, mtime=0))
    return len(rows)

wurst = record('focused', root, 'focused-wurst.log')
framework = {name: record('framework-' + name, root / ('framework/' + name + '-build'),
                         'framework-' + name + '.log') for name in ('original', 'mutated')}
checks = []
for name in ['binding', 'civic', 'administrative', 'integration', 'framework', 'execution', 'release', 'runtime', 'traceability']:
    text = (folder / (name + '-tests.log')).read_text()
    match = re.search(r'Ran (\d+) tests? in ', text)
    assert match and re.search(r'^OK$', text, re.M) and not re.search(r'^FAILED', text, re.M), name
    checks.append(dict(check=name, tests=int(match[1]), status='pass'))
    (folder / (name + '-tests.log.gz')).write_bytes(gzip.compress(text.encode(), mtime=0))
reports = {}
for name, filename in [('release', 'release-blocker-audit.json'), ('runtime', 'runtime-acceptance.json'),
                       ('traceability', 'traceability/requirements.json')]:
    report = json.loads((project / 'reports' / filename).read_text())
    assert all(report[k] == v for k, v in identity.items()), name
    reports[name] = dict(status=report['status'], blockers=report.get('blockerCount', report.get('unresolvedCampaignBlockers')))
inspections = {}
for name in ('regional-payloads', 'packaged-registration'):
    report = json.loads((folder / (name + '.json')).read_text())
    assert report['sourceIdentity'] == identity, name
    if name == 'packaged-registration':
        assert report['status'] == 'pass' and all(report['checks'].values())
    inspections[name] = name + '.json'
assert 'OK: framework content and implementation boundary' in (folder / 'framework-boundary.log').read_text()
summary = dict(format='warcraftmap_focused_validation_v1', status='pass', sourceIdentity=identity,
               checks=checks, pythonTests=sum(row['tests'] for row in checks), wurstTests=wurst,
               standaloneFrameworkTests=framework, typecheck='pass', reports=reports,
               inspections=inspections, frameworkBoundary='pass',
               fullRepositoryValidation='deferred_to_controller',
               mainIntegration='Controller must regenerate all three audits with fresh full-suite and packaged campaign evidence after integration.',
               nativeClient='not_run')
(folder / 'validation.json').write_text(json.dumps(summary, indent=2, sort_keys=True) + '\n')
print(json.dumps(summary, indent=2))
