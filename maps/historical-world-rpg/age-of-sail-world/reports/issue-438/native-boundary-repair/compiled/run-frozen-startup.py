#!/usr/bin/env python3
"""Fail-closed wrapper around the unchanged archived explicit-stub probe."""
from pathlib import Path
import hashlib
import importlib.util
import json
import os

ROOT = Path(__file__).resolve().parent
REPORT = ROOT / 'frozen-startup/result.json'
SCRIPT = ROOT / 'war3map.lua'
LIB = ROOT.parents[1] / 'lua53-runtime/liblua5.3.6-probe.so'
HARNESS = ROOT / 'frozen-startup/probe-lua54-initialization.py'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


assert not REPORT.exists(), 'Preserve previous result'
receipt = json.loads((ROOT / 'build-result.json').read_text())
assert receipt['status'] == 'pass'
assert sha(SCRIPT) == receipt['compiledScriptSha256']
assert sha(HARNESS) == 'b3bd4b946cd4ceb9b46a7c254fb1c9d498868c9deae31cf72836ff8dc1225948'
assert sha(ROOT / 'frozen-startup/late-startup-stubs.lua') == '3c7eda8627f7ba5d4c3d3f49328be834d7598f1e8616462f665b02ae8cdaa630'
assert sha(LIB) == 'fdaa987d06dd329be3232a65ea71cae427f3bfd26f5b757d8853628d33d9492a'
os.environ['WC3_LUA_PROBE_LIBRARY'] = str(LIB)
spec = importlib.util.spec_from_file_location('frozen_startup', HARNESS)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
result = module.probe('europe_central_east', 'startup-complete', 2_000_000_000,
                      lua_path=SCRIPT, report_label='authority-cache-repair')
result['boundBuildReceipt'] = {'path': str(ROOT / 'build-result.json'), 'sha256': sha(ROOT / 'build-result.json')}
result['runnerSha256'] = sha(Path(__file__))
result['nativeStatus'] = 'not_run'
result['timingContext'] = 'Shared workspace may concurrently execute the complete Wurst suite; no native timing or wall-time speedup claim.'
REPORT.write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
assert result['status'] == 'completed_under_stubs', result.get('error')
assert result['campaignStarted'] and result['campaignRegistered']
assert result['compiledLuaSha256'] == receipt['compiledScriptSha256']
assert result['runtimeCounts']['markets'] == 8422 and result['runtimeCounts']['stores'] == 829
print(json.dumps({key: result[key] for key in ('status', 'instructions', 'wallSeconds', 'nativeCalls', 'runtimeCounts', 'tradeSnapshotIdentity')}, indent=2, sort_keys=True))
