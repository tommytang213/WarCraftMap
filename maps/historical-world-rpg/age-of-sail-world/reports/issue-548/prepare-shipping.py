"""Assemble one uninstrumented shipping map for archived registration inspection."""
from pathlib import Path
import json
import shutil
import sys

project = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project.parent / '_shared/tooling'))
from package_wurst_map import _assemble, load_config
from wurst_execution import input_hashes

root = project / '_build/issue-548'
shipping = root / 'shipping'
if shipping.exists():
    shutil.rmtree(shipping)
assembly = _assemble(load_config(project / 'package.json'), shipping, root / 'generated', include_tests=False)
(assembly / '_build/dependencies').mkdir(parents=True)
shutil.copytree(root / 'compile/_build/dependencies/WurstStdlib2', assembly / '_build/dependencies/WurstStdlib2')
(shipping / 'inputs.json').write_text(json.dumps(input_hashes(assembly), indent=2) + '\n')
assert not any('WCM_PROBE:' in path.read_text() for path in (assembly / 'wurst').rglob('*.wurst'))
print('Prepared uninstrumented shipping assembly')
