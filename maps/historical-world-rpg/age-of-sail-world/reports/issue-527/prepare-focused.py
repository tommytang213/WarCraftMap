"""Prepare a focused assembly, never a full-suite release evidence claim.

Usage: python3 reports/issue-527/prepare-focused.py PATH_TO_WURST_STDLIB
Run from the Age of Sail project. The library argument is cached source only;
no predecessor execution report or compiled artifact is consumed.
"""
from pathlib import Path
import json
import hashlib
import shutil
import sys

project = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project.parent / '_shared/tooling'))
from package_wurst_map import load_config, generate, verify_generated, _assemble
from integration_evidence import instrument_tree, load_contract, source_identity
from wurst_execution import discover, select_tests, input_hashes, source_revision

root = project / '_build/issue-527'
for name in ('generated', 'compile'):
    if (root / name).exists():
        shutil.rmtree(root / name)
config = load_config(project / 'package.json')
generate(config, root / 'generated')
verify_generated(config, root / 'generated')
compile_root = _assemble(config, root, root / 'generated')
keep = {'ScienceExplorationTests.wurst', 'ResearchRuntimeTests.wurst', 'CampaignLoadTransactionTests.wurst',
        'ResearchCostTests.wurst', 'FrameworkConformanceTests.wurst'}
for path in (compile_root / 'wurst').glob('*.wurst'):
    if path.name not in keep:
        path.write_text(select_tests(path.read_text(), set()))
instrument_tree(compile_root, load_contract(project))
(compile_root / '_build/dependencies').mkdir(parents=True)
if len(sys.argv) > 1:
    shutil.copytree(sys.argv[1], compile_root / '_build/dependencies/WurstStdlib2')
(root / 'expected.json').write_text(json.dumps(discover(compile_root), indent=2) + '\n')
inputs = input_hashes(compile_root)
inputs.update({p.relative_to(compile_root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in (compile_root / '_build/dependencies').rglob('*') if p.is_file()})
(root / 'inputs.json').write_text(json.dumps(inputs, indent=2) + '\n')
(compile_root / 'inputs.sha256').write_text(''.join(f'{value}  {name}\n' for name, value in sorted(inputs.items())))
(root / 'source-identity.json').write_text(json.dumps(source_identity(project, source_revision(project)), indent=2) + '\n')
print('Prepared', len(discover(compile_root)), 'focused tests', flush=True)
