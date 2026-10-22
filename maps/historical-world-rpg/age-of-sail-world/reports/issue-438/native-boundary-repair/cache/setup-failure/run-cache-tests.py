#!/usr/bin/env python3
"""Focused cache transaction regressions with the unchanged pinned test gate."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import sys

BASE = Path('/workspace/scratch/243ebc79fa0a')
PROJECT = BASE / 'WarCraftMap/maps/historical-world-rpg/age-of-sail-world'
OUTPUT = Path(__file__).resolve().parent / 'cache-focused-tests'
ROOT = OUTPUT / 'compile'
SEED = BASE / 'validation-536/startup-fix/wurst-tests-attempt2/compile'
sys.path.insert(0, str(PROJECT.parent / '_shared/tooling'))
from integration_evidence import execution_sources, source_identity
from wurst_execution import discover, execute_tests, select_tests

FAMILIES = {'CampaignSaveManagerTests.wurst', 'WarcraftCampaignSaveStorageTests.wurst'}
OWNED = [PROJECT.parent / '_shared/wurst/WC3Compatibility.wurst',
         PROJECT.parent / '_shared/wurst/CampaignSaveManager.wurst',
         PROJECT / 'wurst/WarcraftCampaignSaveStorageTests.wurst']


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    if OUTPUT.exists():
        raise RuntimeError('Preserve previous evidence; use a fresh focused run directory')
    revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=PROJECT, text=True).strip()
    context = {
        'scope': 'focused working-tree cache transaction regression; not campaign/native/release acceptance',
        'baselineRevision': revision, 'worktreeDirty': True,
        'sourceIdentityAtAssembly': source_identity(PROJECT, revision),
        'ownedSourceInputs': {str(path): sha(path) for path in OWNED},
        'selectedFamilies': sorted(FAMILIES), 'nativeStatus': 'not_run',
        'repositoryTestAnnotationsModified': False, 'releaseGateModified': False,
        'compileTreeSeed': str(SEED),
    }
    shutil.copytree(SEED, ROOT)
    shutil.rmtree(ROOT / 'wurst')
    for relative, source in execution_sources(PROJECT).items():
        target = ROOT / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    original_discovery = discover(ROOT)
    selected = [row for row in original_discovery
                if Path(row['id'].rsplit(':', 1)[0]).name in FAMILIES]
    assert {Path(row['id'].rsplit(':', 1)[0]).name for row in selected} == FAMILIES
    assert len(selected) == 15
    context['fullDiscoveryCount'] = len(original_discovery)
    context['selectedCount'] = len(selected)
    context['selectedTests'] = selected
    for path in (ROOT / 'wurst').rglob('*.wurst'):
        names = {row['id'].rsplit(':', 1)[1] for row in selected
                 if ROOT / row['id'].rsplit(':', 1)[0] == path}
        path.write_text(select_tests(path.read_text(), names))
    assert discover(ROOT) == selected
    dependency = ROOT / '_build/dependencies/wurstStdlib2'
    context['dependencyRevisionBefore'] = subprocess.check_output(
        ['git', 'rev-parse', 'HEAD'], cwd=dependency, text=True).strip()
    context['dependencyInputsBefore'] = {
        str(path.relative_to(dependency)): sha(path)
        for path in sorted(dependency.rglob('*.wurst')) if '.git' not in path.parts
    }
    (OUTPUT / 'focused-context.json').write_text(json.dumps(context, indent=2) + '\n')
    os.environ['JAVA_TOOL_OPTIONS'] = '-Xmx6g'
    print(f"Running {len(selected)} cache regressions from {len(original_discovery)} discovered tests", flush=True)
    result = execute_tests(ROOT, str(BASE / 'pinned-wurst/grill'), OUTPUT, revision)
    assert {str(path): sha(path) for path in OWNED} == context['ownedSourceInputs']
    assert {str(path.relative_to(dependency)): sha(path)
            for path in sorted(dependency.rglob('*.wurst')) if '.git' not in path.parts} == context['dependencyInputsBefore']
    context.update({'status': result['status'], 'discovered': result['discovered'],
                    'succeeded': result['succeeded'], 'dependencyInputsUnchanged': True,
                    'testedProductionAndRegressionSourcesUnchanged': True})
    (OUTPUT / 'focused-context.json').write_text(json.dumps(context, indent=2) + '\n')


if __name__ == '__main__':
    main()
