#!/usr/bin/env python3
"""Summarize terminal source-bound local evidence without native acceptance."""
from pathlib import Path
import gzip
import hashlib
import json

BASE = Path('/workspace/scratch/243ebc79fa0a')
ROOT = Path(__file__).resolve().parent
AUDIT = ROOT.parent
REPO = BASE / 'WarCraftMap'
PROJECT = REPO / 'maps/historical-world-rpg/age-of-sail-world'


def identity(path):
    data = path.read_bytes()
    return {'path': str(path), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def read(path):
    return json.loads(path.read_text())


def phases(report, name):
    return [dict(occurrence=i + 1, instructions=row['instructions'], cpuSeconds=row['cpuSeconds'],
                 nativeCalls=row['nativeCalls'], completed=row['completed'])
            for i, row in enumerate(row for row in report['execution']['phases'] if row['name'] == name)]


paths = {
    'build': ROOT / 'build-result.json',
    'compileInputsBefore': ROOT / 'inputs-before.json',
    'compileInputsAfter': ROOT / 'inputs-after.json',
    'focusedWurst': AUDIT / 'authority-focused-tests-attempt2/results.json',
    'focusedWurstContext': AUDIT / 'authority-focused-tests-attempt2/focused-context.json',
    'focusedSetupFailure': AUDIT / 'authority-focused-tests/results.json',
    'oldFrozenStartup': BASE / 'validation-536/startup-audit/europe_central_east-lua53-exact-source-fix-probe.json',
    'newFrozenStartup': ROOT / 'frozen-startup/result.json',
    'oldObserver': AUDIT / 'startup-observer-collision32/startup-and-first-callbacks.json',
    'newObserver': ROOT / 'observer/startup-and-first-callbacks.json',
    'compiledParity': ROOT / 'parity/compiled-parity.json',
    'compiledChecksumExcerpt': ROOT / 'parity/compiled-checksum-and-table-helpers.lua',
    'cacheWriteRejection': PROJECT / 'reports/issue-438/native-boundary-repair/compiled/cache-write-rejection.json',
}
build, focused = read(paths['build']), read(paths['focusedWurst'])
old, new = read(paths['oldFrozenStartup']), read(paths['newFrozenStartup'])
old_observer, new_observer = read(paths['oldObserver']), read(paths['newObserver'])
parity = read(paths['compiledParity'])
assert build['status'] == focused['status'] == 'pass'
assert old['status'] == new['status'] == 'completed_under_stubs'
assert old['harnessSha256'] == new['harnessSha256']
assert old['lateNativeStubsSha256'] == new['lateNativeStubsSha256']
assert old['instructionBudget'] == new['instructionBudget'] == 2_000_000_000
assert old['runtimeCounts'] == new['runtimeCounts']
assert old['tradeSnapshotIdentity'] == new['tradeSnapshotIdentity']
assert old['finalCacheRequest'] == new['finalCacheRequest']
assert new['compiledLuaSha256'] == build['compiledScriptSha256']
assert new_observer['inputs']['compiledLua']['sha256'] == build['compiledScriptSha256']
assert parity['inputs']['newLua']['sha256'] == build['compiledScriptSha256']
assert new_observer['status'] == old_observer['status'] == 'completed_under_explicit_stubs'
assert new_observer['execution']['startup']['nativeCalls'] == new['nativeCalls']
assert old_observer['execution']['startup']['nativeCalls'] == old['nativeCalls']
assert new_observer['inputs']['observer']['sha256'] == old_observer['inputs']['observer']['sha256']
assert parity['status'] == 'pass_under_explicit_models'
assert read(paths['compileInputsBefore']) == read(paths['compileInputsAfter'])
payloads = []
assert len(old_observer['cachePayloads']) == len(new_observer['cachePayloads']) == 4
for index, (before, after) in enumerate(zip(old_observer['cachePayloads'], new_observer['cachePayloads']), 1):
    assert (before['mission'], before['key']) == (after['mission'], after['key'])
    old_bytes = gzip.decompress((AUDIT / 'startup-observer-collision32' / f'cache-write-{index}.txt.gz').read_bytes())
    new_bytes = gzip.decompress((ROOT / 'observer' / f'cache-write-{index}.txt.gz').read_bytes())
    assert old_bytes == new_bytes
    payloads.append({'mission': after['mission'], 'key': after['key'], 'bytes': len(new_bytes),
                     'sha256': hashlib.sha256(new_bytes).hexdigest(), 'exactPreviousBytesEqual': True})
selected = ['StringHash', 'SubString', 'StringLength', 'GetStoredString', 'HaveStoredString', 'StoreString', 'SaveGameCache']
phase_names = [
    'PlayableCampaignState_PlayableCampaignState_captureAuthoritativeState',
    'PlayableCampaignState_PlayableCampaignState_validateAuthoritativeState',
    'MilitarySettlementRuntime_MilitarySettlementRuntime_parseSnapshot',
    'PlayableCampaignCodec_PlayableCampaignCodec_encode', 'runtimeChecksum',
]
report = {
    'format': 'native_boundary_repair_source_comparison_v1',
    'status': 'pass_scoped_source_and_explicit_model_checks',
    'nativeStatus': 'not_run', 'nativeHangResolution': 'not_established',
    'playerArtifactPublished': False, 'distributionStatus': 'source_work_only_no_new_campaign',
    'sourceIdentityAtCompile': build['sourceIdentityAtAssembly'],
    'changedProductionInputs': build['changedWurstInputs'],
    'actualCompiledLua': build['extracted']['war3map.lua'],
    'focusedWurst': {'discovered': focused['discovered'], 'succeeded': focused['succeeded'],
                     'status': focused['status'], 'initialSetupFailurePreserved': True},
    'fullWurstSuite': 'separate_root_owned_receipt_not_claimed_here',
    'compilerInputsUnchanged': True,
    'startup': {
        'status': new['status'], 'campaignStarted': new['campaignStarted'], 'campaignRegistered': new['campaignRegistered'],
        'runtimeCounts': new['runtimeCounts'], 'tradeSnapshotIdentity': new['tradeSnapshotIdentity'],
        'finalHandoffRequest': new['finalCacheRequest'], 'instructionBudget': new['instructionBudget'],
        'oldInstructionSamples': old['instructions'], 'newInstructionSamples': new['instructions'],
        'oldStockWallSeconds': old['wallSeconds'], 'newStockWallSeconds': new['wallSeconds'],
        'timingComparison': 'No speedup ratio; later run shared the host with an interpreter suite. Neither is Warcraft timing.',
        'nativeCalls': {name: {'before': old['nativeCalls'].get(name, 0), 'after': new['nativeCalls'].get(name, 0),
                               'difference': new['nativeCalls'].get(name, 0) - old['nativeCalls'].get(name, 0)} for name in selected},
    },
    'sameObserverPhaseCosts': {name: {'before': phases(old_observer, name), 'after': phases(new_observer, name)} for name in phase_names},
    'firstCallbacks': new_observer['execution']['callbackPhase'],
    'cachePayloads': payloads,
    'cachePayloadBytesTotal': sum(row['bytes'] for row in payloads),
    'compiledParity': {'editModels': parity['editModels'], 'checksumModels': parity['checksumModels'],
                      'productionFunctionOverrides': False},
    'remainingCostsAndLimits': [
        {'finding': 'Three actual checksum bodies still perform 3,202,415 one-byte SubString calls.',
         'evidence': 'Observer runtimeChecksum phase deltas and actual compiled checksum excerpt.',
         'source': '../_shared/wurst/PlayableCampaignRuntime.wurst:1067-1077'},
        {'finding': 'Two full captures perform 3,224,728 and 3,224,942 SubString calls; validation performs 4,864,675.',
         'evidence': 'Disjoint capture/validation observer phase deltas. Checksum/encode is measured separately.'},
        {'finding': 'A single cached document is alternated between original authority and the enlarged result during captureDomains.',
         'evidence': 'Source calls lastAuthorityValue(document,...) between edits of result; indexAuthoritySeparators rebuilds when its document differs. This is source analysis, not an extra measured index-miss count.',
         'source': '../_shared/wurst/PlayableCampaignRuntime.wurst:487-531'},
        {'finding': 'Military snapshot parsing still runs twice during one validation and uses catalogue force lookups.',
         'evidence': 'Two completed parseSnapshot phase records; source validates military then builds a detached military state for country validation.',
         'source': '../_shared/wurst/PlayableCampaignRuntime.wurst:707-732'},
        {'finding': 'Four synchronous SaveGameCache calls submit 3,202,546 bytes in total.',
         'evidence': 'Captured actual compiled storage arguments match previous bytes; explicit cache stubs return success without disk work.'},
        {'finding': 'Native bridge latency, full-string native behavior, real disk persistence, assets, rendering and Warcraft callback scheduling remain unmeasured.',
         'evidence': 'Frozen stub limitations; first callback model stops at 1.001 simulated seconds and does not run the 300-second autosave.'},
    ],
    'limitations': [
        'Stock Lua 5.3.6 with explicit stubs is not the Warcraft runtime. The target embedded Lua patch version remains unverified.',
        'Instruction samples include wrapper and stub work. They are not a Warcraft operation limit.',
        'Native argument byte volumes are argument traffic, not proof of bytes copied by the engine.',
        'Observer native-call totals equal the frozen startup probe; the observer has additional measurement instruction overhead.',
        'Hash test oracles deliberately include zero/negative/colliding values. They do not claim to implement current retail StringHash.',
        'Malformed/partial UTF8 tests are scoped to the two explicit models; found edits retain the literal previous tail-relative slicing path.',
        'No complete campaign rebuild, native launch or player retest was performed for this correction.',
    ],
    'evidence': {name: identity(path) for name, path in paths.items()},
    'reproductionScripts': {name: identity(path) for name, path in {
        'compile': AUDIT / 'build-europe-repair.py', 'focused': AUDIT / 'run-authority-focused-tests.py',
        'frozenStartup': ROOT / 'run-frozen-startup.py', 'observer': ROOT / 'observer/observe-startup.py',
        'observerLua': ROOT / 'observer/observe-startup.lua', 'parity': ROOT / 'verify-compiled-parity.py',
        'summary': Path(__file__),
    }.items()},
}
destination = ROOT / 'comparison.json'
assert not destination.exists(), 'Preserve previous comparison'
destination.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
print(json.dumps({'status': report['status'], 'nativeHangResolution': report['nativeHangResolution'],
                  'cachePayloadBytesTotal': report['cachePayloadBytesTotal'], 'comparison': identity(destination)}, indent=2))
