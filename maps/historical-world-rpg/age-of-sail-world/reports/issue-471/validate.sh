set -eu
mkdir -p /tmp/issue471
cd /source
tar --exclude=.git --exclude=./.agents --exclude=./.aws --exclude=./.codex --exclude=_build --exclude=__pycache__ -cf - maps automation .github AGENTS.md | tar -C /tmp/issue471 -xf -
mkdir -p /tmp/issue471-tools
cp /dependencies/usr/bin/python3.14 /tmp/issue471-tools/python3
export PYTHONHOME=/dependencies/usr
export PATH=/tmp/issue471-tools:/home/wurstuser/.wurst:$PATH
cat > /tmp/issue471-tools/grill <<'GRILL'
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
chmod +x /tmp/issue471-tools/grill
cd /tmp/issue471/maps/historical-world-rpg/age-of-sail-world
python3 - <<'CHECK'
import os, sys, re, subprocess, shutil
from pathlib import Path
sys.path.insert(0,'../_shared/tooling')
from package_wurst_map import load_config,generate,_assemble,_run,_find_archive,_inspect
from wurst_execution import execute_tests, toolchain_environment
config=load_config(Path('package.json'));root=Path('_build/issue471')
if root.exists():
    shutil.rmtree(root)
root.mkdir(parents=True)
generate(config,root/'generated');comp=_assemble(config,root,root/'generated')
if os.environ.get('VISITS_TARGETED') == '1':
    keep={'VisitKnowledgeTests.wurst', 'MapDiscoveryScreenTests.wurst', 'PlayableCampaignRuntimeTests.wurst', 'RpgInteractionTests.wurst', 'AuthoredQuestTests.wurst', 'CampaignStartupTests.wurst', 'CampaignLoadTransactionTests.wurst', 'RemoteRegionAuthorityTests.wurst', 'CommandMapTransportTests.wurst', 'ManagementCommandTests.wurst', 'TreasureResolutionTests.wurst', 'TreasureVectorsTests.wurst', 'ResearchRuntimeTests.wurst', 'PlayableTradeTests.wurst', 'TradeCommandTests.wurst', 'TradePricingTests.wurst', 'CampaignAutosaveLifecycleTests.wurst', 'RecruitmentWindowTests.wurst', 'CharacterEquipmentTests.wurst'}
    if os.environ.get('VISITS_SMOKE') == '1':
        keep={'VisitKnowledgeTests.wurst', 'AuthoredQuestTests.wurst', 'ManagementCommandTests.wurst', 'PlayableCampaignRuntimeTests.wurst', 'CommandMapTransportTests.wurst'}
    for p in (comp/'wurst').glob('*.wurst'):
        if p.name not in keep:
            p.write_text(p.read_text().replace('@test',''))
_run('offline dependencies',['/tmp/issue471-tools/grill','install'],comp)
print('Running pinned typecheck',flush=True)
typed = subprocess.run(['/tmp/issue471-tools/grill','typecheck'],cwd=comp,env=toolchain_environment(),stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
(root/'typecheck.log').write_text(typed.stdout)
assert typed.returncode == 0, typed.stdout
if os.environ.get('TYPECHECK_ONLY') == '1':
    sys.exit(0)
if os.environ.get('PACKAGE_ONLY') != '1':
    print('Running pinned execution',flush=True)
    execute_tests(comp,'/tmp/issue471-tools/grill',root/'evidence',os.environ['SOURCE_REVISION'],project=config.project)
if os.environ.get('VISITS_TARGETED') != '1' or os.environ.get('VISITS_PACKAGE') == '1':
    import json, hashlib
    from integration_evidence import source_identity
    identity = source_identity(config.project,os.environ['SOURCE_REVISION'])
    (comp/'map'/config.source_map.name/'runtime/build-identity.json').write_text(json.dumps(identity,sort_keys=True)+'\n')
    print('Building diagnostic package',flush=True)
    _run('diagnostic package',['/tmp/issue471-tools/grill','build',str(Path('map')/config.source_map.name)],comp)
    archive = _find_archive(comp/'_build')
    _inspect(config,archive,comp)
    from warcraft_campaign import MpqReader
    reader = MpqReader(archive)
    packaged = json.loads(reader.read('runtime/scenario-runtime.json'))
    lua = reader.read('war3map.lua').decode()
    expected = json.loads((root/'generated/scenario-runtime.json').read_text())['mapKnowledgeCatalog']
    assert packaged['mapKnowledgeCatalog'] == expected
    assert 'DiscoveryKnowledge_DiscoveryKnowledge_visitSettlement' in lua
    assert 'CampaignMapCommand_CampaignMapCommand_execute' in lua
    report = dict(sourceIdentity=identity,archiveSha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
                  regions=len(expected['regions']),settlements=len(expected['settlements']),
                  catalogueDefinitionsMatch=True,compiledKnowledgeAndCommands=True,nativeClient='not_run',releaseReady=False)
    (root/'packaged-knowledge.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Checking original and mutated framework campaigns',flush=True)
    _run('framework original and content mutation',['python3','../_shared/tooling/validate_framework_fixture.py','../conformance-campaign'],config.project)
CHECK
