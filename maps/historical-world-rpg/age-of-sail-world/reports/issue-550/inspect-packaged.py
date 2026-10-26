"""Inspect fresh archived Lua/runtime; this is not full campaign release evidence."""
from pathlib import Path
import json,re,sys,tarfile
project=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(project.parent/'_shared/tooling'),str(project/'tooling')]
from warcraft_campaign import MpqReader
from wurst_execution import sha,source_revision,PINNED_COMPILER_SHA256
from integration_evidence import source_identity
from land_army_catalog import CLOSURE_EFFECTS
root=project/'_build/issue-550'
shipping=root/'shipping'
with tarfile.open(shipping/'map.tar') as archive:
    assert archive.getnames()==['_build/AgeOfSailWorld.w3x']
    data=archive.extractfile('_build/AgeOfSailWorld.w3x').read()
path=shipping/'AgeOfSailWorld.w3x';path.write_bytes(data)
reader=MpqReader(path)
lua=reader.read('war3map.lua').decode()
runtime=json.loads(reader.read('runtime/scenario-runtime.json'))
assert runtime==json.loads((root/'generated/scenario-runtime.json').read_text())
assert 'WCM_PROBE:' not in lua and 'landReloadMatchedControl' not in lua
log=(project.parents[2]/'_build/issue-550/shipping-build.log').read_text()
assert PINNED_COMPILER_SHA256 in (shipping/'run.sh').read_text()
assert '/home/wurstuser/.wurst/wurst-compiler/wurstscript.jar: OK' in log
assert 'Map built.' in log

def body(name):
    m=re.search(r'^function '+re.escape(name)+r'\([^\n]*\)\s*\n(.*?)^end$',lua,re.M|re.S)
    assert m,name
    return m[1]
checks={}
for (kind,ident),(_,metric,bp) in CLOSURE_EFFECTS.items():
    pattern=r'\bCivicEffect_construct_CivicEffect\([^,\n]+, "'+kind+'", "'+ident+'", "'+metric+'", '+str(bp)+','
    checks[ident]=len(re.findall(pattern,lua))==1
checks['exactConsumerMetadata']={(e['kind'],e['contentId']) for e in runtime['landArmy']['consumers']}==set(CLOSURE_EFFECTS)
checks['noCandidateGeneratedBlockers']=not(set(CLOSURE_EFFECTS)&{(e['kind'],e['contentId']) for e in runtime['researchIntegrationBlockers']})
checks['bayonetStillBlocked']=('modifier','progression_bayonet_system') in {(e['kind'],e['contentId']) for e in runtime['researchIntegrationBlockers']}
checks['registeredCommand']='when calling registerLandArmyCommands in Bootstrap,' in lua and '"land"' in body('registerLandArmyCommands')
checks['clockAdvance']=bool(re.search(r'LandArmyRuntime_LandArmyRuntime_advance\([^\n]+when calling advance in PlayableCampaignRuntime,',lua))
checks['actualPaidInputs']=all(x in body('LandArmyRuntime_LandArmyRuntime_act') for x in ['CampaignCivicEconomy_CampaignCivicEconomy_pay','SettlementRuntimeState_manpower_storage','SettlementRuntimeState_supply_storage','procurementUpkeepBasisPoints'])
checks['actualWork']='when calling commitWork in LandArmyRuntime,' in body('LandArmyRuntime_LandArmyRuntime_advance')
checks['actualDelivery']=all(x in body('LandArmyRuntime_LandArmyRuntime_commitDelivery') for x in ['RuntimeMarket_stock_storage','RuntimeForce_supply_storage'])
checks['sharedReloadResolution']='landReloadMillis(' in body('MilitarySettlementRuntime_MilitarySettlementRuntime_firearmReloadMillis')
checks['abstractDeadline']='RuntimeForce_nextFireAt_storage' in body('MilitarySettlementRuntime_MilitarySettlementRuntime_acceptLandShot')
checks['nativeUsesSameResolution']='landReloadMillis(' in body('WarcraftMilitarySettlementAdapter_WarcraftMilitarySettlementAdapter_replaceReload')
checks['nativeCooldownCall']='BlzSetUnitAttackCooldown(' in body('WarcraftMilitarySettlementAdapter_WarcraftMilitarySettlementAdapter_setAttackCooldown')
assert all(checks.values()),checks
report=dict(status='pass',sourceIdentity=source_identity(project,source_revision(project)),checks=checks,mapSha256=sha(data),luaSha256=sha(lua.encode()),nativeClient='not_run',fullCampaignReleaseEvidence=False)
Path(__file__).with_name('packaged-registration.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
print(json.dumps(checks,sort_keys=True))
