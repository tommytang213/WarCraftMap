#!/usr/bin/env python3
"""Run pinned builds using dependencies from an existing Grill compile tree.

Only dependency installation is replaced by a local copy. Compilation, tests,
packaging and inspection use the production builders and the supplied Grill.
Usage: revalidate-offline.py campaign|conformance COMPILE_TREE GRILL
"""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
from unittest.mock import patch

PROJECT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT.parent / '_shared/tooling'))
import package_wurst_campaign as campaign
import package_wurst_map as maps
from validate_framework_fixture import validate_fixture
from wurst_execution import canonical, source_revision

mode, cached_tree, grill = sys.argv[1:]
assert mode in ('campaign', 'conformance'), mode
cache = Path(cached_tree).resolve() / '_build'
grill = str(Path(grill).resolve())
stdlib = cache / 'dependencies/wurstStdlib2'
assert {path.name for path in (cache / 'dependencies').iterdir()} == {'wurstStdlib2'}
assert not subprocess.check_output(['git', '-C', str(stdlib), 'status', '--porcelain']).strip()
stdlib_revision = subprocess.check_output(['git', '-C', str(stdlib), 'rev-parse', 'HEAD'], text=True).strip()
core = ['common.j', 'blizzard.j', 'core-jass.provenance']
files = [path for path in stdlib.rglob('*') if path.is_file() and '.git' not in path.parts]
files += [cache / name for name in core]
inputs = {path.relative_to(cache).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
          for path in sorted(files)}
print(json.dumps({'sourceRevision': source_revision(PROJECT), 'mode': mode,
                  'dependencyRevision': stdlib_revision,
                  'dependencyInputSetSha256': hashlib.sha256(canonical(inputs)).hexdigest(),
                  'dependencyFiles': len(inputs)}, sort_keys=True), flush=True)
run = maps._run


def offline_run(stage, command, cwd):
    print(stage, flush=True)
    if command[1:] == ['install']:
        # Refuse a new dependency rather than silently supplying an incomplete
        # cache. Core JASS comes from the same previously installed v3.0 tree.
        build = (cwd / 'wurst.build').read_text()
        assert build.count('https://') == 1 and 'https://github.com/wurstscript/WurstStdlib2' in build
        assert 'wc3Patch: v3.0' in build
        target = cwd / '_build'
        target.mkdir(exist_ok=True)
        shutil.copytree(cache / 'dependencies', target / 'dependencies')
        # The online installer normalizes the URL's repository casing. Keep
        # the authored build file and match its dependency directory instead.
        (target / 'dependencies/wurstStdlib2').rename(target / 'dependencies/WurstStdlib2')
        for name in core:
            shutil.copy2(cache / name, target / name)
        for relative, expected in inputs.items():
            installed = relative.replace('dependencies/wurstStdlib2/', 'dependencies/WurstStdlib2/', 1)
            assert hashlib.sha256((target / installed).read_bytes()).hexdigest() == expected
    else:
        run(stage, command, cwd)


with patch.object(maps, '_run', offline_run), patch.object(campaign, '_run', offline_run):
    if mode == 'campaign':
        campaign.build_campaign(PROJECT / 'physical-maps.json', grill=grill)
    else:
        assert shutil.which('grill') == grill, 'Put the supplied Grill directory first on PATH'
        validate_fixture(PROJECT.parent / 'conformance-campaign')
