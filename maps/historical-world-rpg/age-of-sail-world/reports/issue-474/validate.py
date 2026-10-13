"""Run pinned offline typecheck and scoped combat/research/lifecycle tests."""
import argparse
from pathlib import Path
import subprocess
import sys
import shutil

PROJECT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT.parent / '_shared/tooling'))
from package_wurst_map import load_config, generate, _assemble, _run
from wurst_execution import execute_tests, source_revision, toolchain_environment

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--grill', type=Path, required=True)
parser.add_argument('--all', action='store_true')
args = parser.parse_args()
root = PROJECT / '_build/issue474'
root.mkdir(parents=True, exist_ok=True)
config = load_config(PROJECT / 'package.json')
generate(config, root / 'generated')
if (root / 'compile').exists():
    shutil.rmtree(root / 'compile')
comp = _assemble(config, root, root / 'generated')
suites = {'MilitaryCombatEventsTests.wurst', 'ResearchRuntimeTests.wurst', 'ResearchCostTests.wurst',
          'CampaignLoadTransactionTests.wurst', 'CampaignStartupTests.wurst', 'MilitarySettlementRuntimeTests.wurst',
          'ExactNaturalTests.wurst', 'ExactRationalTests.wurst', 'CharacterEquipmentTests.wurst', 'EquipmentSetTests.wurst',
          'PlayableCampaignRuntimeTests.wurst', 'FrameworkConformanceTests.wurst'}
if not args.all:
    for path in (comp / 'wurst').glob('*.wurst'):
        if path.name not in suites:
            path.write_text(path.read_text().replace('@test', ''))
grill = str(args.grill.resolve())
_run('offline dependencies', [grill, 'install'], comp)
typed = subprocess.run([grill, 'typecheck'], cwd=comp, env=toolchain_environment(),
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
(root / 'typecheck.log').write_text(typed.stdout)
assert typed.returncode == 0, typed.stdout
print('Pinned typecheck passed', flush=True)
execute_tests(comp, grill, root / 'evidence', source_revision(PROJECT), project=PROJECT)
