"""Inspect civic policy and epidemic definitions in every generated physical-map payload."""
from pathlib import Path
import hashlib
import json
import sys

PROJECT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(PROJECT.parent / '_shared/tooling'), str(PROJECT / 'tooling')]
from package_wurst_map import load_config, generate, GENERATED_DATA, GENERATED_WURST, PROVENANCE
from package_wurst_campaign import load_campaign_config, validate_campaign, _localize_runtime
from integration_evidence import source_identity
from wurst_execution import source_revision

config = load_campaign_config(PROJECT / 'physical-maps.json')
world = validate_campaign(config)
generated = PROJECT / '_build/issue-548/payloads'
generate(load_config(PROJECT / 'package.json'), generated)
original = {name: (generated / name).read_bytes() for name in (GENERATED_DATA, GENERATED_WURST, PROVENANCE)}
base = json.loads(original[GENERATED_DATA])
keys = {('policy', 'progression_abolitionist_public_sphere'), ('ability', 'epidemic_control')}
effects = [e for e in base['civicGovernance']['effects'] if (e['unlock']['kind'], e['unlock']['contentId']) in keys]
assert len(effects) == 2
rows = []
for physical in config.maps:
    for name, value in original.items():
        (generated / name).write_bytes(value)
    _localize_runtime(config, world, physical, generated)
    data = json.loads((generated / GENERATED_DATA).read_text())
    assert data['civicGovernance'] == base['civicGovernance']
    # Static payload metadata remains conservative; only the execution-backed
    # release audit may recognize these two consumers.
    assert keys <= {(e['kind'], e['contentId']) for e in data['researchIntegrationBlockers']}
    source = (generated / GENERATED_WURST).read_text()
    if not physical.bootstrap:
        for kind, ident in keys:
            assert source.count(f'research.register(new CivicEffect("{kind}", "{ident}",') == 1
        for rule in ('transitionDays = 90', 'responseDays = 90', 'cooldownDays = 90', 'tradePenaltyBasisPoints = 1000'):
            assert 'ledger.' + rule in source
        assert '500)' in source and '2500)' in source
        assert source.count('ledger.configureAdministration(') == base['civicGovernance']['districtCount']
    rows.append(dict(id=physical.id, selectorOnly=physical.bootstrap,
                     runtimeSha256=hashlib.sha256((generated / GENERATED_DATA).read_bytes()).hexdigest(),
                     wurstSha256=hashlib.sha256((generated / GENERATED_WURST).read_bytes()).hexdigest(),
                     executableConsumer=not physical.bootstrap))
report = dict(sourceIdentity=source_identity(PROJECT, source_revision(PROJECT)), effects=effects,
              districtCount=base['civicGovernance']['districtCount'], maps=rows,
              inspection='generated source payloads; no compiled map or native client claim')
Path(__file__).with_name('regional-payloads.json').write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
print(f'Inspected {len(rows)} physical payloads and {report["districtCount"]} administrative districts')
