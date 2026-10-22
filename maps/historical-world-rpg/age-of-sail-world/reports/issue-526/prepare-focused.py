"""Prepare a focused assembly, never a full-suite release evidence claim.

Usage: python3 reports/issue-526/prepare-focused.py PATH_TO_WURST_STDLIB [--integration-repair]
Run from the Age of Sail project. The library argument is cached source only;
no predecessor execution report or compiled artifact is consumed.
"""
from pathlib import Path
import json
import shutil
import sys

project = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project.parent / '_shared/tooling'))
from package_wurst_map import load_config, generate, verify_generated, _assemble
from integration_evidence import instrument_tree, load_contract
from wurst_execution import discover, select_tests, input_hashes

root = project / '_build/issue-526'
for name in ('generated', 'compile'):
    if (root / name).exists():
        shutil.rmtree(root / name)
config = load_config(project / 'package.json')
generate(config, root / 'generated')
verify_generated(config, root / 'generated')
compile_root = _assemble(config, root, root / 'generated')
keep = {'CharteredCompaniesTests.wurst', 'NavalServicesTests.wurst', 'BankingOperationsTests.wurst', 'TradeFinanceTests.wurst', 'PlayableTradeTests.wurst', 'MixedCargoTests.wurst',
        'ResearchCostTests.wurst', 'FrameworkConformanceTests.wurst'}
repair = '--integration-repair' in sys.argv[2:]
if repair:
    keep |= {'CivicGovernanceTests.wurst', 'ScienceExplorationTests.wurst', 'CampaignLoadTransactionTests.wurst'}
for path in (compile_root / 'wurst').glob('*.wurst'):
    if repair and path.name == 'CampaignLoadTransactionTests.wurst':
        path.write_text(select_tests(path.read_text(), {'lateLoadFailureRestoresMunicipalPolicyUrbanizationAndTreasuryAtomically'}))
    if path.name not in keep:
        path.write_text(select_tests(path.read_text(), set()))
instrument_tree(compile_root, load_contract(project))
(compile_root / '_build/dependencies').mkdir(parents=True)
shutil.copytree(sys.argv[1], compile_root / '_build/dependencies/WurstStdlib2')
(root / 'expected.json').write_text(json.dumps(discover(compile_root), indent=2) + '\n')
(root / 'inputs.json').write_text(json.dumps(input_hashes(compile_root), indent=2) + '\n')
print('Prepared', len(discover(compile_root)), 'focused tests', flush=True)
