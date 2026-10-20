#!/usr/bin/env python3
"""One isolated dirty-source Europe compile with exact compiler/input receipts.

Retains the already generated destination map/scenario data and metadata from
the completed a1b43969 build. This developer artifact is not distributable.
"""
from pathlib import Path
from dataclasses import replace
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time

BASE = Path('/workspace/scratch/243ebc79fa0a')
PROJECT = BASE / 'WarCraftMap/maps/historical-world-rpg/age-of-sail-world'
OUT = Path(__file__).resolve().parent / 'europe-repair'
ROOT = OUT / 'compile'
SEED = PROJECT / '_build/maps/europe_central_east/compile'
PINNED = BASE / 'pinned-wurst/grill'
JAR = BASE / 'pinned-wurst/rootfs/home/wurstuser/.wurst/wurst-compiler/wurstscript.jar'
EXPECTED_REVISION = 'a1b43969eb57de4127b005956823d6b876a86068'
EXPECTED_DEPENDENCY = 'cce79096e71dcb066cf94785bc5cb48ef66c26db'
FROZEN = {
    'PlayableCampaignRuntime.wurst': 'bb1b6fb4330dfb0727b756132b3269bbad1db8b23c6f02ec6bed5073146118fa',
    'CampaignSaveManager.wurst': '48e6f7dc416bf03e8f6895d4569bbd0222ea68d2f2ca4bac33c9c221654fe6ce',
    'WC3Compatibility.wurst': '18e48350fe412e847b3877534e695179177fad18f243cdf707b282412c8a75a1',
}
sys.path.insert(0, str(PROJECT.parent / '_shared/tooling'))
from integration_evidence import execution_sources, source_identity
from wurst_execution import input_hashes, toolchain_environment, compiler_identity, PINNED_COMPILER_SHA256, PINNED_IMAGE
from package_wurst_map import load_config, _inspect, _find_archive
from package_wurst_campaign import load_campaign_config, _inspect_physical_map
from warcraft_campaign import MpqReader
from independent_mpq import load_reader, open_archive, read_member


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def identity(path):
    return {'path': str(path), 'bytes': path.stat().st_size, 'sha256': sha(path)}


def tree(path):
    return {str(p.relative_to(path)): sha(p) for p in sorted(path.rglob('*')) if p.is_file() and '.git' not in p.parts}


def dependency(path):
    return {
        'revision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=path, text=True).strip(),
        'dirty': bool(subprocess.check_output(['git', 'status', '--porcelain', '--untracked-files=no'], cwd=path, text=True).strip()),
        'inputs': {str(p.relative_to(path)): sha(p) for p in sorted(path.rglob('*.wurst')) if '.git' not in p.parts},
    }


