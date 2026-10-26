#!/usr/bin/env python3
"""Compile one actual Europe map under pinned tools; no player distribution."""
from pathlib import Path
from dataclasses import replace
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time

BASE = Path('/workspace/scratch/243ebc79fa0a')
ROOT = BASE / 'validation-536/continue-fix'
REVISION = '264b34c9a0762bdadda377fb10cb44a63af33052'
BASELINE_REPO = ROOT / 'baseline-source'
BASELINE_PROJECT = BASELINE_REPO / 'maps/historical-world-rpg/age-of-sail-world'
CURRENT_PROJECT = BASE / 'WarCraftMap/maps/historical-world-rpg/age-of-sail-world'
LAUNCHER = BASE / 'pinned-wurst/grill'
DEPENDENCY = BASE / 'pinned-wurst/WurstStdlib2'
PINNED_DEPENDENCY = 'cce79096e71dcb066cf94785bc5cb48ef66c26db'
sys.path.insert(0, str(BASELINE_PROJECT.parent / '_shared/tooling'))
from integration_evidence import execution_sources, source_identity
from wurst_execution import input_hashes, compiler_identity, toolchain_environment, PINNED_COMPILER_SHA256, PINNED_IMAGE
from package_wurst_map import load_config, generate, verify_generated, _assemble, _inspect, _find_archive
from package_wurst_campaign import load_campaign_config, validate_campaign, _localize_runtime, _inspect_audio_runtime, _validate_budget, _inspect_physical_map
from materialize_physical_map import materialize
from warcraft_campaign import MpqReader
from independent_mpq import load_reader, open_archive, read_member

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def identity(path):
    return {'path': str(path), 'bytes': path.stat().st_size, 'sha256': sha(path)}

def tree(path):
    return {p.relative_to(path).as_posix(): sha(p) for p in sorted(path.rglob('*'))
            if p.is_file() and '.git' not in p.relative_to(path).parts}

