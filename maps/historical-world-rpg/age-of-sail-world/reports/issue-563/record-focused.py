"""Retain fresh focused development checks; never manufacture full-suite evidence."""
from pathlib import Path
import gzip
import json
import re
import sys

project = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(project.parent / '_shared/tooling'), str(project / 'tooling')]
from integration_evidence import source_identity, observed_probes, load_contract
from wurst_execution import parse_results, source_revision, sha, canonical, PINNED_COMPILER_SHA256, PINNED_IMAGE
from land_army_catalog import COMPARATIVE_PATHS, ADAPTER_TEST, BAYONET_ADAPTER_PROBES, BAYONET_ROLLBACK_TEST

folder = Path(__file__).resolve().parent
build = project / '_build/issue-563'
identity = source_identity(project, source_revision(project))
assert identity == json.loads((build / 'source-identity.json').read_text()), 'sources changed after preparation'
raw = (build / 'focused-wurst.log').read_bytes()
log = raw.decode()
expected = json.loads((build / 'expected.json').read_text())
rows, errors = parse_results(log, expected)
assert not errors, errors
assert len(rows) == len(expected) and all(row['status'] == 'pass' for row in rows)
assert BAYONET_ROLLBACK_TEST in {row['id'] for row in rows}
assert '/home/wurstuser/.wurst/wurst-compiler/wurstscript.jar: OK' in log
inputs = json.loads((build / 'inputs.json').read_text())
for relative, digest in inputs.items():
    assert sha((build / 'compile' / relative).read_bytes()) == digest, relative
    assert log.count(relative + ': OK') >= 2, relative
probes = observed_probes(log, rows, load_contract(project))
for _, (_, name, required) in COMPARATIVE_PATHS.items():
    assert required <= set(probes['wurst/LandArmyEffectsTests.wurst:' + name]), name
assert BAYONET_ADAPTER_PROBES <= set(probes[ADAPTER_TEST])
result = dict(format='warcraftmap_focused_wurst_v1', status='pass', fullSuite=False,
              sourceIdentity=identity, expected=expected, tests=rows,
              compilerSha256=PINNED_COMPILER_SHA256, pinnedImage=PINNED_IMAGE,
              inputSetSha256=sha(canonical(inputs)), logSha256=sha(raw), productionCoverage=probes,
              nativeClient='not_run')
(folder / 'focused-results.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
python_checks = {}
for name in ('final-audit-python', 'framework-runtime-trace-python', 'main-evidence-python'):
    data = (build / (name + '.log')).read_bytes()
    text = data.decode()
    matches = re.findall(r'Ran (\d+) tests in ', text)
    assert len(matches) == 1 and '\nOK\n' in text, name
    python_checks[name] = int(matches[0])
    (folder / (name + '.log.gz')).write_bytes(gzip.compress(data, mtime=0))
for name in ('focused-wurst', 'boundary', 'refresh-audits', 'trace-freshness'):
    data = (build / (name + '.log')).read_bytes()
    (folder / (name + '.log.gz')).write_bytes(gzip.compress(data, mtime=0))
assert 'OK: framework content and implementation boundary' in (build / 'boundary.log').read_text()
assert 'Traceability:' in (build / 'trace-freshness.log').read_text()
audits = json.loads((build / 'local-planning-audit.json').read_text())
assert audits['sourceIdentity'] == identity and audits['regenerated'] and not audits['execution']['valid']
release = audits['reports']['release']['report']
previous = audits['reports']['release']['recorded']
assert {f['id'] for f in release['findings']} == {f['id'] for f in previous['findings']}
assert any(f['id'] == 'RESEARCH-UNBOUND-BAYONET-SYSTEM-MODIFIER-PROGRESSION-BAYONET-SYSTEM' for f in release['findings'])
summary = dict(sourceIdentity=identity, focusedPinnedWurstTests=len(rows), pythonTests=python_checks,
               releaseBlockers=release['unresolvedCampaignBlockers'],
               traceabilityBlockers=audits['reports']['traceability']['report']['blockerCount'],
               releaseFindingsUnchanged=True, nativeClient='not_run',
               fullRepositoryValidation='controller after integration preflight',
               integratedClosure='requires new-main full-suite evidence through #560 transport and all three fresh audits')
(folder / 'validation.json').write_text(json.dumps(summary, indent=2, sort_keys=True) + '\n')
print(json.dumps(summary, sort_keys=True))
