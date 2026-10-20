#!/usr/bin/env python3
"""Check retained evidence only. Does not execute Lua, a compiler, or a native client."""
import argparse
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path, PurePosixPath
import sys

ROOT = Path(__file__).resolve().parent
BASELINE = 'a1b43969eb57de4127b005956823d6b876a86068'
SOURCE = '2f55ec1dc084ab27c1a4fde2897728035ea49f086c8fbdd3e1d1cb3aeca22d8b'
OLD_LUA = 'a4fc97bb27b36466bc62bad74605128258c6847c4f46791efe2df184c3f85a45'
NEW_LUA = 'dec76da8c9ba445e315237a44a6dff415c81c07109b7f3f05dab1af806db3626'
COMPILER = '1f3ae40b1018b8757867515596adfa69113ca85f390c1b353cc8b69cf8944145'
LIBRARY = 'fdaa987d06dd329be3232a65ea71cae427f3bfd26f5b757d8853628d33d9492a'
GATE = '49fe8dd2c491ef16ebfcfb481aa782d27c1356779ad229b10e0ba1b108513101'
PRODUCTION = {
    'CampaignSaveManager.wurst': '48e6f7dc416bf03e8f6895d4569bbd0222ea68d2f2ca4bac33c9c221654fe6ce',
    'WC3Compatibility.wurst': '18e48350fe412e847b3877534e695179177fad18f243cdf707b282412c8a75a1',
    'PlayableCampaignRuntime.wurst': 'bb1b6fb4330dfb0727b756132b3269bbad1db8b23c6f02ec6bed5073146118fa',
}
TESTS = {
    'WarcraftCampaignSaveStorageTests.wurst': '9a06d9b4240f8938e14d150582c8a0b1af3ab169b08a9b7eb0ed59fe73743884',
    'CampaignAuthorityPerformanceTests.wurst': 'fd6b0540b647aabb983757b51def17f7977cb0909e7e499413f21f1b089a776a',
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def canonical_digest(value):
    return sha(json.dumps(value, sort_keys=True, separators=(',', ':')).encode())


def verify_wurst(report, log):
    # Load the byte-identical retained gate, then call only its read-only receipt
    # parser. No compiler discovery or execution function is invoked.
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location('retained_wurst_execution', ROOT / 'common/wurst_execution.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    try:
        module.verify_evidence(report, log, BASELINE)
    except module.WurstExecutionError as error:
        raise ValueError('Retained Wurst gate rejected evidence: ' + str(error)) from error


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--allow-pending', action='store_true',
                        help='Check available evidence, with an explicitly incomplete result.')
    args = parser.parse_args()
    manifest = json.loads((ROOT / 'manifest.json').read_text())
    require(manifest['format'] == 'native_boundary_repair_evidence_manifest_v1', 'Manifest format')
    require(manifest['nativeStatus'] == 'not_run', 'Unexpected native acceptance')
    require(manifest['nativeTransitionAcceptance'] == 'not_established', 'Native transition status')
    require(manifest['publicationScope'] == 'source_correction_only_no_new_player_campaign', 'Scope')
    decoded = {}
    for entry in manifest['files']:
        rel = entry['file']
        pure = PurePosixPath(rel)
        require(not pure.is_absolute() and pure.as_posix() == rel and
                all(part not in ('..', '.') for part in pure.parts), 'Unsafe evidence path')
        require(rel not in decoded and rel != 'manifest.json', 'Duplicate or self manifest entry')
        path = ROOT / rel
        require(path.resolve().is_relative_to(ROOT), 'Evidence path escapes pack')
        require(not any((ROOT / PurePosixPath(*pure.parts[:i])).is_symlink()
                        for i in range(1, len(pure.parts) + 1)), 'Evidence symlink')
        payload = path.read_bytes()
        require(len(payload) == entry['packagedBytes'], f'{rel}: packaged bytes')
        require(sha(payload) == entry['packagedSha256'], f'{rel}: packaged digest')
        if entry['encoding'] == 'gzip_mtime_0':
            compressed_text = {f'full-suite/generated/{name}.wurst.gz' for name in
                               ['ScenarioData', 'ScenarioSettings', 'ConformanceData']}
            compressed_text.add('full-suite/execution.log.gz')
            require(rel in compressed_text, 'Unexpected compressed evidence member')
            require(payload[:4] == b'\x1f\x8b\x08\x00' and payload[4:8] == b'\0\0\0\0',
                    f'{rel}: deterministic gzip header')
            payload = gzip.decompress(payload)
        else:
            require(entry['encoding'] == 'identity', f'{rel}: unexpected encoding')
        require(len(payload) == entry['originalBytes'], f'{rel}: original bytes')
        require(sha(payload) == entry['originalSha256'], f'{rel}: original digest')
        decoded[rel] = payload
    actual = set()
    for path in ROOT.rglob('*'):
        require(not path.is_symlink(), 'Unexpected symlink in pack')
        if path.is_file() and path != ROOT / 'manifest.json':
            actual.add(path.relative_to(ROOT).as_posix())
    require(actual == set(decoded), 'Manifest must cover the exact retained file set')
    require(sha(decoded['common/wurst_execution.py']) == GATE, 'Unchanged Wurst evidence gate')

    def read(name):
        return json.loads(decoded[name])

    def bound(item, name):
        require(item['sha256'] == sha(decoded[name]), f'{name}: referenced digest')
        if 'bytes' in item:
            require(item['bytes'] == len(decoded[name]), f'{name}: referenced length')

    owner = read('owner-native-observation.json')
    require(owner['sourceRevision'] == BASELINE and owner['destinationGameplay'] == 'failed',
            'Latest owner native failure must remain visible')
    require(owner['diagnosis'] == 'unconfirmed' and owner['durationSeconds'] is None and
            owner['destinationLuaInitialized'] == 'unknown' and owner['eventualRecovery'] == 'unknown',
            'Unsupported native conclusions')
    require(owner['expectedCampaignSha256'] ==
            '9ea9a0e554fe70f6c85ca99c12718bb867d83658cad36635b39bc20dfd3ea742', 'Observed candidate')
    require(owner['installedFileHashRecollected'] is False and owner['releaseCandidate'] is False,
            'Observed candidate limitations')

    for name, expected, lua_hash, returned, status in [
        ('cache/legacy-false-success-result.json', 'legacy-false-success', OLD_LUA, True,
         'reproduced_legacy_false_success_under_explicit_stubs'),
        ('compiled/cache-write-rejection.json', 'rejected-write', NEW_LUA, False,
         'pass_rejected_write_under_explicit_stubs'),
    ]:
        report = read(name)
        require(report['status'] == status and report['expectedBehavior'] == expected, name)
        require(report['nativeStatus'] == 'not_run' and report['runtimeVersion'] == 'Lua 5.3', name)
        require(report['productionFunctionOverrides'] is False, name)
        require(report['inputs']['compiledLua']['sha256'] == lua_hash, name)
        require(report['inputs']['runtimeLibrary']['sha256'] == LIBRARY, name)
        bound(report['inputs']['runner'], 'cache/cache-write-fault-probe.py')
        bound(report['inputs']['case'], 'cache/cache-write-fault-probe.lua')
        run = report['execution']
        require(run['returned'] is returned and run['stored'] is False, name)
        require(bool(run['diagnostic']) is (not returned), name)
        require(run['productionFunctionsUnchanged'] is True and run['configCalled'] is False and
                run['mainCalled'] is False and run['nativeStatus'] == 'not_run', name)
        require(run['sampledInstructions'] <= report['instructionBudget'] == 100_000, name)
        require(run['nativeCalls']['StoreString'] == run['nativeCalls']['SaveGameCache'] == 1, name)

    for family, count in [('cache', 15), ('authority', 20)]:
        for attempt in ['setup-failure', 'passed']:
            prefix = f'{family}/{attempt}'
            result = read(f'{prefix}/results.json')
            require(result['logSha256'] == sha(decoded[f'{prefix}/execution.log']), f'{prefix}: log')
            require(result['compiler']['sha256'] == COMPILER and result['discovered'] == count,
                    f'{prefix}: discovery/compiler')
            if attempt == 'setup-failure':
                require(result['status'] == 'fail' and result['returnCode'] != 0 and
                        result['succeeded'] == 0 and result['tests'] == [],
                        f'{prefix}: setup failure must stay unexecuted')
            else:
                verify_wurst(result, decoded[f'{prefix}/execution.log'])
                require(result['status'] == 'pass' and result['returnCode'] == 0 and
                        result['executionStatus'] == 'completed' and result['errors'] == [] and
                        result['succeeded'] == count == len(result['tests']), f'{prefix}: test result')
                expected = [(test['id'], test['line']) for test in result['expected']]
                actual_tests = [(test['id'], test['line']) for test in result['tests']]
                require(len(set(actual_tests)) == count and sorted(actual_tests) == sorted(expected) and
                        all(test['status'] == 'pass' for test in result['tests']), f'{prefix}: tests')
                context = read(f'{prefix}/focused-context.json')
                require(context['status'] == 'pass' and context['nativeStatus'] == 'not_run' and
                        context['releaseGateModified'] is False and
                        context['repositoryTestAnnotationsModified'] is False and
                        context['dependencyInputsUnchanged'] is True, f'{prefix}: context')
        result = read(f'{family}/passed/results.json')
        selected = (['CampaignSaveManager.wurst', 'WC3Compatibility.wurst',
                     'WarcraftCampaignSaveStorageTests.wurst'] if family == 'cache' else
                    ['PlayableCampaignRuntime.wurst', 'CampaignAuthorityPerformanceTests.wurst'])
        for filename in selected:
            require(result['inputs']['wurst/' + filename] == (PRODUCTION | TESTS)[filename],
                    f'{family}: selected source identity')

    for folder, completed in [('baseline-incomplete', False), ('baseline-extended', True)]:
        prefix = f'observer/{folder}'
        report = read(f'{prefix}/startup-and-first-callbacks.json')
        require(report['nativeStatus'] == 'not_run' and report['runtimeVersion'] == 'Lua 5.3', prefix)
        for key, target in [('runner', f'{prefix}/observe-startup.py'),
                            ('observer', f'{prefix}/observe-startup.lua'),
                            ('harness', 'common/probe-lua54-initialization.py'),
                            ('nativeStubs', 'common/late-startup-stubs.lua'),
                            ('buildReceipt', 'observer/baseline-build-receipt.json')]:
            bound(report['inputs'][key], target)
        require(report['inputs']['compiledLua']['sha256'] == OLD_LUA and
                report['inputs']['library']['sha256'] == LIBRARY, prefix)
        run = report['execution']
        require(run['startupCompleted'] is True and run['startup']['started'] is True and
                run['startup']['registered'] is True, prefix)
        require(run['callbackPhase']['completed'] is completed, prefix)
        if completed:
            require(report['status'] == 'completed_under_explicit_stubs' and
                    run['callbackPhase']['callbackCount'] == 37 and not run['callbackErrors'], prefix)
        else:
            require(report['status'] == 'failed' and
                    'BlzGetUnitCollisionSize' in json.dumps(run['callbackErrors']), prefix)
        require([item['bytes'] for item in report['cachePayloads']] ==
                [1_067_493, 1_067_491, 1_067_492, 70], prefix)

    runtime = read('common/lua53-runtime-verification.json')
    require(runtime['runtimeLibrarySha256'] == LIBRARY, 'Lua runtime identity')
    refresh = read('source-checks/report-refresh/receipt.json')
    checks = read('source-checks/source-checks.json')
    for report in [refresh, checks]:
        require(report['sourceIdentity'] == {'sourceRevision': BASELINE, 'sourceTreeSha256': SOURCE},
                'Final dirty source identity')
        require(report['worktreeDirty'] is True, 'Source must be labeled dirty at recording')
    require(refresh['status'] == 'pass_freshness_with_acceptance_still_blocked' and
            refresh['sourcesUnchanged'] is True, 'Source freshness')
    require([refresh['runtimeFailures'], refresh['releaseBlockers'], refresh['traceabilityBlockers']] ==
            [30, 238, 7004], 'Existing blockers must remain visible')
    require(all(row['exitCode'] == row['expectedExitCode'] for row in refresh['commands']), 'Refresh exits')
    require(checks['nativeAcceptance'] == 'not_run_for_repaired_source', 'Source checks native claim')
    require(checks['checks'][0]['testCount'] == 17 and 'raw transcript not copied' in
            checks['checks'][0]['evidence'], 'Source checks transcript limitation')

    if 'compiled/comparison.json' in decoded:
        verify_compiled(read, bound, decoded)
    pending = manifest['pending']
    if pending:
        require(manifest['status'].startswith('pending_'), 'Pending status mismatch')
        require(args.allow_pending, 'Pack remains pending: ' + ', '.join(pending))
        status = 'pass_retained_partial_evidence_integrity_pending_final_receipts'
    else:
        require(manifest['status'] == 'complete_source_evidence_native_not_run', 'Complete status')
        verify_final(read, bound, decoded)
        status = 'pass_retained_source_evidence_integrity_native_not_run'
    print(json.dumps({'status': status, 'filesVerified': len(decoded), 'pending': pending,
                      'publicationScope': manifest['publicationScope'],
                      'nativeStatus': 'not_run', 'nativeTransitionAcceptance': 'not_established'},
                     sort_keys=True))


def verify_final(read, bound, decoded):
    verify_compiled(read, bound, decoded)
    receipt = read('full-suite/run-receipt.json')
    result = read('full-suite/results.json')
    require(receipt['format'] == 'warcraftmap_dirty_full_wurst_regression_v1' and
            receipt['status'] == 'pass' and receipt['executionStatus'] == 'completed', 'Full-suite status')
    require(receipt['testCount'] == receipt['discovered'] == receipt['succeeded'] == 667,
            'Complete Wurst test count')
    require(receipt['baselineRevision'] == BASELINE and receipt['baselineRevisionIsActualCleanSource'] is False and
            receipt['sourceState'] == 'dirty_working_tree_bound_to_source_and_compiler_input_hashes',
            'Full-suite dirty source label')
    require(receipt['sourceIdentity'] == result['sourceIdentity'] ==
            {'sourceRevision': BASELINE, 'sourceTreeSha256': SOURCE}, 'Full-suite source identity')
    for key in ['repositoryTestAnnotationsModified', 'repositoryTestDeadlinesModified',
                'repositoryExecutionGateModified', 'playerArtifactProduced']:
        require(receipt[key] is False, 'Unexpected full-suite change: ' + key)
    require(receipt['nativeStatus'] == 'not_run' and
            receipt['executionGate'] == 'unchanged execute_tests(project=PROJECT)', 'Full-suite scope/gate')
    require(not receipt.get('boundaryErrors') and not receipt.get('error'), 'Full-suite boundary failure')
    require(receipt['resultsSha256'] == sha(decoded['full-suite/results.json']) and
            receipt['transcriptSha256'] == sha(decoded['full-suite/execution.log.gz']), 'Full-suite raw evidence')
    require(receipt['actualInstrumentedInputSetSha256'] == result['inputSetSha256'], 'Full-suite gate inputs')
    verify_wurst(result, decoded['full-suite/execution.log.gz'])
    discovery = read('full-suite/complete-discovery.json')
    require(discovery == result['expected'] and len(discovery) == 667, 'Full authored discovery')
    for stem, flag in [('source-inputs', 'authoritativeSourcesUnchanged'),
                       ('compiler-inputs', 'originalCompilerInputsRestoredAndUnchanged'),
                       ('dependency-inputs', 'dependencyInputsUnchanged'),
                       ('toolchain', 'toolchainUnchanged')]:
        require(receipt[flag] is True and read(f'full-suite/{stem}-before.json') ==
                read(f'full-suite/{stem}-after.json'), 'Full-suite before/after: ' + stem)
    sources = read('full-suite/source-inputs-before.json')
    require(canonical_digest(sources) == receipt['authoritativeSourceSetSha256'] == SOURCE,
            'Full source input digest')
    require(sources['../_shared/tooling/wurst_execution.py'] == GATE, 'Actual regression used retained gate')
    original = read('full-suite/compiler-inputs-before.json')
    require(canonical_digest(original) == receipt['originalInputSetSha256'], 'Original compiler input digest')
    generated = {f'wurst/{name}.wurst' for name in ['ScenarioData', 'ScenarioSettings', 'ConformanceData']}
    require(set(receipt['generatedSeedInputs']) == generated, 'Exactly three generated test seed inputs')
    for name in generated:
        retained = 'full-suite/generated/' + name.removeprefix('wurst/') + '.gz'
        require(sha(decoded[retained]) == receipt['generatedSeedInputs'][name] == original[name],
                'Generated input binding: ' + name)
    for name, digest in PRODUCTION.items():
        require(sources['../_shared/wurst/' + name] == original['wurst/' + name] == digest,
                'Full-suite production source ' + name)
    for name, digest in TESTS.items():
        require(sources['wurst/' + name] == original['wurst/' + name] == digest,
                'Full-suite regression source ' + name)
    dependency = read('full-suite/dependency-inputs-before.json')
    require(dependency['revision'] == receipt['dependencyRevision'] ==
            'cce79096e71dcb066cf94785bc5cb48ef66c26db' and dependency['dirty'] is False,
            'Full-suite dependency revision')
    require(canonical_digest(dependency['inputs']) == dependency['inputSetSha256'] ==
            receipt['dependencyInputSetSha256'], 'Full-suite dependency digest')
    for name, digest in read('compiled/build-result.json')['dependency']['inputs'].items():
        require(dependency['inputs'][name] == digest, 'Compile/regression dependency differs: ' + name)
    require(read('full-suite/toolchain-before.json')['compiler']['sha256'] ==
            receipt['compilerSha256'] == COMPILER, 'Full-suite compiler identity')


def verify_compiled(read, bound, decoded):
    build = read('compiled/build-result.json')
    require(build['status'] == build['archiveInspection'] == 'pass', 'Isolated build status')
    require(build['nativeStatus'] == 'not_run' and build['compilerSha256'] == COMPILER,
            'Isolated compiler identity/native scope')
    require(build['sourceIdentityAtAssembly'] ==
            {'sourceRevision': BASELINE, 'sourceTreeSha256': SOURCE}, 'Compile source identity')
    require(build['compiledScriptSha256'] == NEW_LUA and build['compiledScriptBytes'] == 16_113_292,
            'Compiled script identity')
    for key in ['compilerInputsUnchangedDuringBuild', 'compilerOutputEqualsArchiveLua',
                'independentKnownMembersEqual', 'frozenWpmEqual', 'authoredProductionUnchanged']:
        require(build[key] is True, 'Build check: ' + key)
    require(build['dependency']['revision'] == 'cce79096e71dcb066cf94785bc5cb48ef66c26db' and
            build['dependency']['dirty'] is False and build['dependencyInstallInvoked'] is False,
            'Isolated dependency provenance')
    require('not distributable' in build['mapMetadataIdentity'], 'Developer artifact identity')
    require({row['file']: row['after'] for row in build['changedWurstInputs']} == PRODUCTION and
            len(build['changedWurstInputs']) == 3, 'Only three production files changed')
    before = read('compiled/inputs-before.json')
    require(before == read('compiled/inputs-after.json'), 'Compile inputs drifted')
    require({k: v for k, v in before.items() if k.startswith('wurst/')} == build['wurstInputs'],
            'Compiled Wurst snapshot binding')
    for name, digest in PRODUCTION.items():
        require(before['wurst/' + name] == digest, 'Compiled production source ' + name)
    require([stage['stage'] for stage in build['stages']] == ['typecheck', 'build'], 'Build stages')
    for stage in build['stages']:
        require(stage['exitCode'] == 0 and stage['inputsUnchanged'] is True and
                stage['compiler']['sha256'] == COMPILER, 'Compiler stage failed or drifted')
        bound(stage['log'], 'compiled/' + stage['stage'] + '.log')

    frozen = read('compiled/frozen-startup.json')
    baseline = read('observer/baseline-frozen-startup.json')
    for report, lua in [(baseline, OLD_LUA), (frozen, NEW_LUA)]:
        require(report['status'] == 'completed_under_stubs' and report['completed'] is True and
                report['campaignRegistered'] is True and report['campaignStarted'] is True,
                'Frozen startup result')
        require(report['compiledLuaSha256'] == lua and report['runtimeVersion'] == 'Lua 5.3' and
                report['evidenceLevel'] == 'supplemental_lua53_explicit_stub_probe',
                'Frozen startup scope/input')
        require(report['harnessSha256'] == sha(decoded['common/probe-lua54-initialization.py']) and
                report['lateNativeStubsSha256'] == sha(decoded['common/late-startup-stubs.lua']),
                'Frozen harness/native model drift')
        require(report['instructions'] <= report['instructionBudget'] == 2_000_000_000,
                'Frozen startup budget')
        require(report['runtimeCounts']['markets'] == 8422 and report['runtimeCounts']['stores'] == 829,
                'Frozen catalogue size')
    require(frozen['nativeStatus'] == 'not_run', 'New frozen native status')
    require(frozen['runnerSha256'] == sha(decoded['compiled/run-frozen-startup.py']), 'Frozen runner')
    bound(frozen['boundBuildReceipt'], 'compiled/build-result.json')

    observer = read('compiled/observer/startup-and-first-callbacks.json')
    old_observer = read('observer/baseline-extended/startup-and-first-callbacks.json')
    require(observer['status'] == 'completed_under_explicit_stubs' and
            observer['nativeStatus'] == 'not_run' and observer['runtimeVersion'] == 'Lua 5.3',
            'New observer scope/status')
    for key, target in [('runner', 'compiled/observer/observe-startup.py'),
                        ('observer', 'compiled/observer/observe-startup.lua'),
                        ('harness', 'common/probe-lua54-initialization.py'),
                        ('nativeStubs', 'common/late-startup-stubs.lua'),
                        ('buildReceipt', 'compiled/build-result.json')]:
        bound(observer['inputs'][key], target)
    require(observer['inputs']['compiledLua']['sha256'] == NEW_LUA and
            observer['inputs']['library']['sha256'] == LIBRARY, 'Observer script/runtime')
    require(decoded['compiled/observer/observe-startup.lua'] ==
            decoded['observer/baseline-extended/observe-startup.lua'], 'Same observer Lua required')
    execution = observer['execution']
    require(execution['startupCompleted'] is True and execution['startup']['started'] is True and
            execution['startup']['registered'] is True and not execution['callbackErrors'],
            'Observer startup/callback result')
    require(execution['callbackPhase']['completed'] is True and
            execution['callbackPhase']['callbackCount'] == 37 and
            execution['callbackPhase']['throughSeconds'] == 1.001 and
            execution['callbackPhase']['instructions'] <= execution['callbackPhase']['budget'],
            'Observer callback phase')
    for old, new in zip(old_observer['cachePayloads'], observer['cachePayloads'], strict=True):
        for key in ['bytes', 'sha256', 'key', 'mission']:
            require(old[key] == new[key], 'Modeled save payload differs: ' + key)
    require(len(observer['cachePayloads']) == 4, 'Modeled cache write count')
    require(execution['startup']['nativeCalls'] == frozen['nativeCalls'], 'Observer native-count parity')

    parity = read('compiled/parity/compiled-parity.json')
    require(parity['status'] == 'pass_under_explicit_models' and parity['nativeStatus'] == 'not_run' and
            parity['productionFunctionOverrides'] is False, 'Compiled parity scope/status')
    for key, target in [('runner', 'compiled/verify-compiled-parity.py'),
                        ('harness', 'common/probe-lua54-initialization.py'),
                        ('buildReceipt', 'compiled/build-result.json')]:
        bound(parity['inputs'][key], target)
    bound(parity['compiledLoweringExcerpt'], 'compiled/parity/compiled-checksum-and-table-helpers.lua')
    require(parity['inputs']['oldLua']['sha256'] == OLD_LUA and
            parity['inputs']['newLua']['sha256'] == NEW_LUA and
            parity['inputs']['library']['sha256'] == LIBRARY, 'Parity compiled/runtime identities')
    slices = {'raw_byte_slices', 'invalid_slice_to_replacement_marker'}
    require({row['sliceModel'] for row in parity['editModels']} == slices and
            len(parity['editModels']) == 2, 'Edit slice models')
    for row in parity['editModels']:
        require(row['status'] == 'pass' and row['exactOutputBytesEqual'] is True and row['cases'] == 188 and
                row['operations'] == row['cachedIndexesChecked'] == 1144, 'Edit differential cases')
    hashes = {'all_zero', 'all_minimum_signed_int', 'casefold_many_collisions',
              'stable_casefold_polynomial32'}
    require({(row['sliceModel'], row['hashModel']) for row in parity['checksumModels']} ==
            {(s, h) for s in slices for h in hashes} and len(parity['checksumModels']) == 8,
            'Checksum oracle matrix')
    for row in parity['checksumModels']:
        require(row['status'] == 'pass' and row['exactChecksumsEqual'] is True and
                row['newHashCalls'] == row['uniqueReturnedSlices'] and
                row['oldHashCalls'] == row['bytePositions'] and row['nativeHashtableCalls'] == 0,
                'Checksum differential result')
    require(sum(row['includesFullCapturedBody'] for row in parity['checksumModels']) == 1 and
            parity['fullBody']['bytes'] == 1_067_473, 'Full captured checksum body coverage')

    comparison = read('compiled/comparison.json')
    require(comparison['status'] == 'pass_scoped_source_and_explicit_model_checks' and
            comparison['nativeStatus'] == 'not_run' and comparison['nativeHangResolution'] == 'not_established' and
            comparison['playerArtifactPublished'] is False and
            comparison['distributionStatus'] == 'source_work_only_no_new_campaign', 'Comparison scope')
    require(comparison['sourceIdentityAtCompile'] == build['sourceIdentityAtAssembly'] and
            comparison['actualCompiledLua']['sha256'] == NEW_LUA, 'Comparison input binding')
    available = {(sha(data), len(data)) for data in decoded.values()}
    for group in ['evidence', 'reproductionScripts']:
        for name, item in comparison[group].items():
            require((item['sha256'], item['bytes']) in available, 'Unretained comparison input: ' + name)
    require(comparison['startup']['newInstructionSamples'] == frozen['instructions'] and
            comparison['startup']['oldInstructionSamples'] == baseline['instructions'],
            'Instruction comparison inputs')
    for name, row in comparison['startup']['nativeCalls'].items():
        require(row['before'] == baseline['nativeCalls'][name] and row['after'] == frozen['nativeCalls'][name] and
                row['difference'] == row['after'] - row['before'], 'Native-call comparison: ' + name)
    require(comparison['compiledParity']['checksumModels'] == parity['checksumModels'] and
            comparison['compiledParity']['editModels'] == parity['editModels'] and
            comparison['compiledParity']['productionFunctionOverrides'] is False, 'Parity summary')
    require(comparison['cachePayloadBytesTotal'] == 3_202_546 and
            all(row['exactPreviousBytesEqual'] is True for row in comparison['cachePayloads']),
            'Payload summary')


if __name__ == '__main__':
    try:
        main()
    except (KeyError, ValueError, OSError, TypeError) as error:
        print(json.dumps({'status': 'fail_retained_evidence_verification', 'error': str(error)},
                         sort_keys=True), file=sys.stderr)
        sys.exit(1)
