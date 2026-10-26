#!/usr/bin/env python3
"""Fail-closed, local compiled-Lua trade regression; never native Warcraft proof."""
from __future__ import annotations

import argparse
import ctypes
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import sys
import time

ROOT = Path(__file__).resolve().parent
FROZEN_HARNESS_SHA = 'b3bd4b946cd4ceb9b46a7c254fb1c9d498868c9deae31cf72836ff8dc1225948'
FROZEN_STUBS_SHA = '3c7eda8627f7ba5d4c3d3f49328be834d7598f1e8616462f665b02ae8cdaa630'
WPM_SHA = '7cf3b29475751ebe1d962e17651b0c42ace030b9fa2e4523cf935adf27aee0bd'
SOURCE_SHA = '0730e299ae8fa093e317bb586f7b0992dd30e8ca86082be84637653c3865ecda'
BUDGET = 2_000_000_000


def identity(path: Path) -> dict:
    payload = path.read_bytes()
    return {'path': str(path.resolve()), 'bytes': len(payload),
            'sha256': hashlib.sha256(payload).hexdigest()}


def lua_table(values: list[str]) -> str:
    return '{' + ','.join(json.dumps(value) for value in values) + '}'


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--lua-path', type=Path, required=True,
                        help='Actual Lua extracted from the retained destination archive')
    parser.add_argument('--build-receipt', type=Path, default=ROOT / 'build-result.json')
    parser.add_argument('--library', required=True, help='Stock Lua 5.3 or 5.4 shared library')
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    report = {'format': 'compiled_lua_full_scale_trade_roundtrip_v1', 'status': 'failed',
              'nativeStatus': 'not_run', 'releaseStatus': 'not_a_release_gate',
              'instructionBudgetPerPhase': BUDGET, 'timerCallbacksExecuted': 0,
              'productionFunctionOverrides': False,
              'initialRequest': 'v1|1|pending|austria|europe_central_east|europe_central_alpine|vienna',
              'limitations': [
                  'Local stock Lua with explicit typed native stubs; no Warcraft client is run.',
                  'StringHash is a collision-free ID stub, not Warcraft hashing; collision semantics require separate Wurst regressions.',
                  'InitBlizzard is a no-op and player slots are 24; synthetic units, orders, regions and timers have the frozen model defaults.',
                  'No timer/trigger callback, rendering, transition, engine collision, assets or disk game-cache behavior is exercised.',
                  'Pathing uses retained base WPM only; game-cache save always succeeds in memory.',
                  'Two independent sampled 2B instruction safety budgets include Lua stub work; this is not a Warcraft operation limit.',
                  'Startup call/return debug-hook observation adds overhead. These timings are not the frozen before/after startup comparison or native load times.',
                  'The exact embedded Warcraft Lua patch version is unverified; stock Lua 5.3.6 is not asserted binary-equivalent.',
              ]}
    started = time.monotonic()
    state = None
    module = None
    try:
        harness = ROOT / 'probe-lua54-initialization.py'
        stubs = ROOT / 'late-startup-stubs.lua'
        case = ROOT / 'full-scale-roundtrip.lua'
        assert identity(harness)['sha256'] == FROZEN_HARNESS_SHA, 'Frozen harness digest changed'
        assert identity(stubs)['sha256'] == FROZEN_STUBS_SHA, 'Frozen stubs digest changed'
        receipt = json.loads(args.build_receipt.read_text())
        script_identity = identity(args.lua_path)
        assert script_identity['sha256'] == receipt['compiledScriptSha256'], 'Archived script does not match compile receipt'
        assert receipt['wurstInputs']['wurst/PlayableTrade.wurst'] == SOURCE_SHA, 'Production source digest differs'
        assert receipt['buildExitCode'] == 0 and receipt['typecheckExitCode'] == 0
        assert receipt['compilerInputsUnchangedDuringBuild'] is True
        stub_text = stubs.read_text()
        pathing_paths = re.findall(r"io\.open\('([^']+war3map\.wpm)'", stub_text)
        assert len(pathing_paths) == 1, 'Cannot identify exact frozen pathing input'
        pathing = Path(pathing_paths[0])
        assert identity(pathing)['sha256'] == WPM_SHA, 'Frozen pathing input digest changed'
        report['inputs'] = {
            'compiledLua': script_identity, 'buildReceipt': identity(args.build_receipt),
            'productionSourceSha256': SOURCE_SHA,
            'frozenHarness': identity(harness), 'frozenNativeStubs': identity(stubs),
            'roundtripHarness': identity(Path(__file__)), 'roundtripCase': identity(case),
            'pathing': identity(pathing),
        }
        os.environ['WC3_LUA_PROBE_LIBRARY'] = args.library
        spec = importlib.util.spec_from_file_location('frozen_lua_probe', harness)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        lib = module.lib
        pointer_string = ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int,
                                          ctypes.POINTER(ctypes.c_size_t))(('lua_tolstring', lib))
        state = lib.luaL_newstate()
        assert state, 'Cannot allocate Lua state'
        lib.luaL_openlibs(state)

        def get_bytes(name: str) -> bytes:
            lib.lua_getglobal(state, name.encode())
            size = ctypes.c_size_t()
            address = pointer_string(state, -1, ctypes.byref(size))
            assert address, 'Missing Lua string: ' + name
            result = ctypes.string_at(address, size.value)
            lib.lua_settop(state, 0)
            return result

        report['runtimeVersion'] = get_bytes('_VERSION').decode()
        assert report['runtimeVersion'] in ('Lua 5.3', 'Lua 5.4')
        runtime_paths = {line.split()[-1] for line in Path('/proc/self/maps').read_text().splitlines()
                         if 'liblua' in line and line.split()[-1].startswith('/')}
        if Path(args.library).is_file():
            runtime_path = Path(args.library)
        else:
            candidates = [Path(value) for value in runtime_paths if Path(value).name.startswith(Path(args.library).name)]
            assert len(candidates) == 1, 'Cannot identify loaded Lua library'
            runtime_path = candidates[0]
        report['runtimeLibrary'] = identity(runtime_path)
        status = lib.luaL_loadfilex(state, str(args.lua_path.resolve()).encode(), b't')
        if not status:
            status = lib.lua_pcallk(state, 0, 0, 0, 0, None)
        if status:
            raise RuntimeError(lib.lua_tolstring(state, -1, None).decode(errors='replace'))
        source = args.lua_path.read_text()
        function_names = re.findall(r'^function ([A-Za-z_][A-Za-z0-9_]*)\(', source, re.M)
        module.execute(state, '__scale_original_functions={}\nfor _,name in ipairs(' + lua_table(function_names) + ') do '
                       'assert(type(_G[name])=="function",name);__scale_original_functions[name]=_G[name] end')
        module.execute(state, module.PRELUDE)
        module.execute(state, stub_text)
        literal_returns = {index: line.strip().split(' ', 1)[1]
                           for index, line in enumerate(source.splitlines(), 1)
                           if line.strip() in ('return true', 'return false')}
        module.execute(state, '__scale_budget=' + str(BUDGET) + '\n__scale_literal_returns={' +
                       ','.join(f'[{key}]={json.dumps(value)}' for key, value in literal_returns.items()) + '}')
        module.execute(state, case.read_text())
        unchanged = ('for name,original in pairs(__scale_original_functions) do '
                     'assert(_G[name]==original,"Compiled function replaced: "..name) end')
        module.execute(state, unchanged)
        report['compiledFunctionsCheckedUnchanged'] = len(function_names)
        for phase_name in ('startup', 'roundtrip'):
            before = time.monotonic()
            try:
                module.execute(state, '__scale_run_' + phase_name + '()')
            finally:
                module.execute(state, 'debug.sethook();__scale_json=__probe.json(__scale)')
                report['execution'] = json.loads(get_bytes('__scale_json'))
                report.setdefault('phaseWallSeconds', {})[phase_name] = round(time.monotonic() - before, 6)
            module.execute(state, unchanged)
        saved, changed, restored = [get_bytes('__scale_' + label) for label in ('saved', 'mutated', 'restored')]
        assert saved == restored and saved != changed, 'Python byte comparison failed'
        report['captures'] = {label: {'bytes': len(payload), 'sha256': hashlib.sha256(payload).hexdigest()}
                              for label, payload in (('saved', saved), ('mutated', changed), ('restored', restored))}
        execution = report['execution']
        assert set(execution['phases']) == {'startup', 'roundtrip'}
        for phase_name, phase in execution['phases'].items():
            assert phase['completed'] is True and phase['instructions'] <= BUDGET, 'Phase failed: ' + phase_name
            assert not phase.get('budgetExhausted'), 'Instruction budget exhausted'
        result = execution['roundtrip']
        assert result['marketCount'] == result['mutatedMarkets'] == 8422
        assert result['storeCount'] == result['populatedStores'] == result['mutatedStores'] == 829
        assert result['populatedLots'] == result['clearedLots'] == result['restoredLots'] == 829
        assert result['reconstructReturned'] is True and result['exactCaptureEquality'] is True
        assert result['selectionRestored'] is True and result['catalogueOrderRestored'] is True
        assert len(execution['phases']['roundtrip']['stages']) == 5
        assert all(stage['completed'] is True for stage in execution['phases']['roundtrip']['stages'])
        assert identity(args.lua_path) == script_identity, 'Compiled Lua changed during execution'
        assert identity(harness)['sha256'] == FROZEN_HARNESS_SHA
        assert identity(stubs)['sha256'] == FROZEN_STUBS_SHA
        report['status'] = 'pass_full_scale_roundtrip_under_explicit_stubs'
    except Exception as exc:
        report['error'] = str(exc)
    finally:
        if state and module:
            module.lib.lua_close(state)
        report['wallSeconds'] = round(time.monotonic() - started, 6)
        args.report.parent.mkdir(parents=True, exist_ok=True)
        temporary = args.report.with_name(args.report.name + '.part')
        temporary.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
        os.replace(temporary, args.report)
    print(json.dumps({key: report[key] for key in ('status', 'nativeStatus', 'wallSeconds')}, sort_keys=True))
    if report['status'] == 'failed':
        print(report.get('error', 'Unspecified failure'), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
