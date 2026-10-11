set -eu
mkdir -p /tmp/issue465
cd /source
tar --exclude=.git --exclude=./.agents --exclude=./.aws --exclude=./.codex --exclude=_build --exclude=__pycache__ -cf - maps automation .github AGENTS.md | tar -C /tmp/issue465 -xf -
mkdir -p /tmp/issue465-tools
cp /dependencies/usr/bin/python3.14 /tmp/issue465-tools/python3
export PYTHONHOME=/dependencies/usr
export PATH=/tmp/issue465-tools:/home/wurstuser/.wurst:$PATH
cat > /tmp/issue465-tools/grill <<'GRILL'
#!/bin/sh
set -eu
mkdir -p _build/dependencies
if [ ! -d _build/dependencies/WurstStdlib2 ]; then
  cp -R /dependencies/tmp/issue383-package/age-of-sail-world/_build/compile/_build/dependencies/wurstStdlib2 _build/dependencies/WurstStdlib2
fi
if [ "$1" = install ]; then
  printf '%s\n' "$PWD/_build/dependencies/WurstStdlib2" > wurst.dependencies
  python3 - <<'CORE'
from pathlib import Path
from zipfile import ZipFile
jar=ZipFile('/home/wurstuser/.wurst/grill-cli/grill.jar')
for name in ('common.j','blizzard.j'):
    Path('_build',name).write_bytes(jar.read('core-jass/v3.0/'+name))
CORE
  exit 0
fi
exec /home/wurstuser/.wurst/grill "$@"
GRILL
chmod +x /tmp/issue465-tools/grill
cd /tmp/issue465/maps/historical-world-rpg/age-of-sail-world
python3 - <<'CHECK'
import os, sys, re, subprocess
from pathlib import Path
sys.path.insert(0,'../_shared/tooling')
from package_wurst_map import load_config,generate,_assemble,_run,_find_archive,_inspect
from wurst_execution import execute_tests, toolchain_environment
config=load_config(Path('package.json'));root=Path('_build/issue465');root.mkdir(parents=True,exist_ok=True)
generate(config,root/'generated');comp=_assemble(config,root,root/'generated')
if os.environ.get('TREASURE_TARGETED') == '1':
    keep={'TreasureResolutionTests.wurst', 'TreasureVectorsTests.wurst', 'RpgInteractionTests.wurst', 'CampaignStartupTests.wurst', 'CampaignLoadTransactionTests.wurst', 'WarcraftRpgRuntimeTests.wurst', 'LiveRecoveryTests.wurst', 'HeroEarnedGrowthTests.wurst', 'CharacterEquipmentTests.wurst', 'EquipmentSetTests.wurst'}
    for p in (comp/'wurst').glob('*.wurst'):
        if p.name not in keep:
            p.write_text(p.read_text().replace('@test',''))
_run('offline dependencies',['/tmp/issue465-tools/grill','install'],comp)
print('Running pinned typecheck',flush=True)
typed = subprocess.run(['/tmp/issue465-tools/grill','typecheck'],cwd=comp,env=toolchain_environment(),stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
(root/'typecheck.log').write_text(typed.stdout)
assert typed.returncode == 0, typed.stdout
print('Running pinned execution',flush=True)
execute_tests(comp,'/tmp/issue465-tools/grill',root/'evidence',os.environ['SOURCE_REVISION'],project=config.project)
if os.environ.get('TREASURE_TARGETED') != '1' or os.environ.get('TREASURE_PACKAGE') == '1':
    import json, hashlib
    from integration_evidence import source_identity
    identity = source_identity(config.project,os.environ['SOURCE_REVISION'])
    (comp/'map'/config.source_map.name/'runtime/build-identity.json').write_text(json.dumps(identity,sort_keys=True)+'\n')
    print('Building diagnostic package',flush=True)
    _run('diagnostic package',['/tmp/issue465-tools/grill','build',str(Path('map')/config.source_map.name)],comp)
    archive = _find_archive(comp/'_build')
    _inspect(config,archive,comp)
    from warcraft_campaign import MpqReader
    reader = MpqReader(archive)
    packaged = json.loads(reader.read('runtime/scenario-runtime.json'))
    lua = reader.read('war3map.lua').decode()
    expected = json.loads((root/'generated/scenario-runtime.json').read_text())['treasureResolutionCatalog']
    assert packaged['treasureResolutionCatalog'] == expected
    assert 'TreasureRuntime_TreasureRuntime_resolveAll' in lua
    report = dict(sourceIdentity=identity,archiveSha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
                  treasures=len(expected['treasures']),candidates=len(expected['candidateLocations']),
                  candidateDefinitionsMatch=True,compiledResolver=True,nativeClient='not_run',releaseReady=False)
    (root/'packaged-treasures.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Checking original and mutated framework campaigns',flush=True)
    _run('framework original and content mutation',['python3','../_shared/tooling/validate_framework_fixture.py','../conformance-campaign'],config.project)
CHECK