def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def main():
    assert not OUT.exists(), 'Preserve previous attempt; choose a fresh output path'
    assert sha(JAR) == PINNED_COMPILER_SHA256
    revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=PROJECT, text=True).strip()
    assert revision == EXPECTED_REVISION
    sources = execution_sources(PROJECT)
    for name, digest in FROZEN.items():
        assert sha(sources['wurst/' + name]) == digest
    before_dependency = dependency(SEED / '_build/dependencies/wurstStdlib2')
    assert before_dependency['revision'] == EXPECTED_DEPENDENCY and not before_dependency['dirty']
    OUT.mkdir(parents=True)
    receipt = {
        'format': 'native_boundary_focused_compile_v1', 'status': 'running',
        'scope': 'one dirty-source destination compile; no full campaign/release/native acceptance',
        'baselineRevision': revision, 'sourceIdentityAtAssembly': source_identity(PROJECT, revision),
        'compilerSha256': sha(JAR), 'expectedImage': PINNED_IMAGE,
        'executionEnvironment': 'Verified extracted pinned compiler on workspace host; full OCI image not run',
        'nativeStatus': 'not_run', 'seedAssembly': str(SEED), 'dependencyInstallInvoked': False,
        'mapMetadataIdentity': 'Retained a1b43969 map metadata in disposable developer artifact; not distributable.',
        'stages': [],
    }
    began = time.monotonic()
    try:
        for name in ('map', 'wurst'):
            shutil.copytree(SEED / name, ROOT / name)
        for relative in ('wurst.build', 'wurst_run.args', '_build/common.j', '_build/blizzard.j'):
            target = ROOT / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(SEED / relative, target)
        shutil.copytree(SEED / '_build/dependencies/wurstStdlib2', ROOT / '_build/dependencies/wurstStdlib2')
        receipt['seedMapInputs'] = tree(ROOT / 'map')
        receipt['retainedGeneratedInputs'] = {}
        changes = []
        mapped_inputs = {}
        retained = {'Bootstrap.wurst', 'ScenarioData.wurst', 'ScenarioSettings.wurst'}
        for path in sorted((ROOT / 'wurst').glob('*.wurst')):
            relative = str(path.relative_to(ROOT))
            if path.name in retained:
                receipt['retainedGeneratedInputs'][relative] = sha(path)
                continue
            assert relative in sources, f'No authored production input for {relative}'
            source = sources[relative]
            before, after = sha(path), sha(source)
            if before != after:
                changes.append({'file': path.name, 'before': before, 'after': after})
            shutil.copy2(source, path)
            mapped_inputs[relative] = {'source': str(source), 'sha256': after}
        assert {row['file'] for row in changes} == set(FROZEN)
        receipt['changedWurstInputs'] = changes
        receipt['authoredProductionInputs'] = mapped_inputs
        receipt['dependency'] = before_dependency
        receipt['configuration'] = {
            'wurst.build': identity(ROOT / 'wurst.build'),
            'authoredWurstBuild': identity(PROJECT / 'wurst.build'),
            'policy': 'Retains previous Grill-installed YAML normalization and dependency URL case; exact compile config is bound.',
            'wurst_run.args': identity(ROOT / 'wurst_run.args'),
        }
        assert (ROOT / 'wurst_run.args').read_bytes() == (PROJECT / 'wurst_run.args').read_bytes()
        inputs = input_hashes(ROOT)
        receipt['wurstInputs'] = {k: v for k, v in inputs.items() if k.endswith('.wurst')}
        write(OUT / 'inputs-before.json', inputs)
        write(OUT / 'build-result.json', receipt)
        os.environ['JAVA_TOOL_OPTIONS'] = '-Xmx6g'
        for name, args in (('typecheck', ['typecheck']), ('build', ['build', 'map/AgeOfSailWorld.w3x'])):
            assert input_hashes(ROOT) == inputs
            assert dependency(ROOT / '_build/dependencies/wurstStdlib2') == before_dependency
            command = [str(PINNED)] + args
            started = time.monotonic()
            print(f'Running isolated Europe {name}', flush=True)
            result = subprocess.run(command, cwd=ROOT, env=toolchain_environment(), stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT, text=True)
            log = OUT / (name + '.log')
            log.write_text(result.stdout)
            row = {'stage': name, 'command': command, 'exitCode': result.returncode,
                   'wallSeconds': round(time.monotonic() - started, 6), 'log': identity(log),
                   'compiler': compiler_identity(result.stdout), 'inputsUnchanged': input_hashes(ROOT) == inputs}
            receipt['stages'].append(row)
            write(OUT / 'build-result.json', receipt)
            assert result.returncode == 0, f'{name} failed; inspect {log}'
            assert row['inputsUnchanged']
            assert dependency(ROOT / '_build/dependencies/wurstStdlib2') == before_dependency
        archive = _find_archive(ROOT)
        config = load_campaign_config(PROJECT / 'physical-maps.json')
        physical = next(m for m in config.maps if m.id == 'europe_central_east')
        map_config = replace(load_config(config.map_config_path), source_map=physical.source_map, manifest=physical.source_manifest)
        _inspect(map_config, archive, ROOT, physical.terrain_ids)
        _inspect_physical_map(physical, archive)
        own = MpqReader(archive)
        independent = open_archive(load_reader(BASE / 'validation-536/mpyq-reviewed.py'), archive.read_bytes())
        extracted = {}
        for name in ('war3map.lua', 'war3map.wpm', 'war3map.w3i', 'runtime/build-identity.json'):
            data = own.read(name)
            assert data == read_member(independent, name), f'Independent member mismatch: {name}'
            target = OUT / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            extracted[name] = identity(target)
        assert extracted['war3map.wpm']['sha256'] == '7cf3b29475751ebe1d962e17651b0c42ace030b9fa2e4523cf935adf27aee0bd'
        assert (ROOT / '_build/02_compiled.lua').read_bytes() == (OUT / 'war3map.lua').read_bytes()
        for relative, row in mapped_inputs.items():
            assert sha(Path(row['source'])) == row['sha256']
        write(OUT / 'inputs-after.json', input_hashes(ROOT))
        receipt.update(status='pass', archive=identity(archive), extracted=extracted, archiveInspection='pass',
                       independentKnownMembersEqual=True, frozenWpmEqual=True, compilerOutputEqualsArchiveLua=True,
                       compilerInputsUnchangedDuringBuild=True, authoredProductionUnchanged=True,
                       compiledScript=str(OUT / 'war3map.lua'), compiledScriptSha256=sha(OUT / 'war3map.lua'),
                       compiledScriptBytes=(OUT / 'war3map.lua').stat().st_size)
    except Exception as error:
        receipt.update(status='fail', error=str(error))
        raise
    finally:
        receipt['wallSeconds'] = round(time.monotonic() - began, 6)
        write(OUT / 'build-result.json', receipt)
    print(json.dumps({key: receipt[key] for key in ('status', 'compiledScriptSha256', 'compiledScriptBytes', 'wallSeconds')}, indent=2))


if __name__ == '__main__':
    main()
