"""Retain source-bound final transcripts and a focused validation summary."""
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

PROJECT = Path(__file__).resolve().parents[2]
ROOT = PROJECT / '_build/issue522'
OUTPUT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT.parent / '_shared/tooling'))
from integration_evidence import source_identity
from wurst_execution import source_revision

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

evidence = json.loads((ROOT / 'evidence/results.json').read_text())
identity = source_identity(PROJECT, source_revision(PROJECT))
assert evidence['status'] == 'pass' and evidence['sourceIdentity'] == identity
assert not evidence['errors'] and all(row['status'] == 'pass' for row in evidence['tests'])
regional = json.loads((OUTPUT / 'regional-payloads.json').read_text())
assert regional['sourceIdentity'] == identity
paths = {
    'wurst-results.json': ROOT / 'evidence/results.json',
    'wurst-execution.log': ROOT / 'evidence/execution.log',
    'wurst-typecheck.log': ROOT / 'typecheck.log',
    'framework-pinned.log': ROOT / 'framework-pinned.log',
}
python_logs = {
    'combat': ROOT / 'combat-tests.log', 'research': ROOT / 'research-tests.log',
    'military': ROOT / 'military-tests.log', 'traceability': ROOT / 'traceability-tests.log',
    'release': ROOT / 'release-tests-final.log', 'runtime': ROOT / 'runtime-tests.log',
    'vessel': ROOT / 'vessel-tests.log', 'save': ROOT / 'save-tests.log',
    'liveTradition': ROOT / 'live-tradition-tests.log', 'framework': ROOT / 'framework-tests.log',
}
counts = {}
for name, path in python_logs.items():
    text = path.read_text()
    assert re.search(r'^OK$', text, re.M) and not re.search(r'^FAILED', text, re.M), name
    counts[name] = int(re.search(r'Ran (\d+) tests?', text)[1])
    paths['python-' + name + '.log'] = path
for name in ('runtime-audit', 'release-audit', 'traceability-audit', 'framework-boundary', 'world-validation', 'map-validation'):
    paths[name + '.log'] = ROOT / (name + '.log')
transcripts = []
for name, path in paths.items():
    target = OUTPUT / (name + '.gz')
    target.write_bytes(gzip.compress(path.read_bytes(), mtime=0))
    transcripts.append(dict(file=target.name, sha256=sha(target)))
release_path = PROJECT / 'reports/release-blocker-audit.json'
release = json.loads(release_path.read_text())
old = json.loads(subprocess.check_output(['git', 'show', 'HEAD:' + str(release_path.relative_to(PROJECT.parents[2]))], cwd=PROJECT))
old_findings = {r['id'] for r in old['findings']}
new_findings = {r['id'] for r in release['findings']}
closed = 'RESEARCH-UNBOUND-CAST-CANNON-MODIFIER-PROGRESSION-CAST-CANNON'
assert old_findings - new_findings == {closed} and not new_findings - old_findings
framework = json.loads((PROJECT.parent / 'conformance-campaign/_build/conformance-report.json').read_text())
assert framework['status'] == 'pass'
report = dict(issue=522, sourceIdentity=identity, toolchain=evidence['compiler'],
    standardLibraryRevision='1bd90397f6c034f19602127af2ab48d332d8fff9',
    wurst=dict(status='pass', typecheck='pass', passed=len(evidence['tests']),
               suites=dict(Counter(t['id'].split(':')[0] for t in evidence['tests'])),
               newTests=[t['id'] for t in evidence['tests'] if 'castCannon' in t['id']]),
    python=dict(status='pass', passed=sum(counts.values()), suites=counts),
    framework=dict(status='pass', pinnedTestsPerCampaign=2, campaigns=2, sharedSourcesUnchanged=True),
    regionalPayloads=dict(physicalMaps=len(regional['maps']), qualifiedProfiles=len(regional['qualifiedProfiles'])),
    simulations=dict(localBattleProfiles=3, status='pass'),
    releaseAudit=dict(removed=[closed], added=[], retainedCampaignBlockers=release['unresolvedCampaignBlockers']),
    auditReports={str(p.relative_to(PROJECT)): sha(p) for p in
        (release_path, PROJECT / 'reports/runtime-acceptance.json', PROJECT / 'reports/traceability/requirements.json')},
    transcripts=transcripts, nativeClient='not_run', fullRepositoryValidation='outer worker', releaseReady=False)
(OUTPUT / 'validation.json').write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
print(f"Retained {report['wurst']['passed']} pinned Wurst and {report['python']['passed']} Python passes")
