"""Collect real focused interpreter evidence, without claiming full-suite closure."""
from pathlib import Path
import gzip
import hashlib
import json
import sys

project = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project.parent / '_shared/tooling'))
from wurst_execution import parse_results, source_revision, input_hashes
from integration_evidence import load_contract, observed_probes, source_identity

root = Path(__file__).resolve().parent
assembly = project / '_build/issue-528'
raw = Path(sys.argv[1]).read_bytes()
expected = json.loads((assembly / 'expected.json').read_text())
tests, errors = parse_results(raw.decode(), expected)
assert not errors, errors
assert len(tests) == len(expected) and all(r['status'] == 'pass' for r in tests)
count = len(tests)
assert input_hashes(assembly / 'compile') == json.loads((assembly / 'inputs.json').read_text())
identity = source_identity(project, source_revision(project))
result = {'format': 'focused_wurst_execution_not_release_evidence',
          'scope': f'{count} selected real interpreter cases. Full repository validation and shipping archive inspection remain controller work.',
          'sourceIdentity': identity,
          'compiler': {'image': 'frotty/wurstscript@sha256:ea428badd326df6f16f5d3857f7aadc100dbaacfbdb8fbac026933ab369fbb5a',
                       'jarSha256': '1f3ae40b1018b8757867515596adfa69113ca85f390c1b353cc8b69cf8944145',
                       'uid': 1001, 'gid': 1001, 'sourceMount': 'read-only', 'buildDirectory': 'container-private /tmp'},
          'tests': tests, 'productionCoverage': {'tests': observed_probes(raw.decode(), tests, load_contract(project))},
          'transcriptSha256': hashlib.sha256(raw).hexdigest()}
(root / 'focused-results.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
for filename, data in [('focused-wurst.log.gz', raw), ('focused-inputs.json.gz', (assembly / 'inputs.json').read_bytes())]:
    with gzip.GzipFile(str(root / filename), 'wb', mtime=0) as stream:
        stream.write(data)
runtime = json.loads((assembly / 'generated/scenario-runtime.json').read_text())
unlocks = [r for r in runtime['researchUnlockDefinitions'] if r['nodeId'] == 'ciphered_dispatches']
assert {(r['kind'], r['contentId']) for r in unlocks} == {('modifier', 'progression_ciphered_dispatches')}
assert not any(r['nodeId'] == 'ciphered_dispatches' for r in runtime['researchIntegrationBlockers'])
inspection = {'scope': 'Generated release assembly identity inspection; shipping archive inspection belongs to controller validation.',
              'sourceIdentity': identity, 'unlocks': unlocks,
              'dispatchContract': json.loads((project / 'scenario/progression/dispatch-contract.json').read_text()),
              'civicEffects': runtime['civicGovernance']['effects'],
              'generatedHashes': {name: hashlib.sha256((assembly / 'generated' / name).read_bytes()).hexdigest()
                                  for name in ('ScenarioData.wurst', 'scenario-runtime.json', 'provenance.json')}}
source = (assembly / 'generated/ScenarioData.wurst').read_text()
from dispatch_contract import verify_registration
verify_registration(project, json.loads((project / 'scenario/world/world.json').read_text()), source, runtime['civicGovernance'])
(root / 'generated-identities.json').write_text(json.dumps(inspection, indent=2, sort_keys=True) + '\n')
print(f'{count}/{count} real focused Wurst tests passed; exact generated dispatch identity and relay registration inspected.')
