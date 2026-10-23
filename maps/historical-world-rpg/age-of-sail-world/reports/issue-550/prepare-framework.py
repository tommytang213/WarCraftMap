"""Assemble fresh original/mutated framework sources for pinned execution."""
from pathlib import Path
import hashlib
import json
import shutil
import sys

project = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project.parent / '_shared/tooling'))
from framework_conformance import mutate_content
from package_wurst_map import generate, verify_generated, load_config, _assemble
from wurst_execution import discover, input_hashes

root = project / '_build/issue-550/framework'
if root.exists():
    shutil.rmtree(root)
root.mkdir(parents=True)
# Only framework consumer content is copied; every implementation is current
# shared source. Cached stdlib is an upstream source dependency, never evidence.
original = root / 'original'
shutil.copytree(project.parent / 'conformance-campaign', original,
                ignore=shutil.ignore_patterns('_build', '__pycache__', '.wurst'))
shutil.copytree(project.parent / '_shared', root / '_shared',
                ignore=shutil.ignore_patterns('__pycache__', '_build'))
mutate_content(original, root / 'mutated')
for name in ('original', 'mutated'):
    scenario = root / name
    config = load_config(scenario / 'package.json')
    build = root / (name + '-build')
    generate(config, build / 'generated')
    verify_generated(config, build / 'generated')
    assembly = _assemble(config, build, build / 'generated')
    (assembly / '_build/dependencies').mkdir(parents=True)
    shutil.copytree(sys.argv[1], assembly / '_build/dependencies/WurstStdlib2')
    expected = discover(assembly)
    assert len(expected) == 3
    (build / 'expected.json').write_text(json.dumps(expected, indent=2) + '\n')
    inputs = input_hashes(assembly)
    inputs.update({p.relative_to(assembly).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                   for p in (assembly / '_build/dependencies').rglob('*') if p.is_file()})
    (build / 'inputs.json').write_text(json.dumps(inputs, indent=2) + '\n')
    (assembly / 'inputs.sha256').write_text(''.join(f'{value}  {path}\n' for path, value in sorted(inputs.items())))
    print(name, len(expected), 'fresh framework tests', flush=True)
