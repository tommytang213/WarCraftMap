"""Inspect the actual pinned uninstrumented W3X, separate from execution proof."""
from pathlib import Path
import gzip
import json
import re
import sys
import tarfile

project = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project.parent / '_shared/tooling'))
from integration_evidence import source_identity
from wurst_execution import sha, PINNED_COMPILER_SHA256
from warcraft_campaign import MpqReader

folder = Path(__file__).resolve().parent
root = project / '_build/issue-548'
identity = json.loads((root / 'source-identity.json').read_text())
assert source_identity(project, identity['sourceRevision']) == identity
shipping = root / 'shipping'
with tarfile.open(shipping / 'map.tar') as archive:
    assert archive.getnames() == ['_build/AgeOfSailWorld.w3x']
    data = archive.extractfile('_build/AgeOfSailWorld.w3x').read()
path = shipping / 'AgeOfSailWorld.w3x'
path.write_bytes(data)
reader = MpqReader(path)
lua = reader.read('war3map.lua').decode()
runtime = json.loads(reader.read('runtime/scenario-runtime.json'))
generated = json.loads((root / 'generated/scenario-runtime.json').read_text())
assert runtime == generated
assert 'WCM_PROBE:' not in lua
assert 'civicPolicyMatchedControlProvesOptionalTransitionFundedDiffusionAndRenewal' not in lua
log = (folder / 'shipping-build.log').read_text()
assert PINNED_COMPILER_SHA256 + '  /home/wurstuser/.wurst/wurst-compiler/wurstscript.jar' in log
assert 'Build succeeded. Output file:' in log

def body(function):
    match = re.search(r'^function ' + re.escape(function) + r'\([^\n]*\)\s*\n(.*?)^end$', lua, re.M | re.S)
    assert match, function
    return match[1]

checks = {}
for kind, ident, metric, bp in [('policy', 'progression_abolitionist_public_sphere', 'civic_reform_diffusion', 500),
                                 ('ability', 'epidemic_control', 'epidemic_losses_avoided', 2500)]:
    pattern = r'\bCivicEffect_construct_CivicEffect\([^,\n]+, "' + kind + '", "' + ident + '", "' + metric + '", ' + str(bp) + ','
    checks[ident] = len(re.findall(pattern, lua)) == 1
checks['commandRegistration'] = '"civic"' in body('registerCivicCommands') and 'when calling registerCivicCommands in Bootstrap,' in lua
checks['registeredActionConsumer'] = 'CivicCampaignRuntime_CivicCampaignRuntime_act(' in body('CivicCommand_CivicCommand_execute')
checks['clockCallback'] = bool(re.search(r'CivicCampaignRuntime_CivicCampaignRuntime_advance\([^\n]+when calling advance in PlayableCampaignRuntime,', lua))
checks['ledgerAdvance'] = 'CivicLedger_CivicLedger_advance(' in body('CivicCampaignRuntime_CivicCampaignRuntime_advance')
checks['actualTreasuryAndStock'] = all(token in body('CampaignCivicEconomy_CampaignCivicEconomy_pay')
                                      for token in ['PlayableCountryInteractionRuntime_treasury_storage', 'RuntimeMarket_stock_storage'])
checks['actualManpowerLoss'] = bool(re.search(r'SettlementRuntimeState_manpower_storage\[[^\n]+ = \(SettlementRuntimeState_manpower_storage\[[^\n]+ - ', body('CampaignCivicEconomy_CampaignCivicEconomy_disease')))
checks['localDiffusionMutation'] = 'when calling diffuse in CivicGovernance,' in body('CivicLedger_CivicLedger_advance')
checks['tradeBudgetConsumer'] = 'when calling tradeAllowed in PlayableTrade,' in lua
checks['bothTradeCommits'] = len(re.findall('when calling recordTrade in PlayableTrade,', lua)) == 2
assert all(checks.values()), checks
report = dict(sourceIdentity=identity, status='pass', mapSha256=sha(data), luaSha256=sha(lua.encode()),
              runtimeSha256=sha(reader.read('runtime/scenario-runtime.json')), checks=checks,
              districtCount=runtime['civicGovernance']['districtCount'],
              inspection='Actual pinned uninstrumented shipping W3X and its archived Lua/runtime, one map. Full localized campaign validation remains with controller.',
              nativeClient='not_run', fullCampaignReleaseEvidence=False)
(folder / 'packaged-registration.json').write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
(folder / 'shipping-build.log.gz').write_bytes(gzip.compress(log.encode(), mtime=0))
print(json.dumps(report, indent=2))
