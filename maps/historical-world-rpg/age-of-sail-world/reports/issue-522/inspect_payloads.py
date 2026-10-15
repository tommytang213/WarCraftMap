"""Inspect production-localized regional payloads without compiling map archives."""
from pathlib import Path
import hashlib
import json
import sys

PROJECT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(PROJECT.parent / '_shared/tooling'), str(PROJECT / 'tooling')]
from package_wurst_map import load_config, generate, GENERATED_DATA, GENERATED_WURST, PROVENANCE
from package_wurst_campaign import load_campaign_config, validate_campaign, _localize_runtime
from combat_effect_catalog import build, verify
from integration_evidence import source_identity
from wurst_execution import source_revision

config = load_campaign_config(PROJECT / 'physical-maps.json')
world = validate_campaign(config)
generated = PROJECT / '_build/issue522/payloads'
generate(load_config(PROJECT / 'package.json'), generated)
original = {name: (generated / name).read_bytes() for name in (GENERATED_DATA, GENERATED_WURST, PROVENANCE)}
base = json.loads(original[GENERATED_DATA])
catalog = build()
key = ('modifier', 'progression_cast_cannon')
binding = catalog.research_effects[key]
profiles = sorted(p['id'] for p in catalog.profiles.values()
                  if any(a['id'] == binding['recipient']['attackId'] for a in p['attacks'])
                  and set(p['weaponIds']) & set(binding['recipient']['weaponIds']))
rows = []
for physical in config.maps:
    for name, value in original.items():
        (generated / name).write_bytes(value)
    _localize_runtime(config, world, physical, generated)
    data = json.loads((generated / GENERATED_DATA).read_text())
    assert data['combatEffectBindings'] == base['combatEffectBindings']
    assert data['combatProfiles'] == base['combatProfiles']
    assert not any((u['kind'], u['contentId']) == key for u in data['researchIntegrationBlockers'])
    source = (generated / GENERATED_WURST).read_text()
    if physical.bootstrap:
        assert 'bindings.addResearchAttack(' not in source
    else:
        verify(source, catalog)
        assert source.count('bindings.addResearchWeapon("research:modifier:progression_cast_cannon",') == len(profiles)
    rows.append(dict(id=physical.id, selectorOnly=physical.bootstrap,
                     runtimeSha256=hashlib.sha256((generated / GENERATED_DATA).read_bytes()).hexdigest(),
                     wurstSha256=hashlib.sha256((generated / GENERATED_WURST).read_bytes()).hexdigest(),
                     executableConsumer=not physical.bootstrap))
report = dict(sourceIdentity=source_identity(PROJECT, source_revision(PROJECT)),
              binding=binding, qualifiedProfiles=profiles, maps=rows,
              inspection='generated production payloads; not compiled regional archives')
Path(__file__).with_name('regional-payloads.json').write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
print(f'Inspected {len(rows)} physical payloads, {len(profiles)} qualified weapon profiles')
