"""Inspect the exact three consumer identities in all freshly generated map payloads."""
from pathlib import Path
import json,hashlib,sys
project=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(project.parent/'_shared/tooling'),str(project/'tooling')]
from package_wurst_map import load_config,generate,GENERATED_DATA,GENERATED_WURST,PROVENANCE
from package_wurst_campaign import load_campaign_config,validate_campaign,_localize_runtime
from land_army_catalog import CLOSURE_EFFECTS
config=load_campaign_config(project/'physical-maps.json');world=validate_campaign(config)
root=project/'_build/issue-550/payloads';generate(load_config(project/'package.json'),root)
original={name:(root/name).read_bytes() for name in (GENERATED_DATA,GENERATED_WURST,PROVENANCE)}
base=json.loads(original[GENERATED_DATA]);rows=[]
for physical in config.maps:
    for name,data in original.items():(root/name).write_bytes(data)
    _localize_runtime(config,world,physical,root)
    payload=json.loads((root/GENERATED_DATA).read_text())
    assert payload['landArmy']==base['landArmy']
    assert {(e['kind'],e['contentId']) for e in payload['landArmy']['consumers']}==set(CLOSURE_EFFECTS)
    assert not set(CLOSURE_EFFECTS)&{(e['kind'],e['contentId']) for e in payload['researchIntegrationBlockers']}
    source=(root/GENERATED_WURST).read_text()
    if not physical.bootstrap:
        for (kind,ident),(_,metric,bp) in CLOSURE_EFFECTS.items():
            assert source.count(f'research.register(new CivicEffect("{kind}", "{ident}", "{metric}", {bp}))')==1
    rows.append(dict(mapId=physical.id,selectorOnly=physical.bootstrap,runtimeSha256=hashlib.sha256((root/GENERATED_DATA).read_bytes()).hexdigest(),sourceSha256=hashlib.sha256(source.encode()).hexdigest()))
Path(__file__).with_name('regional-payloads.json').write_text(json.dumps(dict(maps=rows,consumers=base['landArmy']['consumers'],inspection='Generated source only; no native or full campaign execution claim.'),indent=2)+'\n')
print('Inspected',len(rows),'fresh physical-map payloads')
