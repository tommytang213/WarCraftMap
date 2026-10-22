"""Retain focused evidence; this format cannot satisfy full-suite release gates."""
from pathlib import Path
import gzip
import json
import re
import sys

project = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project.parent / '_shared/tooling'))
from wurst_execution import parse_results, PINNED_COMPILER_SHA256, PINNED_IMAGE, sha, canonical
from integration_evidence import source_identity, observed_probes, load_contract

folder = Path(__file__).resolve().parent
root = project / '_build/issue-527'
identity = json.loads((root / 'source-identity.json').read_text())
assert source_identity(project, identity['sourceRevision']) == identity
expected = json.loads((root / 'expected.json').read_text())
inputs = json.loads((root / 'inputs.json').read_text())
raw = (folder / 'focused-wurst.log').read_bytes()
log = raw.decode()
rows, errors = parse_results(log, expected)
assert not errors, errors
assert all(row['status'] == 'pass' for row in rows)
assert 'Typecheck succeeded.' in log
assert PINNED_COMPILER_SHA256 + '  /home/wurstuser/.wurst/wurst-compiler/wurstscript.jar' in log
for name, digest in inputs.items():
    assert sha((root / 'compile' / name).read_bytes()) == digest, name
    assert len(re.findall(r'^' + re.escape(name) + r': OK$', log, re.M)) == 2, name
probes = observed_probes(log, rows, load_contract(project))
record = dict(format='warcraftmap_focused_wurst_v1', status='pass', sourceIdentity=identity,
              pinnedImage=PINNED_IMAGE, compilerSha256=PINNED_COMPILER_SHA256,
              discovered=len(expected), succeeded=len(rows), tests=rows, errors=errors,
              inputs=inputs, inputSetSha256=sha(canonical(inputs)), logSha256=sha(raw),
              productionProbes=probes, currentFlattenedWurstInputsVerified=True,
              typecheck='pass', fullSuiteReleaseEvidence=False,
              transcript='focused-wurst.log.gz',
              isolation='Network disabled; read-only source; default image user UID/GID 1001; private container /tmp build.',
              standardLibrary='Cached upstream source dependency only, hashed before and after; no predecessor code or execution evidence.')
(folder / 'focused-results.json').write_text(json.dumps(record, indent=2, sort_keys=True) + '\n')
(folder / 'focused-wurst.log.gz').write_bytes(gzip.compress(raw, mtime=0))
checks = []
for name in ['research-science-save', 'economy', 'framework', 'packaging', 'audit-tests']:
    text = (folder / (name + '.log')).read_text()
    match = re.search(r'Ran (\d+) tests? in ', text)
    assert match and re.search(r'^OK$', text, re.M) and not re.search(r'^FAILED', text, re.M), name
    checks.append(dict(check=name, tests=int(match[1]), status='pass'))
    (folder / (name + '.log.gz')).write_bytes(gzip.compress(text.encode(), mtime=0))
for name in ['release-blocker-audit.json', 'runtime-acceptance.json', 'traceability/requirements.json']:
    report = json.loads((project / 'reports' / name).read_text())
    assert all(report[k] == v for k, v in identity.items()), name
summary = dict(format='warcraftmap_focused_validation_v1', status='pass', sourceIdentity=identity,
               checks=checks, pythonTests=sum(row['tests'] for row in checks), wurstTests=len(rows),
               typecheck='pass', reports='All three reports regenerated; source-only publication blockers retained.',
               fullRepositoryValidation='deferred_to_controller', nativeClient='not_run')
(folder / 'validation.json').write_text(json.dumps(summary, indent=2, sort_keys=True) + '\n')
print(json.dumps(summary, indent=2))
