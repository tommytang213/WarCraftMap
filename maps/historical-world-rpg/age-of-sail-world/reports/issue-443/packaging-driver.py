from pathlib import Path
from dataclasses import replace
import json, shutil, sys
sys.path.insert(0,'maps/historical-world-rpg/_shared/tooling')
import package_wurst_campaign as c
import package_wurst_map as m
from materialize_physical_map import materialize
from integration_evidence import source_identity
from wurst_execution import source_revision
config=c.load_campaign_config(Path('maps/historical-world-rpg/age-of-sail-world/physical-maps.json'))
base=m.load_config(config.map_config_path)
world=c.validate_campaign(config)
identity=source_identity(config.project, source_revision(config.project))
grill=str(Path('_build/issue443-tools/grill').resolve())
summary=[]
built=[]
for physical in config.maps:
    map_id=physical.id
    cfg=replace(base,source_map=physical.source_map,manifest=physical.source_manifest)
    root=config.project/'_build/issue443-packaged'/map_id
    m.validate_inputs(cfg,grill)
    previous=root/(map_id+'.w3x')
    previous_identity=root/'compile/map'/cfg.source_map.name/'runtime/build-identity.json'
    if previous.is_file() and previous_identity.is_file() and json.loads(previous_identity.read_text())==identity:
        c._inspect_physical_map(physical,previous)
        built.append((physical,previous))
        print('REUSED verified physical map:',map_id,flush=True)
        continue
    if root.exists(): shutil.rmtree(root)
    generated=root/'generated'
    m.generate(cfg,generated)
    c._localize_runtime(config,world,physical,generated)
    c._inspect_audio_runtime(physical,generated)
    m.verify_generated(cfg,generated)
    c._validate_budget(cfg,physical,generated)
    compiled=m._assemble(cfg,root,generated,physical.terrain_ids,include_tests=False)
    (compiled/'map'/cfg.source_map.name/'runtime/build-identity.json').write_text(json.dumps(identity)+'\n')
    if physical.bootstrap:
        shutil.copy2(config.project.parent/'_shared/wurst-bootstrap/Bootstrap.wurst',compiled/'wurst/Bootstrap.wurst')
        c._retain_bootstrap_dependencies(compiled)
    runtime=json.loads((generated/m.GENERATED_DATA).read_text())
    materialize(config.project,compiled/'map'/cfg.source_map.name,generated,physical,runtime)
    m._run('offline dependency and typecheck',[grill,'install'],compiled)
    m._run('pinned physical map build',[grill,'build',str(Path('map')/cfg.source_map.name)],compiled)
    archive=m._find_archive(compiled/'_build')
    m._inspect(cfg,archive,compiled,physical.terrain_ids)
    c._inspect_physical_map(physical,archive)
    destination=root/(map_id+'.w3x')
    c._write_browser_safe_w3x(archive,destination)
    built.append((physical,destination))
    summary.append(dict(mapId=map_id,archive=str(destination),navigation='bootstrap' if physical.bootstrap else 'verified_against_packaged_wpm',movementClasses=0 if physical.bootstrap else 4,anchors=[len(n['anchors']) for n in runtime.get('recoveryNavigation',{}).get(map_id,[])]))
    print('PASS packaged navigation:',map_id,flush=True)
Path('_build/issue443-packaging.json').write_text(json.dumps(summary,indent=2)+'\n')

if source_identity(config.project, source_revision(config.project)) != identity:
    raise RuntimeError('sources changed during diagnostic build')
c._write_campaign(config.output,config,built)
c.inspect_campaign(config,config.output)
print('PASS diagnostic campaign:',config.output,flush=True)
