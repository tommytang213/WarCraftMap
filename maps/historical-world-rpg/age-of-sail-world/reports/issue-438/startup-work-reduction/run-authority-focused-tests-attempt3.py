#!/usr/bin/env python3
"""Focused current-source authority regressions; no native/release acceptance."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import sys

BASE = Path('/workspace/scratch/243ebc79fa0a')
PROJECT = BASE / 'WarCraftMap/maps/historical-world-rpg/age-of-sail-world'
OUTPUT = Path(__file__).resolve().parent / 'authority-focused-attempt3'
ROOT = OUTPUT / 'compile'
SEED = BASE / 'pinned-wurst/WurstStdlib2'
GENERATED_SEED = BASE / 'validation-536/continue-fix/test-seed'
EXPECTED_DEPENDENCY = 'cce79096e71dcb066cf94785bc5cb48ef66c26db'
sys.path.insert(0, str(PROJECT.parent / '_shared/tooling'))
from integration_evidence import execution_sources, source_identity
from wurst_execution import discover, execute_tests, select_tests, input_hashes

FAMILIES = {'CampaignAuthorityPerformanceTests.wurst', 'PlayableCampaignRuntimeTests.wurst'}
FROZEN = {
    PROJECT.parent / '_shared/wurst/PlayableCampaignRuntime.wurst': '47a9f534d29d23a0542df28f9e5b6701fe759793d9a4857f234143c3ac8f43cc',
    PROJECT / 'wurst/CampaignAuthorityPerformanceTests.wurst': 'c66195704cd69c9723e7f67ce7923795eb56a14aab29f6190e1fb0134381e612',
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dependencies(path):
    return {str(p.relative_to(path)): sha(p) for p in sorted(path.rglob('*.wurst')) if '.git' not in p.parts}


def main():
    if OUTPUT.exists():
        raise RuntimeError('Preserve previous evidence; use a fresh focused run directory')
    assert {p: sha(p) for p in FROZEN} == FROZEN
    revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=PROJECT, text=True).strip()
    context = {
        'scope': 'focused dirty-source developer regression; no campaign/native/release acceptance',
        'baselineRevision': revision,
        'sourceIdentityAtAssembly': source_identity(PROJECT, revision),
        'frozenSourceInputs': {str(p): value for p, value in FROZEN.items()},
        'selectedFamilies': sorted(FAMILIES), 'nativeStatus': 'not_run',
        'repositoryTestAnnotationsModified': False, 'releaseGateModified': False,
        'dependencySeed': str(SEED), 'dependencyInstallInvoked': False,
    }
    assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=SEED, text=True).strip() == EXPECTED_DEPENDENCY
    assert not subprocess.check_output(['git', 'status', '--porcelain', '--untracked-files=no'], cwd=SEED, text=True).strip()
    dependency = ROOT / '_build/dependencies/WurstStdlib2'
    shutil.copytree(SEED, dependency)
    source_inputs = execution_sources(PROJECT)
    context['authoredWurstInputs'] = {relative: sha(path) for relative, path in sorted(source_inputs.items())}
    for relative, source in source_inputs.items():
        target = ROOT / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    for name in ('wurst.build', 'wurst_run.args'):
        shutil.copy2(PROJECT / name, ROOT / name)
    context['generatedSeedInputs'] = {}
    for relative in ('wurst/ScenarioData.wurst', 'wurst/ScenarioSettings.wurst', 'wurst/ConformanceData.wurst',
                     '_build/common.j', '_build/blizzard.j'):
        assert relative not in source_inputs
        source = GENERATED_SEED / relative
        target = ROOT / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        context['generatedSeedInputs'][relative] = {'path': str(source), 'sha256': sha(source)}
    original_discovery = discover(ROOT)
    selected = [row for row in original_discovery if Path(row['id'].rsplit(':', 1)[0]).name in FAMILIES]
    assert {Path(row['id'].rsplit(':', 1)[0]).name for row in selected} == FAMILIES
    assert sum('CampaignAuthorityPerformanceTests.wurst:' in row['id'] for row in selected) == 6
    context['fullDiscoveryCount'] = len(original_discovery)
    context['selectedCount'] = len(selected)
    context['selectedTests'] = selected
    for path in (ROOT / 'wurst').rglob('*.wurst'):
        names = {row['id'].rsplit(':', 1)[1] for row in selected if ROOT / row['id'].rsplit(':', 1)[0] == path}
        path.write_text(select_tests(path.read_text(), names))
    assert discover(ROOT) == selected
    context['dependencyRevision'] = EXPECTED_DEPENDENCY
    context['dependencyInputsBefore'] = dependencies(dependency)
    before = input_hashes(ROOT)
    context['interpreterInputsBefore'] = before
    path = OUTPUT / 'focused-context.json'
    path.write_text(json.dumps(context, indent=2, sort_keys=True) + '\n')
    os.environ['JAVA_TOOL_OPTIONS'] = '-Xmx6g'
    print(f'Running {len(selected)} authority regressions from {len(original_discovery)} discovered tests', flush=True)
    try:
        result = execute_tests(ROOT, str(BASE / 'pinned-wurst/grill'), OUTPUT, revision)
        assert input_hashes(ROOT) == before
        assert {relative: sha(p) for relative, p in sorted(source_inputs.items())} == context['authoredWurstInputs']
        assert dependencies(dependency) == context['dependencyInputsBefore']
        context.update(status=result['status'], discovered=result['discovered'], succeeded=result['succeeded'],
                       dependencyInputsUnchanged=True, interpreterInputsUnchanged=True, authoredWurstUnchanged=True)
    except Exception as error:
        context.update(status='fail', error=str(error))
        raise
    finally:
        path.write_text(json.dumps(context, indent=2, sort_keys=True) + '\n')


if __name__ == '__main__':
    main()
