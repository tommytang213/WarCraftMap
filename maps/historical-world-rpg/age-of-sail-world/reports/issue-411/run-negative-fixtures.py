#!/usr/bin/env python3
"""Execute registration/callback mutants using an already installed compile tree.

Usage: python3 run-negative-fixtures.py COMPILE_TREE GRILL OUTPUT_DIRECTORY
The input is copied. Only disposable copies are mutated; no receipt from this
negative run is suitable as passing release evidence.
"""
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

PROJECT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT.parent / '_shared/tooling'))
from wurst_execution import toolchain_environment

compile_tree, grill, output = (Path(value).resolve() for value in sys.argv[1:])
output.mkdir(parents=True, exist_ok=True)
mutations = {
    'missing-registration': 'natives.registerChat(chatListener,Player(i),"/",false)',
    'disconnected-callback': 'TriggerAddAction(chatListener,function routeChat)',
}
results = {}
for name, removed in mutations.items():
    root = output / name
    shutil.copytree(compile_tree, root)
    router = root / 'wurst/CommandRouter.wurst'
    original = router.read_text()
    assert original.count(removed) == 1, removed
    router.write_text(original.replace(removed, 'skip'))
    row = {}
    for package in ('CommandRouterTests', 'InstalledCommandHelpTests'):
        process = subprocess.run([str(grill), 'test', package], cwd=root,
                                 stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                 env=toolchain_environment())
        log = process.stdout.decode()
        (output / f'{name}-{package}.log').write_bytes(process.stdout)
        summary = re.search(r'Tests succeeded: (\d+)/(\d+)', log)
        assert summary, log[-4000:]
        row[package] = {'returnCode': process.returncode,
                        'succeeded': int(summary[1]), 'discovered': int(summary[2])}
        if package == 'CommandRouterTests':
            assert process.returncode == 0 and summary[1] == summary[2] == '3', row
        else:
            assert int(summary[1]) < int(summary[2]) and 'FAILED assertion' in log, row
    results[name] = row
(output / 'negative-fixtures.json').write_text(json.dumps(results, indent=2) + '\n')
print(json.dumps(results, indent=2))
