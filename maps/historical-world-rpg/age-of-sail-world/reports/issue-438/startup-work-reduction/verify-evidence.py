#!/usr/bin/env python3
"""Verify retained source evidence; never run a compiler, Lua, or Warcraft."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path, PurePosixPath
import re
import sys

BASELINE = '264b34c9a0762bdadda377fb10cb44a63af33052'
SOURCE = 'b69fd4f0100a2a9f5f5e4c266e4e68ee3e35af3dc5be91d010be9b325e97b62d'
BASELINE_SOURCE = '2f55ec1dc084ab27c1a4fde2897728035ea49f086c8fbdd3e1d1cb3aeca22d8b'
CAPTURE_SOURCE = '95f514cdc2370337c006ca05331e820b8e45bb78331ba3e2c9a9e1d5b2fe8a77'
COMPILER = '1f3ae40b1018b8757867515596adfa69113ca85f390c1b353cc8b69cf8944145'
DEPENDENCY = 'cce79096e71dcb066cf94785bc5cb48ef66c26db'
GATE = '49fe8dd2c491ef16ebfcfb481aa782d27c1356779ad229b10e0ba1b108513101'
LIBRARY = 'fdaa987d06dd329be3232a65ea71cae427f3bfd26f5b757d8853628d33d9492a'
HARNESS = 'b3bd4b946cd4ceb9b46a7c254fb1c9d498868c9deae31cf72836ff8dc1225948'
STUBS = '3c7eda8627f7ba5d4c3d3f49328be834d7598f1e8616462f665b02ae8cdaa630'
OBSERVER = '6a8f2f7a5b3240bfc72b8f219e43321234219fa9b608d16698039c8a76cfc420'
FULL_RUNNER = '85b483b67caeeab44ca03007da8da3ffba02af8d895402240bf49bc6d245b96c'
CAPTURE_RUNNER = 'e0eb92ac6255181d852d7a25c379033c3fb5d59724ce2d28148fcd895cf6bac7'
SOURCE_REVIEW = 'e6ee8aa4f7010a6f8cd9dfb8eaeac5041ae7992f39ceacd3fc8dae4b4f6cb06c'
PREVIOUS_NATIVE = 'b506d6d4c6dd9961f771803718196b672656328d24b2c5f456166d076ea93a5d'
PRODUCTION = {
    'MilitarySettlementRuntime.wurst': 'e06c2f7576bafacf66adb7df098677b51620415712e4d4a5e8ca48c8a9010b6e',
    'PlayableCampaignRuntime.wurst': 'a5b708859532eada5bca21655ea573cab87b922c432570bd4523c0edf125a580',
}
TESTS = {
    'MilitarySnapshotValidationTests.wurst': '65d066ca668866c64c056412b73b424b63291cd6032d2caefe6149e80bf49602',
    'CampaignAuthorityPerformanceTests.wurst': 'c66195704cd69c9723e7f67ce7923795eb56a14aab29f6190e1fb0134381e612',
}
BASELINE_PRODUCTION = {
    'MilitarySettlementRuntime.wurst': '6ff22cf29821cbb1caff3f91686b053213ab2d7e4b9a87d04d1995fd6c4a33c7',
    'PlayableCampaignRuntime.wurst': 'bb1b6fb4330dfb0727b756132b3269bbad1db8b23c6f02ec6bed5073146118fa',
}
CAPTURE_PRODUCTION = {
    **BASELINE_PRODUCTION,
    'PlayableCampaignRuntime.wurst': '47a9f534d29d23a0542df28f9e5b6701fe759793d9a4857f234143c3ac8f43cc',
}
KNOWN_LUA = {
    'baseline': 'ba4a7640aefb1dec614fdc3cabaa23ba7b2f5e495997f0fde5f131b037580345',
    'captureOnly': '0b4badfc5cdb7431f48ad633b37e9f9a634a5fba97305584660804462d2d9990',
}
WORLD_COUNTS = {'forces': 1553, 'markets': 8422, 'provenanceLots': 0, 'settlements': 827, 'stores': 829}
FINAL_REQUEST = 'v1|1|consumed|austria|europe_central_east|europe_central_alpine|vienna'
SAVE_IDENTITIES = [
    ('bootstrap', 'campaign_start_1', 1067493, '11ed6ed4f4fce5fe74fd14d75c376eed16988cc43b5778c770bc919db0b76c02'),
    ('campaign', 'session_start', 1067491, 'b95920dbfae43ab0532bd0a61e01e57d1f8b520de796c8c81b451266b14f7880'),
    ('campaign', 'major_milestone', 1067492, '5bacd39de86dd3cba9d9ef821363d701290afdd087ebf8025429969da2066aa7'),
    ('bootstrap', 'request', 70, 'ddbd3d75f93d4a8e78a6e1f835a10692b8df81a120f83e7ee93479a35810eb2d'),
]
PHASE_NAMES = {
    'PlayableCampaignState_PlayableCampaignState_captureAuthoritativeState',
    'PlayableCampaignState_PlayableCampaignState_validateAuthoritativeState',
    'MilitarySettlementRuntime_MilitarySettlementRuntime_parseSnapshot',
    'runtimeChecksum',
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def canonical_digest(value):
    return sha(json.dumps(value, sort_keys=True, separators=(',', ':')).encode())


def source_identity(digest=SOURCE):
    return {'sourceRevision': BASELINE, 'sourceTreeSha256': digest}


def safe_relative(value):
    require(isinstance(value, str) and value and '\\' not in value, 'Invalid evidence path')
    path = PurePosixPath(value)
    require(path.parts and not path.is_absolute() and path.as_posix() == value and
            all(part not in ('..', '.') for part in path.parts), 'Unsafe evidence path: ' + value)
    return value


class Evidence:
    def __init__(self, root):
        self.root = root.resolve()
        self.manifest = json.loads((self.root / 'manifest.json').read_text())
        manifest = self.manifest
        require(manifest['format'] == 'startup_work_reduction_evidence_v1', 'Manifest format')
        require(manifest['status'] == 'complete_source_evidence_native_not_run', 'Pack is not complete')
        require(manifest['baselineRevision'] == BASELINE and manifest['sourceIdentity'] == source_identity(),
                'Manifest source identity')
        require(manifest['nativeStatus'] == 'not_run' and manifest['nativeHangResolution'] == 'not_established'
                and manifest['playerArtifactProduced'] is False, 'Unsupported native or player-artifact claim')
        self.raw, self.decoded, self.entries = {}, {}, {}
        for entry in manifest['files']:
            relative = safe_relative(entry['file'])
            require(relative not in self.raw and relative != 'manifest.json', 'Duplicate or self manifest entry')
            path = self.root / relative
            require(path.resolve().is_relative_to(self.root), 'Evidence escapes report pack')
            require(not any(parent.is_symlink() for parent in [path, *path.parents]
                            if parent.is_relative_to(self.root)), 'Evidence symlink')
            raw = path.read_bytes()
            require(len(raw) == entry['packagedBytes'] and sha(raw) == entry['packagedSha256'],
                    relative + ': packaged bytes/digest')
            if entry['encoding'] == 'gzip_mtime_0':
                require(raw[:4] == b'\x1f\x8b\x08\x00' and raw[4:8] == b'\0\0\0\0',
                        relative + ': deterministic gzip header')
                decoded = gzip.decompress(raw)
            else:
                require(entry['encoding'] == 'identity', relative + ': encoding')
                decoded = raw
            require(len(decoded) == entry['originalBytes'] and sha(decoded) == entry['originalSha256'],
                    relative + ': original bytes/digest')
            self.raw[relative], self.decoded[relative], self.entries[relative] = raw, decoded, entry
        actual = set()
        for path in self.root.rglob('*'):
            require(not path.is_symlink(), 'Unexpected symlink in pack')
            if path.is_file() and path != self.root / 'manifest.json':
                actual.add(path.relative_to(self.root).as_posix())
        require(actual == set(self.raw), 'Manifest must bind the exact file set')
        require('verify-evidence.py' in actual, 'Verifier must be retained and hash-bound')
        require(sha(self.decoded['common/wurst_execution.py']) == GATE, 'Changed retained Wurst gate')
        sys.dont_write_bytecode = True
        spec = importlib.util.spec_from_file_location('retained_wurst_gate', self.root / 'common/wurst_execution.py')
        self.gate = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.gate)

    def read(self, relative):
        return json.loads(self.decoded[safe_relative(relative)])

    def bind(self, identity, relative, *, raw=False):
        data = (self.raw if raw else self.decoded)[safe_relative(relative)]
        require(identity['sha256'] == sha(data), relative + ': referenced digest')
        if 'bytes' in identity:
            require(identity['bytes'] == len(data), relative + ': referenced byte count')

    def bind_recorded_path(self, identity):
        marker = '/validation-536/continue-fix/'
        require(marker in identity['path'], 'Runner identity is outside retained workspace evidence')
        self.bind(identity, identity['path'].split(marker, 1)[1])

    def verify_wurst(self, report, log):
        try:
            self.gate.verify_evidence(report, log, BASELINE)
        except self.gate.WurstExecutionError as error:
            raise ValueError('Retained unchanged Wurst gate rejected evidence: ' + str(error)) from error


def verify_focused(pack):
    review = pack.read('source-review.json')
    require(sha(pack.decoded['source-review.json']) == SOURCE_REVIEW, 'Source review identity')
    require(review['sourceIdentity'] == source_identity() and
            review['status'] == 'source-review-pass-native-unresolved', 'Source review scope')
    require({Path(key).name: value for key, value in review['frozenSourceInputs'].items()} == PRODUCTION | TESTS,
            'Source review frozen inputs')
    require(len(review['testAttempts']) == 4, 'All military focused attempts must remain visible')
    for number, row in enumerate(review['testAttempts'], 1):
        require(row['attempt'] == number and row['succeeded'] == [0, 27, 27, 28][number - 1],
                'Historical focused result changed')
        for relative, digest in row['retainedEvidence'].items():
            require(sha(pack.decoded[relative]) == digest, relative + ': source-review binding')
        prefix = f'military-focused-attempt{number}'
        result = pack.read(prefix + '/results.json')
        log = pack.decoded[prefix + '/execution.log']
        require(result['logSha256'] == sha(log) and result['discovered'] == 28 and
                result['succeeded'] == row['succeeded'], prefix + ': raw result binding')
        if number < 4:
            require(result['status'] == 'fail' and result['returnCode'] != 0 and result['errors'],
                    prefix + ': failed attempt was relabeled')
        else:
            verify_focused_pass(pack, prefix, 28, source_identity(), PRODUCTION,
                                {'MilitarySnapshotValidationTests.wurst': TESTS['MilitarySnapshotValidationTests.wurst']})
    require(sha(pack.decoded['run-authority-focused-tests-attempt3.py']) == CAPTURE_RUNNER,
            'Capture-focused runner identity')
    verify_focused_pass(pack, 'authority-focused-attempt3', 21, source_identity(CAPTURE_SOURCE),
                        CAPTURE_PRODUCTION, {'CampaignAuthorityPerformanceTests.wurst': TESTS['CampaignAuthorityPerformanceTests.wurst']})
    # Earlier capture setup failures are retained if collected; no passing
    # result or completed test execution is inferred from those receipts.
    for prefix in ('authority-focused', 'authority-focused-attempt2'):
        if prefix + '/results.json' in pack.decoded:
            result = pack.read(prefix + '/results.json')
            require(result['status'] == 'fail' and result['logSha256'] == sha(pack.decoded[prefix + '/execution.log']),
                    prefix + ': historical failure binding')


def verify_focused_pass(pack, prefix, count, identity, production, selected_tests):
    result = pack.read(prefix + '/results.json')
    context = pack.read(prefix + '/focused-context.json')
    pack.verify_wurst(result, pack.decoded[prefix + '/execution.log'])
    require(result['discovered'] == result['succeeded'] == context['selectedCount'] == count,
            prefix + ': complete selected discovery')
    require(context['status'] == 'pass' and context['sourceIdentityAtAssembly'] == identity and
            context['nativeStatus'] == 'not_run', prefix + ': source/scope')
    require(context['selectedTests'] == result['expected'] and
            context['interpreterInputsBefore'] == result['inputs'], prefix + ': input/discovery binding')
    for flag in ('dependencyInputsUnchanged', 'interpreterInputsUnchanged', 'authoredWurstUnchanged'):
        require(context[flag] is True, prefix + ': ' + flag)
    for flag in ('repositoryTestAnnotationsModified', 'releaseGateModified'):
        require(context[flag] is False, prefix + ': ' + flag)
    for name, digest in (production | selected_tests).items():
        require(result['inputs']['wurst/' + name] == digest, prefix + ': selected source ' + name)


def verify_builds(pack):
    paths = pack.manifest['compiledPaths']
    require(set(paths) == {'baseline', 'captureOnly', 'combined', 'captureComparison', 'combinedComparison'},
            'Compiled roles')
    require(len(set(paths.values())) == 5, 'Compiled roles must have distinct paths')
    for path in paths.values():
        safe_relative(path)
    builds, inputs, dependencies = {}, {}, {}
    for role, expected_source, expected_production in [
        ('baseline', BASELINE_SOURCE, BASELINE_PRODUCTION),
        ('captureOnly', CAPTURE_SOURCE, CAPTURE_PRODUCTION),
        ('combined', SOURCE, PRODUCTION),
    ]:
        prefix = paths[role]
        build = pack.read(prefix + '/build-result.json')
        builds[role] = build
        require(build['format'] == 'continue_fix_isolated_europe_compile_v1' and build['status'] == 'pass',
                prefix + ': terminal build status')
        require(build['baselineRevision'] == BASELINE and
                build['sourceIdentityAtAssembly'] == source_identity(expected_source), prefix + ': source identity')
        require(build['nativeStatus'] == 'not_run' and build['playerArtifactProduced'] is False and
                build['compilerSha256'] == COMPILER and build['dependencyRevision'] == DEPENDENCY and
                build['dependencyInstallInvoked'] is False, prefix + ': compiler/dependency/scope')
        for flag in ('compilerOutputEqualsArchiveLua', 'independentKnownMembersEqual', 'authoredSourcesUnchanged'):
            require(build[flag] is True, prefix + ': ' + flag)
        require(not build.get('error'), prefix + ': terminal error')
        require(re.fullmatch('[0-9a-f]{64}', build['compiledScriptSha256']) and build['compiledScriptBytes'] > 1_000_000,
                prefix + ': compiled identity')
        if role in KNOWN_LUA:
            require(build['compiledScriptSha256'] == KNOWN_LUA[role], prefix + ': established archived Lua identity')
        require(build['extracted']['war3map.lua']['sha256'] == build['compiledScriptSha256'] and
                build['extracted']['war3map.lua']['bytes'] == build['compiledScriptBytes'], prefix + ': archive Lua binding')
        inputs[role] = pack.read(prefix + '/inputs-before.json')
        require(inputs[role] == pack.read(prefix + '/inputs-after.json'), prefix + ': compiler inputs changed')
        dependencies[role] = pack.read(prefix + '/dependency-before.json')
        for name, digest in expected_production.items():
            require(inputs[role]['wurst/' + name] == digest, prefix + ': production source ' + name)
        require([row['stage'] for row in build['stages']] == ['typecheck', 'build'], prefix + ': compile stages')
        for row in build['stages']:
            require(row['exitCode'] == 0 and row['inputsUnchanged'] is True and
                    row['compiler']['sha256'] == COMPILER, prefix + ': stage result')
            pack.bind(row['log'], prefix + '/' + row['stage'] + '.log')
        if 'runner' in build:
            pack.bind_recorded_path(build['runner'])
        if role != 'baseline':
            require(build['generatedInputs'] == builds['baseline']['generatedInputs'] and
                    build['mapInputs'] == builds['baseline']['mapInputs'], prefix + ': changed scenario/map inputs')
            require(dependencies[role] == dependencies['baseline'], prefix + ': changed dependency inputs')
            require(set(inputs[role]) == set(inputs['baseline']), prefix + ': changed assembly file set')
            changed = [{'file': key, 'before': inputs['baseline'][key], 'after': inputs[role][key]}
                       for key in sorted(inputs[role]) if inputs['baseline'][key] != inputs[role][key]]
            expected_names = {'wurst/PlayableCampaignRuntime.wurst'} if role == 'captureOnly' else {
                'wurst/PlayableCampaignRuntime.wurst', 'wurst/MilitarySettlementRuntime.wurst'}
            require({row['file'] for row in changed} == expected_names and
                    build['changedProductionInputs'] == changed, prefix + ': exact production change set')
    # The first combined attempt must remain an explicitly failed receipt.
    failed_prefix = 'europe-combined'
    failed = pack.read(failed_prefix + '/build-result.json')
    require(failed['status'] == 'fail' and failed.get('error') and
            failed['sourceIdentityAtAssembly'] == source_identity() and failed['nativeStatus'] == 'not_run',
            'Original combined failure was hidden or relabeled')
    require(any(stage['exitCode'] != 0 for stage in failed['stages']), 'Failed combined compiler exit')
    for stage in failed['stages']:
        pack.bind(stage['log'], failed_prefix + '/' + stage['stage'] + '.log')
    if 'runner' in failed:
        pack.bind_recorded_path(failed['runner'])
    failure = pack.read(failed_prefix + '/resource-failure-observation.json')
    pack.bind(failure['buildResult'], failed_prefix + '/build-result.json')
    pack.bind(failure['compilerBuildLog'], failed_prefix + '/build.log')
    require(failure['nativeStatus'] == 'not_run' and failure['sourceOrGateChanges'] is False and
            failure['compilerChildExitCodeReportedByGrill'] == 137,
            'Resource-failure observation scope')
    return builds, dependencies


def phase_rows(observed):
    return [{key: row[key] for key in ('name', 'nativeCalls', 'instructions', 'completed')}
            for row in observed['execution']['phases'] if row['name'] in PHASE_NAMES]


def callback_rows(observed):
    return [{key: row[key] for key in ('atSeconds', 'kind', 'completed', 'nativeCalls')}
            for row in observed['execution']['callbacks']]


def verify_comparison(pack, role, revised_role, builds, *, combined):
    paths = pack.manifest['compiledPaths']
    prefix = paths[role]
    comparison = pack.read(prefix + '/comparison.json')
    require(comparison['status'] == 'pass_under_explicit_models' and comparison['nativeStatus'] == 'not_run' and
            comparison['nativeHangResolution'] == 'not_established', prefix + ': supplemental scope')
    pack.bind_recorded_path(comparison['runner'])
    require(comparison['library']['sha256'] == LIBRARY, prefix + ': modeled Lua runtime')
    frozen, observed, payloads = {}, {}, {}
    for side, build_role in [('baseline', 'baseline'), ('revised', revised_role)]:
        side_prefix = prefix + '/' + side
        build = builds[build_role]
        build_path = paths[build_role] + '/build-result.json'
        pack.bind(comparison['baselineBuild' if side == 'baseline' else 'revisedBuild'], build_path)
        run = pack.read(side_prefix + '/frozen/result.json')
        observation = pack.read(side_prefix + '/observer/startup-and-first-callbacks.json')
        frozen[side], observed[side], payloads[side] = run, observation, []
        pack.bind(run['boundBuildReceipt'], build_path)
        pack.bind_recorded_path(run['runner'])
        require(run['status'] == 'completed_under_stubs' and run['completed'] is True and
                run['campaignStarted'] is True and run['campaignRegistered'] is True and
                run['expectedStop'] is False and run['nativeStatus'] == 'not_run' and
                run['runtimeVersion'] == 'Lua 5.3', side_prefix + ': frozen probe completion/scope')
        require(run['compiledLuaSha256'] == build['compiledScriptSha256'] and
                run['harnessSha256'] == HARNESS and run['lateNativeStubsSha256'] == STUBS,
                side_prefix + ': frozen inputs')
        require(run['instructions'] <= run['instructionBudget'] == 2_000_000_000,
                side_prefix + ': bounded model execution')
        require(run['runtimeCounts'] == WORLD_COUNTS and run['finalCacheRequest'] == FINAL_REQUEST,
                side_prefix + ': world/selected handoff authority')
        require(observation['status'] == 'completed_under_explicit_stubs' and
                observation['nativeStatus'] == 'not_run' and observation['runtimeVersion'] == 'Lua 5.3' and
                observation['releaseStatus'] == 'not_a_release_gate', side_prefix + ': observer scope')
        inputs = observation['inputs']
        for field, target in [('buildReceipt', build_path),
                              ('harness', side_prefix + '/frozen/probe-lua54-initialization.py'),
                              ('nativeStubs', side_prefix + '/frozen/late-startup-stubs.lua'),
                              ('observer', side_prefix + '/observer/observe-startup.lua'),
                              ('runner', side_prefix + '/observer/observe-startup.py')]:
            pack.bind(inputs[field], target)
        require(inputs['compiledLua']['sha256'] == build['compiledScriptSha256'] and
                inputs['compiledLua']['bytes'] == build['compiledScriptBytes'] and
                inputs['library']['sha256'] == LIBRARY and inputs['harness']['sha256'] == HARNESS and
                inputs['nativeStubs']['sha256'] == STUBS, side_prefix + ': actual probe/observer bindings')
        execution = observation['execution']
        require(execution['nativeStatus'] == 'not_run' and execution['startupCompleted'] is True and
                execution['startup']['started'] is True and execution['startup']['registered'] is True and
                execution['startup']['finalCacheRequest'] == FINAL_REQUEST and
                execution['startup']['nativeCalls'] == run['nativeCalls'], side_prefix + ': startup/readiness')
        callbacks = execution['callbackPhase']
        require(callbacks['completed'] is True and callbacks['callbackCount'] == 37 and
                callbacks['throughSeconds'] == 1.001 and execution['callbackErrors'] in ([], {}) and
                callbacks['instructions'] <= callbacks['budget'] == 200_000_000 and
                len(execution['callbacks']) == 37 and all(row['completed'] is True for row in execution['callbacks']),
                side_prefix + ': first modeled callbacks')
        require(len(observation['cachePayloads']) == 4, side_prefix + ': saved payload count')
        for index, (row, expected) in enumerate(zip(observation['cachePayloads'], SAVE_IDENTITIES), 1):
            saved_path = side_prefix + f'/observer/cache-write-{index}.txt.gz'
            require(pack.entries[saved_path]['encoding'] == 'identity', saved_path + ': preserve original compression')
            pack.bind(row['compressed'], saved_path, raw=True)
            saved = gzip.decompress(pack.raw[saved_path])
            identity = (row['mission'], row['key'], len(saved), sha(saved))
            require(identity == expected and row['bytes'] == len(saved) and row['sha256'] == sha(saved),
                    saved_path + ': actual saved bytes')
            payloads[side].append(saved)
    before, after = frozen['baseline'], frozen['revised']
    require(before['nativeCalls']['SubString'] == 15_095_868 and before['nativeCalls']['StringHash'] == 37_931,
            prefix + ': established baseline work counts')
    require(after['nativeCalls']['SubString'] < before['nativeCalls']['SubString'], prefix + ': modeled work reduction')
    names = sorted(set(before['nativeCalls']) | set(after['nativeCalls']))
    expected_calls = {name: {'before': before['nativeCalls'].get(name, 0), 'after': after['nativeCalls'].get(name, 0),
                            'difference': after['nativeCalls'].get(name, 0) - before['nativeCalls'].get(name, 0)}
                      for name in names}
    require(comparison['nativeCalls'] == expected_calls, prefix + ': work counts derived from raw probes')
    for name in ('CreateUnit', 'StoreString', 'SaveGameCache', 'InitGameCache', 'InitBlizzard', 'TimerStart'):
        require(before['nativeCalls'][name] == after['nativeCalls'][name], prefix + ': unchanged native call count ' + name)
    require(comparison['instructionSamples'] == {'before': before['instructions'], 'after': after['instructions']},
            prefix + ': instruction samples')
    for field in ('runtimeCounts', 'tradeSnapshotIdentity', 'finalCacheRequest'):
        require(before[field] == after[field] == comparison[field], prefix + ': preserved ' + field)
    require(payloads['baseline'] == payloads['revised'], prefix + ': saved payload bytes differ')
    actual_payloads = []
    for saved, expected in zip(payloads['revised'], SAVE_IDENTITIES):
        non_ascii = sum(byte >= 128 for byte in saved)
        actual_payloads.append({'mission': expected[0], 'key': expected[1], 'bytes': len(saved), 'sha256': sha(saved),
                                'exactPreviousBytesEqual': True, 'asciiOnly': non_ascii == 0,
                                'nonAsciiByteCount': non_ascii})
    require(comparison['cachePayloads'] == actual_payloads and
            comparison['cachePayloadBytesTotal'] == sum(map(len, payloads['revised'])),
            prefix + ': actual payload comparison receipt')
    require(callback_rows(observed['baseline']) == callback_rows(observed['revised']),
            prefix + ': callback order/native observations differ')
    for field, expected in [('phases', {key: phase_rows(observed[side]) for key, side in [('before', 'baseline'), ('after', 'revised')]}),
                            ('callbackPhases', {key: observed[side]['execution']['callbackPhase'] for key, side in [('before', 'baseline'), ('after', 'revised')]}),
                            ('nativeArgumentVolumes', {key: observed[side]['execution']['nativeArgumentVolumes'] for key, side in [('before', 'baseline'), ('after', 'revised')]})]:
        require(comparison[field] == expected, prefix + ': observer-derived ' + field)
    for rows in comparison['phases'].values():
        require(all(row['completed'] is True for row in rows), prefix + ': incomplete measured phase')
    parse_name = 'MilitarySettlementRuntime_MilitarySettlementRuntime_parseSnapshot'
    counts = {key: sum(row['name'] == parse_name for row in rows) for key, rows in comparison['phases'].items()}
    require(counts == {'before': 2, 'after': 1 if combined else 2}, prefix + ': detached parser count')
    left_observer = pack.decoded[prefix + '/baseline/observer/observe-startup.lua']
    right_observer = pack.decoded[prefix + '/revised/observer/observe-startup.lua']
    require(left_observer == right_observer, prefix + ': observer must match across compiled inputs')
    if combined:
        original = pack.decoded[paths['captureComparison'] + '/baseline/observer/observe-startup.lua']
        removed = b" 'MilitarySettlementRuntime_MilitarySettlementRuntime_validateSnapshot',\n"
        require(sha(original) == OBSERVER and original.count(removed) == 1 and
                left_observer in (original, original.replace(removed, b'')), 'Unexpected observer semantic change')
        variant = comparison['observerVariant']
        pack.bind(variant['original'], paths['captureComparison'] + '/baseline/observer/observe-startup.lua')
        pack.bind(variant['selected'], prefix + '/baseline/observer/observe-startup.lua')
        require(variant['productionFunctionOverridesAdded'] is False, 'Observer variant scope')
        if left_observer != original:
            require(variant['targetDefinedInBaseline'] is True and variant['targetDefinedInRevised'] is False,
                    'Dead-stripped measurement wrapper scope')
        require(comparison['nativeArgumentVolumeScope'] == 'Startup and modeled callbacks through 1.001 simulated seconds',
                'Argument-volume scope must include modeled callbacks')
    else:
        require(sha(left_observer) == OBSERVER, 'Changed capture-only observer')
    return comparison


def verify_full_suite(pack, build_dependencies):
    prefix = 'full-wurst-tests'
    receipt = pack.read(prefix + '/run-receipt.json')
    result = pack.read(prefix + '/results.json')
    log_path = prefix + '/execution.log.gz'
    require(pack.entries[log_path]['encoding'] == 'gzip_mtime_0', 'Full transcript compression')
    log = pack.decoded[log_path]
    require(receipt['format'] == 'warcraftmap_dirty_full_wurst_regression_v1' and
            receipt['status'] == 'pass' and receipt['executionStatus'] == 'completed', 'Full suite is not complete')
    require(receipt['testCount'] == receipt['discovered'] == receipt['succeeded'] == 671,
            'Full authored Wurst discovery count')
    require(receipt['baselineRevision'] == BASELINE and receipt['baselineRevisionIsActualCleanSource'] is False and
            receipt['sourceState'] == 'dirty_working_tree_bound_to_source_and_compiler_input_hashes',
            'Frozen working-tree scope must remain explicit')
    require(receipt['sourceIdentity'] == result['sourceIdentity'] == source_identity(), 'Full suite source identity')
    for field in ('repositoryTestAnnotationsModified', 'repositoryTestDeadlinesModified',
                  'repositoryExecutionGateModified', 'playerArtifactProduced'):
        require(receipt[field] is False, 'Unexpected full-suite change: ' + field)
    require(receipt['nativeStatus'] == 'not_run' and receipt['executionGate'] == 'unchanged execute_tests(project=PROJECT)' and
            not receipt.get('boundaryErrors') and not receipt.get('error'), 'Full suite gate/scope/boundaries')
    require(receipt['resultsSha256'] == sha(pack.decoded[prefix + '/results.json']) and
            receipt['transcriptSha256'] == sha(log), 'Full suite raw result binding')
    pack.verify_wurst(result, log)
    require(receipt['actualInstrumentedInputSetSha256'] == result['inputSetSha256'], 'Instrumented gate input set')
    require(pack.read(prefix + '/complete-discovery.json') == result['expected'] and len(result['expected']) == 671,
            'All authored tests must match raw executed discovery')
    for stem, flag in [('source-inputs', 'authoritativeSourcesUnchanged'),
                       ('compiler-inputs', 'originalCompilerInputsRestoredAndUnchanged'),
                       ('dependency-inputs', 'dependencyInputsUnchanged'), ('toolchain', 'toolchainUnchanged')]:
        require(receipt[flag] is True and pack.read(prefix + '/' + stem + '-before.json') ==
                pack.read(prefix + '/' + stem + '-after.json'), 'Full-suite before/after: ' + stem)
    sources = pack.read(prefix + '/source-inputs-before.json')
    require(canonical_digest(sources) == receipt['authoritativeSourceSetSha256'] == SOURCE, 'Full source digest')
    require(sources['../_shared/tooling/wurst_execution.py'] == GATE, 'Full suite used the retained gate')
    original = pack.read(prefix + '/compiler-inputs-before.json')
    require(canonical_digest(original) == receipt['originalInputSetSha256'], 'Original compiler input digest')
    generated = {'wurst/' + name + '.wurst' for name in ('ScenarioData', 'ScenarioSettings', 'ConformanceData')}
    require(set(receipt['generatedSeedInputs']) == generated, 'Exactly three generated scenario packages')
    for name in generated:
        relative = prefix + '/generated/' + name.removeprefix('wurst/') + '.gz'
        require(pack.entries[relative]['encoding'] == 'gzip_mtime_0' and
                sha(pack.decoded[relative]) == receipt['generatedSeedInputs'][name] == original[name],
                'Generated test input: ' + name)
    for name, digest in PRODUCTION.items():
        require(sources['../_shared/wurst/' + name] == original['wurst/' + name] == digest,
                'Full suite production input: ' + name)
    for name, digest in TESTS.items():
        require(sources['wurst/' + name] == original['wurst/' + name] == digest, 'Full suite test input: ' + name)
    dependency = pack.read(prefix + '/dependency-inputs-before.json')
    require(dependency['revision'] == receipt['dependencyRevision'] == DEPENDENCY and dependency['dirty'] is False,
            'Full suite dependency revision')
    require(canonical_digest(dependency['inputs']) == dependency['inputSetSha256'] == receipt['dependencyInputSetSha256'],
            'Full suite dependency digest')
    for name, digest in build_dependencies['combined'].items():
        require(dependency['inputs'][name] == digest, 'Compile/full-suite dependency differs: ' + name)
    require(pack.read(prefix + '/toolchain-before.json')['compiler']['sha256'] == receipt['compilerSha256'] == COMPILER,
            'Full suite compiler identity')
    require(sha(pack.decoded['run-full-wurst-tests.py']) == FULL_RUNNER, 'Full suite runner binding')


def verify_source_checks(pack):
    prefix = 'source-checks/'
    receipt = pack.read(prefix + 'receipt.json')
    require(receipt['format'] == 'source_report_refresh_v1' and receipt['baselineRevision'] == BASELINE and
            receipt['sourceIdentity'] == source_identity(), 'Source-report refresh identity')
    require(receipt['status'] == 'pass_freshness_with_acceptance_still_blocked' and
            receipt['nativeStatus'] == 'not_run' and receipt['sourcesUnchanged'] is True and
            receipt['worktreeDirty'] is True, 'Source-report refresh must not imply acceptance')
    expected = [('runtime', 1), ('release', 1), ('traceability', 0), ('report-freshness', 0), ('diff-check', 0)]
    require([(row['name'], row['expectedExitCode']) for row in receipt['commands']] == expected,
            'All five source-report commands and expected exits must be retained')
    for row in receipt['commands']:
        require(row['exitCode'] == row['expectedExitCode'], 'Source-report command exit: ' + row['name'])
        for stream in ('stdout', 'stderr'):
            path = prefix + row['name'] + '.' + stream
            require(sha(pack.decoded[path]) == row[stream + 'Sha256'], 'Source-report stream binding: ' + path)
    runtime = pack.read(prefix + 'runtime.stdout')
    release = pack.read(prefix + 'release.stdout')
    traceability = re.fullmatch(r'Traceability: (\d+) obligations; (\d+) publication blockers\n',
                               pack.decoded[prefix + 'traceability.stdout'].decode())
    require(runtime['status'] == release['status'] == 'fail' and
            receipt['runtimeFailures'] == runtime['failures'] == 30 and
            receipt['releaseBlockers'] == release['unresolvedCampaignBlockers'] == 238 and
            traceability is not None and receipt['traceabilityBlockers'] == int(traceability.group(2)) == 7004,
            'Source acceptance must retain the actual 30/238/7004 failures/blockers')
    freshness = pack.decoded[prefix + 'report-freshness.stderr'].decode()
    require(re.search(r'^test_checked_in_machine_and_human_reports_are_current .* \.\.\. ok$',
                      freshness, flags=re.MULTILINE) is not None and
            re.search(r'^Ran 1 test in [0-9.]+s\n\nOK\n?\Z', freshness, flags=re.MULTILINE) is not None and
            not re.search(r'\b(?:FAILED|ERROR|skipped)\b', freshness), 'Report freshness must retain one passing test')
    require(pack.decoded[prefix + 'diff-check.stdout'] == pack.decoded[prefix + 'diff-check.stderr'] == b'',
            'Source diff check must be clean')
    previous = pack.read('previous-native-observation.json')
    require(sha(pack.decoded['previous-native-observation.json']) == PREVIOUS_NATIVE,
            'Previous native observation must be preserved byte for byte')
    require(previous['format'] == 'owner_native_transition_observation_v1' and
            previous['pullRequest'] == 536 and previous['issue'] == 438 and
            previous['sourceRevision'] == 'a1b43969eb57de4127b005956823d6b876a86068' and
            previous['expectedCampaignSha256'] == '9ea9a0e554fe70f6c85ca99c12718bb867d83658cad36635b39bc20dfd3ea742' and
            previous['expectedZipSha256'] == 'c2473202be4433f41cd90b4fe4feaa7337b5f3f3630540e2070dbf8a58b66636',
            'Previous native candidate identity')
    require(previous['destinationGameplay'] == 'failed' and previous['destinationLuaInitialized'] == 'unknown' and
            previous['durationSeconds'] is None and previous['eventualRecovery'] == 'unknown' and
            previous['installedFileHashRecollected'] is False and previous['diagnosis'] == 'unconfirmed' and
            previous['releaseCandidate'] is False and previous['unchangedRetestRequested'] is False,
            'Previous native failure and uncertainty must remain explicit')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parent, help='Retained report-pack directory')
    args = parser.parse_args()
    pack = Evidence(args.root)
    verify_focused(pack)
    builds, dependencies = verify_builds(pack)
    capture = verify_comparison(pack, 'captureComparison', 'captureOnly', builds, combined=False)
    combined = verify_comparison(pack, 'combinedComparison', 'combined', builds, combined=True)
    require(combined['nativeCalls']['SubString']['after'] < capture['nativeCalls']['SubString']['after'],
            'Final combined source must retain the further measured parse reduction')
    verify_full_suite(pack, dependencies)
    verify_source_checks(pack)
    print(json.dumps({'status': 'pass_retained_source_evidence_integrity_native_not_run',
                      'filesVerified': len(pack.raw), 'fullWurstTests': 671, 'focusedMilitaryTests': 28,
                      'focusedCaptureTests': 21, 'savedPayloadsComparedPerBuild': 4,
                      'nativeStatus': 'not_run', 'nativeHangResolution': 'not_established',
                      'playerArtifactProduced': False,
                      'compiledArtifactScope': 'retained archive identities and equality receipts; binaries not re-extracted'},
                     sort_keys=True))


if __name__ == '__main__':
    try:
        main()
    except (OSError, KeyError, TypeError, ValueError, EOFError) as error:
        raise SystemExit('Evidence verification failed: ' + str(error)) from error
