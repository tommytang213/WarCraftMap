"""Prepare fresh focused tests; this cannot produce full release evidence."""
from pathlib import Path
import sys,json,hashlib,shutil
project=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(project.parent/'_shared/tooling'),str(project/'tooling')]
from package_wurst_map import load_config,generate,verify_generated,_assemble
from wurst_execution import discover,select_tests,input_hashes,source_revision
from integration_evidence import instrument_tree,load_contract,source_identity
root=project/'_build/issue-563'
root.mkdir(parents=True,exist_ok=True)
for name in ('generated','compile'):
 if (root/name).exists(): shutil.rmtree(root/name)
config=load_config(project/'package.json')
generate(config,root/'generated');verify_generated(config,root/'generated')
assembly=_assemble(config,root,root/'generated',terrain_ids=())
keep={'LandArmyEffectsTests.wurst','ResearchRuntimeTests.wurst','ResearchCostTests.wurst','FrameworkConformanceTests.wurst'}
partial={'CampaignLoadTransactionTests.wurst':{'lateLoadFailureRestoresLandArmyScienceWorkAndFiringClock','rejectedLoadsRestoreTypedResearchLayersForEveryController'},'MilitaryCombatEventsTests.wurst':{'installedLandDrillAndBayonetUseProductionWeaponCallbacks','bayonetSaveLoadTransferMigrationAndLateRollbackKeepCurrentDefense','disciplineAddsToContinuousExactRatingsBeforeOneDefensiveDivision','castCannonComposesExactTraditionRefitAndAbstractRatings','nativeTypedLayerReplacementKeepsUnrelatedModifiersAndLoadCheckpoint','castCannonRegisteredResearchChangesQualifiedGameplayExactlyOnce'}}
for source in (assembly/'wurst').glob('*.wurst'):
 if source.name in partial: source.write_text(select_tests(source.read_text(),partial[source.name]))
 elif source.name not in keep: source.write_text(select_tests(source.read_text(),set()))
instrument_tree(assembly,load_contract(project))
(root/'expected.json').write_text(json.dumps(discover(assembly),indent=2)+'\n')
inputs=input_hashes(assembly)
(assembly/'inputs.sha256').write_text(''.join(f'{v}  {k}\n' for k,v in sorted(inputs.items())))
(root/'inputs.json').write_text(json.dumps(inputs,indent=2)+'\n')
(root/'source-identity.json').write_text(json.dumps(source_identity(project,source_revision(project)),indent=2)+'\n')
(root/'run.sh').write_text('''set -eu
export JAVA_TOOL_OPTIONS=-Xmx8g
cp -R /source/compile /tmp/compile
cd /tmp/compile
printf '%s  /home/wurstuser/.wurst/wurst-compiler/wurstscript.jar\\n' '1f3ae40b1018b8757867515596adfa69113ca85f390c1b353cc8b69cf8944145' | sha256sum -c -
mkdir -p _build/dependencies /tmp/core
cp -R /stdlib _build/dependencies/WurstStdlib2
printf '%s\\n' /tmp/compile/_build/dependencies/WurstStdlib2 > wurst.dependencies
(cd /tmp/core && jar xf /home/wurstuser/.wurst/grill-cli/grill.jar core-jass/v3.0/common.j core-jass/v3.0/blizzard.j)
cp /tmp/core/core-jass/v3.0/common.j _build/common.j
cp /tmp/core/core-jass/v3.0/blizzard.j _build/blizzard.j
sha256sum -c inputs.sha256
grill typecheck
grill test
sha256sum -c inputs.sha256
''')
print(root, len(discover(assembly)),flush=True)
