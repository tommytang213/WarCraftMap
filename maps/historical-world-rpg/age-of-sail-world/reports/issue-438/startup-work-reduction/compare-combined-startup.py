#!/usr/bin/env python3
"""Compare actual archived baseline/revised Lua under unchanged explicit models.

This is developer evidence only. No Warcraft native execution is implied.
"""
from pathlib import Path
import argparse
import gzip
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys

BASE = Path('/workspace/scratch/243ebc79fa0a')
PACK = BASE / 'WarCraftMap/maps/historical-world-rpg/age-of-sail-world/reports/issue-438/native-boundary-repair'
LIBRARY = BASE / 'validation-536/lua53-runtime/liblua5.3.6-probe.so'
EXPECTED = {
    'probe-lua54-initialization.py': 'b3bd4b946cd4ceb9b46a7c254fb1c9d498868c9deae31cf72836ff8dc1225948',
    'late-startup-stubs.lua': '3c7eda8627f7ba5d4c3d3f49328be834d7598f1e8616462f665b02ae8cdaa630',
}


def identity(path):
    data = path.read_bytes()
    return {'path': str(path), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def read(path):
    return json.loads(path.read_text())


def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def observe(label, build_path, out, observer_source):
    build = read(build_path)
    assert build['status'] == 'pass'
    script = Path(build['compiledScript'])
    assert identity(script)['sha256'] == build['compiledScriptSha256']
    run = out / label
    frozen = run / 'frozen'
    observer = run / 'observer'
    frozen.mkdir(parents=True)
    observer.mkdir()
    for name, digest in EXPECTED.items():
        source = PACK / 'common' / name
        assert identity(source)['sha256'] == digest
        shutil.copy2(source, frozen / name)
    os.environ['WC3_LUA_PROBE_LIBRARY'] = str(LIBRARY)
    harness = frozen / 'probe-lua54-initialization.py'
    spec = importlib.util.spec_from_file_location('frozen_startup_' + label, harness)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    print('Running unchanged frozen probe: ' + label, flush=True)
    result = module.probe('europe_central_east', 'startup-complete', 2_000_000_000,
                          lua_path=script, report_label=label)
    result['boundBuildReceipt'] = identity(build_path)
    result['nativeStatus'] = 'not_run'
    result['runner'] = identity(Path(__file__))
    write(frozen / 'result.json', result)
    assert result['status'] == 'completed_under_stubs'
    assert result['campaignStarted'] and result['campaignRegistered']
    assert result['compiledLuaSha256'] == build['compiledScriptSha256']
    shutil.copy2(observer_source, observer / 'observe-startup.lua')
    runner = (PACK / 'compiled/observer/observe-startup.py').read_text()
    substitutions = {
        "OUT=ROOT/'validation-536/native-boundary-audit/europe-repair/observer'": 'OUT=Path(' + repr(str(observer)) + ')',
        "EVIDENCE=ROOT/'WarCraftMap/maps/historical-world-rpg/age-of-sail-world/reports/issue-438/trade-startup'": 'EVIDENCE=Path(' + repr(str(frozen)) + ')',
        "SCRIPT=ROOT/'validation-536/native-boundary-audit/europe-repair/war3map.lua'": 'SCRIPT=Path(' + repr(str(script)) + ')',
        "RECEIPT=ROOT/'validation-536/native-boundary-audit/europe-repair/build-result.json'": 'RECEIPT=Path(' + repr(str(build_path)) + ')',
    }
    for before, after in substitutions.items():
        assert runner.count(before) == 1
        runner = runner.replace(before, after)
    runner_path = observer / 'observe-startup.py'
    runner_path.write_text(runner)
    print('Running unchanged observer Lua: ' + label, flush=True)
    subprocess.run([sys.executable, '-B', str(runner_path)], check=True)
    observed = read(observer / 'startup-and-first-callbacks.json')
    assert observed['status'] == 'completed_under_explicit_stubs'
    assert observed['execution']['startup']['nativeCalls'] == result['nativeCalls']
    assert observed['execution']['startup']['started'] and observed['execution']['startup']['registered']
    callbacks = observed['execution']['callbackPhase']
    assert callbacks['completed'] and callbacks['callbackCount'] == 37 and callbacks['throughSeconds'] == 1.001
    assert not observed['execution']['callbackErrors']
    assert observed['inputs']['observer']['sha256'] == identity(observer_source)['sha256']
    assert len(observed['cachePayloads']) == 4
    return {'frozen': result, 'observer': observed, 'directory': run, 'build': identity(build_path)}


def phases(report):
    names = {
        'PlayableCampaignState_PlayableCampaignState_captureAuthoritativeState',
        'PlayableCampaignState_PlayableCampaignState_validateAuthoritativeState',
        'MilitarySettlementRuntime_MilitarySettlementRuntime_parseSnapshot',
        'runtimeChecksum',
    }
    return [{key: row[key] for key in ('name', 'nativeCalls', 'instructions', 'completed')}
            for row in report['execution']['phases'] if row['name'] in names]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--baseline-build', type=Path, required=True)
    parser.add_argument('--revised-build', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--observer', type=Path, default=PACK / 'compiled/observer/observe-startup.lua')
    args = parser.parse_args()
    assert not args.output.exists(), 'Preserve prior evidence; choose a fresh output directory'
    assert identity(LIBRARY)['sha256'] == 'fdaa987d06dd329be3232a65ea71cae427f3bfd26f5b757d8853628d33d9492a'
    original_observer = PACK / 'compiled/observer/observe-startup.lua'
    original_bytes = original_observer.read_bytes()
    selected_bytes = args.observer.read_bytes()
    removed = b" 'MilitarySettlementRuntime_MilitarySettlementRuntime_validateSnapshot',\n"
    assert original_bytes.count(removed) == 1
    assert selected_bytes in (original_bytes, original_bytes.replace(removed, b'')), 'Only the obsolete wrapper removal is permitted'
    observer_variant = {'original': identity(original_observer), 'selected': identity(args.observer),
                        'productionFunctionOverridesAdded': False,
                        'change': 'none' if selected_bytes == original_bytes else 'Remove only obsolete validateSnapshot measurement wrapper after compiler dead-code elimination; same observer on both compiled inputs'}
    if selected_bytes != original_bytes:
        declaration = b'function MilitarySettlementRuntime_MilitarySettlementRuntime_validateSnapshot('
        baseline_build, revised_build = read(args.baseline_build), read(args.revised_build)
        assert baseline_build['status'] == revised_build['status'] == 'pass'
        baseline_lua, revised_lua = Path(baseline_build['compiledScript']), Path(revised_build['compiledScript'])
        assert identity(baseline_lua)['sha256'] == baseline_build['compiledScriptSha256']
        assert identity(revised_lua)['sha256'] == revised_build['compiledScriptSha256']
        assert declaration in baseline_lua.read_bytes() and declaration not in revised_lua.read_bytes()
        observer_variant['targetDefinedInBaseline'] = True
        observer_variant['targetDefinedInRevised'] = False
    args.output.mkdir(parents=True)
    report = {'status': 'running', 'nativeStatus': 'not_run', 'nativeHangResolution': 'not_established',
              'runner': identity(Path(__file__)), 'library': identity(LIBRARY), 'observerVariant': observer_variant,
              'limitations': [
                  'Stock Lua with frozen explicit native stubs is not Warcraft execution.',
                  'The observer delegates production functions but is not a function-identity gate.',
                  'Argument byte volumes are traffic, not proof that Warcraft copies these bytes.',
                  'The timer model ends after 1.001 simulated seconds; no disk, rendering, assets or native scheduling proof.',
                  'No wall-time speedup ratio or native loading-time claim.']}
    try:
        before = observe('baseline', args.baseline_build.resolve(), args.output, args.observer)
        after = observe('revised', args.revised_build.resolve(), args.output, args.observer)
        old, new = before['frozen'], after['frozen']
        assert old['nativeCalls']['SubString'] == 15095868, 'Restored baseline differs from published264b evidence'
        assert old['nativeCalls']['StringHash'] == 37931
        for key in ('runtimeCounts', 'tradeSnapshotIdentity', 'finalCacheRequest'):
            assert old[key] == new[key], key
        assert new['runtimeCounts']['markets'] == 8422 and new['runtimeCounts']['stores'] == 829
        payloads = []
        for i, (old_row, new_row) in enumerate(zip(before['observer']['cachePayloads'], after['observer']['cachePayloads']), 1):
            assert (old_row['mission'], old_row['key']) == (new_row['mission'], new_row['key'])
            old_data = gzip.decompress((before['directory'] / 'observer' / f'cache-write-{i}.txt.gz').read_bytes())
            new_data = gzip.decompress((after['directory'] / 'observer' / f'cache-write-{i}.txt.gz').read_bytes())
            assert old_data == new_data
            non_ascii = sum(byte >= 128 for byte in new_data)
            payloads.append({'mission': new_row['mission'], 'key': new_row['key'], 'bytes': len(new_data),
                             'sha256': hashlib.sha256(new_data).hexdigest(), 'exactPreviousBytesEqual': True,
                             'asciiOnly': non_ascii == 0, 'nonAsciiByteCount': non_ascii})
        names = sorted(set(old['nativeCalls']) | set(new['nativeCalls']))
        report.update(status='pass_under_explicit_models',
            baselineBuild=before['build'], revisedBuild=after['build'],
            nativeCalls={name: {'before': old['nativeCalls'].get(name, 0), 'after': new['nativeCalls'].get(name, 0),
                                'difference': new['nativeCalls'].get(name, 0) - old['nativeCalls'].get(name, 0)} for name in names},
            instructionSamples={'before': old['instructions'], 'after': new['instructions']},
            runtimeCounts=new['runtimeCounts'], tradeSnapshotIdentity=new['tradeSnapshotIdentity'],
            finalCacheRequest=new['finalCacheRequest'], cachePayloads=payloads,
            cachePayloadBytesTotal=sum(row['bytes'] for row in payloads),
            nativeArgumentVolumeScope='Startup and modeled callbacks through 1.001 simulated seconds',
            nativeArgumentVolumes={'before': before['observer']['execution']['nativeArgumentVolumes'],
                                   'after': after['observer']['execution']['nativeArgumentVolumes']},
            phases={'before': phases(before['observer']), 'after': phases(after['observer'])},
            callbackPhases={'before': before['observer']['execution']['callbackPhase'],
                            'after': after['observer']['execution']['callbackPhase']})
    except Exception as exc:
        report.update(status='fail', error=str(exc))
        raise
    finally:
        write(args.output / 'comparison.json', report)
    print(json.dumps({key: report[key] for key in ('status', 'instructionSamples', 'cachePayloads', 'nativeArgumentVolumes')}, indent=2))


if __name__ == '__main__':
    main()