def write(path, data):
    path.write_text(json.dumps(data, sort_keys=True, indent=2) + '\n')

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['baseline', 'revised', 'combined'])
    parser.add_argument('--prepared-from', type=Path)
    args = parser.parse_args()
    assert args.mode == 'combined', 'This runner only retries the frozen combined compile'
    out = ROOT / 'europe-combined-retry'
    assert not out.exists(), 'Preserve the previous attempt'
    out.mkdir(parents=True)
    runner_copy = out / 'build-runner.py'
    shutil.copy2(Path(__file__), runner_copy)
    compile_root = out / 'compile'
    project = BASELINE_PROJECT if args.mode == 'baseline' else CURRENT_PROJECT
    config = load_campaign_config(BASELINE_PROJECT / 'physical-maps.json')
    physical = next(p for p in config.maps if p.id == 'europe_central_east')
    base_config = load_config(config.map_config_path)
    map_config = replace(base_config, source_map=physical.source_map, manifest=physical.source_manifest)
    compiler = BASE / 'pinned-wurst/rootfs/home/wurstuser/.wurst/wurst-compiler/wurstscript.jar'
    assert sha(compiler) == PINNED_COMPILER_SHA256
    assert subprocess.check_output(['git','rev-parse','HEAD'], cwd=DEPENDENCY, text=True).strip() == PINNED_DEPENDENCY
    assert not subprocess.check_output(['git','status','--porcelain'], cwd=DEPENDENCY, text=True).strip()
    source_at_start = source_identity(project, REVISION)
    assert source_at_start['sourceTreeSha256'] == 'b69fd4f0100a2a9f5f5e4c266e4e68ee3e35af3dc5be91d010be9b325e97b62d', 'Frozen combined source changed'
    active_compilers = []
    for proc in Path('/proc').iterdir():
        if not proc.name.isdigit():
            continue
        try:
            command = (proc/'cmdline').read_bytes().split(b'\0')
        except (OSError, PermissionError):
            continue
        if command and command[0].endswith(b'/java') and any(arg.endswith(b'/wurstscript.jar') for arg in command):
            active_compilers.append(proc.name)
    assert not active_compilers, f'Wait for other compiler JVMs to finish: {active_compilers}'
    receipt = {
        'format': 'continue_fix_isolated_europe_compile_v1', 'status': 'running',
        'baselineRevision': REVISION, 'mode': args.mode, 'sourceIdentityAtAssembly': source_at_start,
        'sourcePolicy': ('Exact git archive of published revision' if args.mode == 'baseline' else
                         'Dirty working source; retain baseline generated/map inputs and replace authored production files'),
        'nativeStatus': 'not_run', 'playerArtifactProduced': False,
        'executionEnvironment': 'Exact verified extracted compiler/runtime on workspace host; full OCI image not run',
        'expectedImage': PINNED_IMAGE, 'compilerSha256': sha(compiler),
        'runner': identity(runner_copy),
        'dependencyRevision': PINNED_DEPENDENCY, 'dependencyInstallInvoked': False,
        'retryOf': identity(ROOT/'europe-combined/build-result.json'),
        'retryReason': 'Previous combined compiler process exit137 coincided with shared cgroup OOM; run alone with unchanged heap and inputs',
        'cgroupBefore': {name: (Path('/sys/fs/cgroup')/name).read_text() for name in ['memory.max','memory.current','memory.events','memory.peak']},
        'stages': [],
    }
    began = time.monotonic()
    try:
        if args.mode == 'baseline' and args.prepared_from:
            prepared_receipt = json.loads((args.prepared_from/'build-result.json').read_text())
            assert prepared_receipt['sourceIdentityAtAssembly'] == source_at_start
            original_inputs = json.loads((args.prepared_from/'inputs-before.json').read_text())
            assert input_hashes(args.prepared_from/'compile') == original_inputs
            shutil.copytree(args.prepared_from/'compile', compile_root)
            shutil.copytree(args.prepared_from/'generated', out/'generated')
            receipt['preparedAssembly'] = str(args.prepared_from)
            receipt['previousAttempt'] = 'Preserved zero-test compiler-spawn failure caused by extracted jspawnhelper mode; exact image mode restored'
        elif args.mode == 'baseline':
            world = validate_campaign(config)
            generated = out / 'generated'
            generate(map_config, generated)
            _localize_runtime(config, world, physical, generated)
            _inspect_audio_runtime(physical, generated)
            verify_generated(map_config, generated)
            _validate_budget(map_config, physical, generated)
            assembled = _assemble(map_config, out, generated, physical.terrain_ids, include_tests=False)
            assert assembled == compile_root
            (compile_root/'map'/map_config.source_map.name/'runtime/build-identity.json').write_text(json.dumps(source_at_start,sort_keys=True)+'\n')
            runtime = json.loads((generated/'scenario-runtime.json').read_text())
            materialize(config.project, compile_root/'map'/map_config.source_map.name, generated, physical, runtime)
            shutil.copytree(DEPENDENCY, compile_root/'_build/dependencies/WurstStdlib2')
            for name in ['common.j','blizzard.j']:
                shutil.copy2(ROOT/'test-seed/_build'/name, compile_root/'_build'/name)
        else:
            seed = ROOT/'europe-baseline/compile'
            original = json.loads((ROOT/'europe-baseline/build-result.json').read_text())
            assert original['status'] == 'pass'
            shutil.copytree(seed, compile_root)
            for p in (compile_root/'_build').glob('*.w3x'):
                p.unlink()
            authored = execution_sources(CURRENT_PROJECT)
            changed = []
            for p in sorted((compile_root/'wurst').glob('*.wurst')):
                if p.name in {'ScenarioData.wurst','ScenarioSettings.wurst'}:
                    continue
                key = 'wurst/' + p.name
                assert key in authored, key
                before, after = sha(p), sha(authored[key])
                if before != after:
                    changed.append({'file': key, 'before': before, 'after': after})
                    shutil.copy2(authored[key], p)
            expected_changes = {'wurst/PlayableCampaignRuntime.wurst'}
            if args.mode == 'combined':
                expected_changes.add('wurst/MilitarySettlementRuntime.wurst')
            assert {x['file'] for x in changed} == expected_changes, changed
            receipt['changedProductionInputs'] = changed
            receipt['mapMetadataIdentity'] = 'Baseline 264b metadata retained; developer artifact, not distributable'
        dep_root = compile_root/'_build/dependencies/WurstStdlib2'
        dependency_before = tree(dep_root)
        inputs = input_hashes(compile_root)
        receipt['mapInputs'] = tree(compile_root/'map')
        receipt['generatedInputs'] = {p.name: sha(p) for p in (compile_root/'wurst').glob('Scenario*.wurst')}
        write(out/'inputs-before.json', inputs)
        write(out/'dependency-before.json', dependency_before)
        write(out/'build-result.json', receipt)
        os.environ['JAVA_TOOL_OPTIONS'] = '-Xmx6g'
        for stage, arguments in [('typecheck',['typecheck']), ('build',['build','map/'+map_config.source_map.name])]:
            command = [str(LAUNCHER), *arguments]
            print(f'{args.mode}: {stage}', flush=True)
            started = time.monotonic()
            result = subprocess.run(command, cwd=compile_root, env=toolchain_environment(), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            log = out/(stage+'.log'); log.write_text(result.stdout)
            row = {'stage':stage,'command':command,'exitCode':result.returncode,'wallSeconds':round(time.monotonic()-started,6),'log':identity(log)}
            receipt['stages'].append(row)
            write(out/'build-result.json', receipt)
            assert result.returncode == 0, f'{stage} failed; inspect {log}'
            row['compiler'] = compiler_identity(result.stdout)
            row['inputsUnchanged'] = input_hashes(compile_root) == inputs
            assert row['inputsUnchanged']
            assert tree(dep_root) == dependency_before
        archive = _find_archive(compile_root/'_build')
        _inspect(map_config, archive, compile_root, physical.terrain_ids)
        _inspect_physical_map(physical, archive)
        own = MpqReader(archive)
        independent = open_archive(load_reader(BASE/'validation-536/mpyq-reviewed.py'), archive.read_bytes())
        extracted = {}
        for name in ['war3map.lua','war3map.wpm','war3map.w3i','runtime/build-identity.json']:
            payload = own.read(name)
            assert payload == read_member(independent, name)
            target = out/name; target.parent.mkdir(parents=True,exist_ok=True); target.write_bytes(payload)
            extracted[name] = identity(target)
        assert (compile_root/'_build/02_compiled.lua').read_bytes() == (out/'war3map.lua').read_bytes()
        assert source_identity(project, REVISION) == source_at_start
        write(out/'inputs-after.json', input_hashes(compile_root))
        receipt.update(status='pass',archive=identity(archive),extracted=extracted,independentKnownMembersEqual=True,
                       compilerOutputEqualsArchiveLua=True,authoredSourcesUnchanged=True,
                       compiledScript=str(out/'war3map.lua'),compiledScriptSha256=sha(out/'war3map.lua'),compiledScriptBytes=(out/'war3map.lua').stat().st_size)
    except BaseException as error:
        receipt.update(status='fail',error=f'{type(error).__name__}: {error}')
        raise
    finally:
        receipt['wallSeconds'] = round(time.monotonic()-began,6)
        receipt['cgroupAfter'] = {name: (Path('/sys/fs/cgroup')/name).read_text() for name in ['memory.max','memory.current','memory.events','memory.peak']}
        write(out/'build-result.json', receipt)
    print(json.dumps({k:receipt[k] for k in ['mode','status','compiledScriptSha256','compiledScriptBytes','wallSeconds']},indent=2))

if __name__ == '__main__':
    main()
