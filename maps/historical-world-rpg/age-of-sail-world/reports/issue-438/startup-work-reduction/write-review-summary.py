#!/usr/bin/env python3
"""Summarize only completed bound evidence for the two startup corrections."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parent


def read(relative):
    return json.loads((ROOT / relative).read_text())


def identity(relative):
    value = (ROOT / relative).read_bytes()
    return {'file': relative, 'bytes': len(value), 'sha256': hashlib.sha256(value).hexdigest()}


def main():
    full = read('full-wurst-tests/run-receipt.json')
    capture = read('compiled-comparison-attempt2/comparison.json')
    combined = read('compiled-combined-comparison/comparison.json')
    build = read('europe-combined-retry/build-result.json')
    refresh = read('source-checks/receipt.json')
    assert full['status'] == build['status'] == 'pass'
    assert full['succeeded'] == full['discovered'] == 671
    assert combined['status'] == capture['status'] == 'pass_under_explicit_models'
    assert full['sourceIdentity'] == build['sourceIdentityAtAssembly'] == refresh['sourceIdentity']
    assert refresh['status'] == 'pass_freshness_with_acceptance_still_blocked'
    before = combined['nativeCalls']['SubString']['before']
    after = combined['nativeCalls']['SubString']['after']
    saved = combined['cachePayloadBytesTotal']
    summary = {
        'format': 'startup_work_reduction_summary_v1',
        'sourceIdentity': full['sourceIdentity'],
        'status': 'verified_source_work_reduction_native_unresolved',
        'nativeStatus': 'not_run', 'nativeHangResolution': 'not_established',
        'playerArtifactProduced': False,
        'fullWurstTests': 671, 'focusedCaptureTests': 21, 'focusedMilitaryTests': 28,
        'substringCalls': {'baseline': before, 'captureOnly': capture['nativeCalls']['SubString']['after'],
                           'combined': after, 'removed': before - after,
                           'percentRemoved': round(100 * (before - after) / before, 4)},
        'instructionSamples': {'baseline': combined['instructionSamples']['before'],
                               'captureOnly': capture['instructionSamples']['after'],
                               'combined': combined['instructionSamples']['after']},
        'savedPayloads': {'count': 4, 'bytes': saved, 'byteIdenticalInComparison': True},
        'compiledLua': {'sha256': build['compiledScriptSha256'], 'bytes': build['compiledScriptBytes']},
        'retainedBlockers': {name: refresh[name] for name in
                             ['runtimeFailures', 'releaseBlockers', 'traceabilityBlockers']},
        'inputs': {name: identity(path) for name, path in {
            'fullSuite': 'full-wurst-tests/run-receipt.json',
            'captureComparison': 'compiled-comparison-attempt2/comparison.json',
            'combinedComparison': 'compiled-combined-comparison/comparison.json',
            'combinedBuild': 'europe-combined-retry/build-result.json',
            'sourceReports': 'source-checks/receipt.json',
        }.items()},
    }
    (ROOT / 'verification-summary.json').write_text(json.dumps(summary, indent=2, sort_keys=True) + '\n')
    rows = []
    for name in ['SubString', 'StringLength', 'StringHash', 'StoreString', 'SaveGameCache']:
        rows.append(f"| `{name}` | {combined['nativeCalls'][name]['before']:,} | {capture['nativeCalls'][name]['after']:,} | {combined['nativeCalls'][name]['after']:,} |")
    rows.append(f"| Lua instruction samples | {combined['instructionSamples']['before']:,} | {capture['instructionSamples']['after']:,} | {combined['instructionSamples']['after']:,} |")
    table = '\n'.join(rows)
    observer_note = ('The final build dead-strips the now-unused boolean validation entry. The supplementary observer removes exactly that obsolete measurement wrapper and uses the identical resulting observer for both baseline and combined inputs. The original capture-only observer, frozen startup probe, native stubs and instruction budgets remain unchanged.'
                     if combined['observerVariant']['selected']['sha256'] != combined['observerVariant']['original']['sha256'] else
                     'The combined comparison uses the original observer unchanged on both inputs. The frozen startup probe, native stubs and instruction budgets are also unchanged.')
    text = f'''# Issue #438 / PR #536: reduce repeated startup work

**Native Continue acceptance remains unresolved.** The last player observation, on 2026-10-20 at 16:52:49 UTC, was an unresponsive Warcraft window after Austria → Victory → Continue. No destination terrain or responsive player-controlled unit was observed. Duration, eventual recovery, the installed-file hash and destination Lua initialization remain unknown. The original observation is retained in [previous-native-observation.json](previous-native-observation.json).

This change removes two demonstrated sources of unnecessary startup work. It does not establish the cause or resolution of the native stall. PR #536 remains open and draft; issue #438 remains open. No new complete player campaign is produced or offered by this work.

## Source correction

`PlayableCampaignState.captureDomains` now reads metadata from its immutable input before editing the expanded output. The former alternation between those strings evicted the separator index and rescanned the large captured domains. Callback order and serialized edit order remain unchanged. The capture-only comparison isolates this correction before adding the second change.

`MilitarySettlementRuntime.parseValidatedSnapshot` returns an owned detached copy after the existing parser and all six campaign-day checks succeed. Campaign validation reuses that copy for the country checks instead of parsing the same military state a second time. One cleanup point disposes it after success or rejection, before the independent economy validation and before publishing staged authority. The existing boolean validation API remains available and disposes successful results. Diagnostic order, legacy parsing, and current stateless definition-provider behavior are preserved. Separate remote-command and founded-pirate reconciliation parses remain unchanged.

Campaign schema **10**, trade snapshot **5**, military snapshot **15**, the native substring/checksum semantics and the Continue handoff calls are unchanged. The four new regressions cover serialized field order and Unicode, all six date bounds, detached ownership, saved-versus-live conflict authority, cleanup, and diagnostic precedence. [Source review and failed-attempt provenance](source-review.json) records the exact scope.

## Measured compiled startup

All columns execute the actual archived Europe Lua with the same pinned stock Lua 5.3 runtime and explicit native model. These are startup work counts, not Warcraft timings.

| Measurement | Published baseline `264b34c` | Capture correction only | Both corrections |
| --- | ---: | ---: | ---: |
{table}

The combined source removes **{before - after:,} substring calls ({100 * (before - after) / before:.1f}%)** from the baseline probe. Military snapshot parsing falls from two calls to one in this startup path.

All **four saved payloads are byte-identical**, totaling **{saved:,} bytes**. The retained original compressed fixture payloads allow the verifier to compare the actual decompressed bytes. The world retains 8,422 markets, 829 stores, 827 settlements and 1,553 forces. Both observers complete all 37 initial callbacks through 1.001 simulated seconds with identical callback order and native observations. The final modeled request remains the consumed Austria/Vienna handoff.

{observer_note}

The three large checkpoint strings each contain 58 non-ASCII bytes in military data. A whole-save ASCII assumption is false. Native argument byte-volume measurements count traffic through startup and the modeled callbacks; they do not establish native copies or loading time. Disk behavior, engine scheduling, rendering, assets, later autosaves and player movement are outside this model.

## Completed verification

- **671/671** tests passed in the complete unchanged Wurst interpreter gate, in seven batches. Source bytes, compiler inputs, dependency bytes and toolchain identities agree before and after. No test annotations, deadlines or release gates were weakened.
- Focused capture validation passed **21/21** tests. Focused military/campaign validation passed **28/28**, including three new ownership/date/diagnostic regressions.
- The baseline, capture-only and combined Europe maps passed type checking, compilation, physical-map/archive checks and independent MPQ member comparison. The compiler output equals the Lua extracted from each archive. Exactly one and then two production files differ from baseline; scenario, generated-map and dependency inputs are identical. These internal maps retain baseline metadata and are not distributable player builds.
- The combined archived Lua is **{build['compiledScriptBytes']:,} bytes**, SHA-256 `{build['compiledScriptSha256']}`. The pinned compiler is `1f3ae40b1018b8757867515596adfa69113ca85f390c1b353cc8b69cf8944145`; stdlib revision is `cce79096e71dcb066cf94785bc5cb48ef66c26db`. Verified extracted tools ran on the workspace host; the full OCI image was not executed.
- The checked-in report-freshness regression passed. Regenerated source reports retain **30 runtime failures, 238 release blockers and 7,004 traceability blockers**. Expected nonzero runtime/release audit exits remain recorded.

The tested source identity is `{full['sourceIdentity']['sourceTreeSha256']}`, recorded as frozen working-tree content based on `264b34c9a0762bdadda377fb10cb44a63af33052`. It is not labeled as a clean test of the baseline bytes. [verification-summary.json](verification-summary.json) binds the terminal receipts used here.

## Preserved unsuccessful attempts

The first two capture-focused attempts and the initial baseline compile did not execute tests because extraction omitted the JDK helper's executable permission. Restoring the exact pinned image mode resolved that setup fault; binary bytes did not change. The initial startup probe also stopped before map initialization because its frozen pathing-file path was missing; the exact verified WPM was restored without changing the stubs.

Military attempt 1 failed compilation on a local-name collision. Attempts 2 and 3 each passed 27/28 tests while exposing a mistake in the new rejection fixture: editing the first duplicate field did not change the last authoritative field. The final fixture explicitly appends and checks the invalid last record; attempt 4 passed 28/28. Failed logs remain separately retained.

The first combined map typechecked but its compiler child exited 137 while the full regression JVM was also active. The 8 GiB workspace reached its memory cap and recorded an OOM kill. Attribution of that compiler termination to shared memory pressure is an inference; no per-PID kernel record was captured. The identical frozen build passed when retried alone after the full suite completed. The failed build and resource observation remain intact.

## Inspect or reproduce the evidence

From this directory, run:

```sh
python3 verify-evidence.py
```

The standard-library-only verifier checks the exact manifest file set, hashes, original transcripts with the unchanged Wurst gate, complete discovery and input boundaries, build bindings, modeled counts and callbacks, and actual saved bytes. It executes no compiler, Lua or Warcraft. Raw map archives and compiled Lua binaries are represented by their bound build/equality receipts; this verifier does not re-extract omitted binaries.

The retained runners use their original workspace paths. Re-execution requires reconstructing the pinned toolchain and source assemblies at matching paths, or explicitly adapting those paths while retaining the compiler, dependency, input and harness hashes. The manifest and receipts distinguish those reproduction inputs from observed outputs.

## Remaining discriminator

The missing external observation is execution of a complete campaign built from the corrected source in the real Warcraft client. A successful Continue must show destination terrain and a player-controlled unit responding to movement. Without that observation, the cause and resolution of the native stall remain unconfirmed. No unchanged or incremental player retest is requested by this source-only change.
'''
    (ROOT / 'README.md').write_text(text)
    print(json.dumps({'status': summary['status'], 'removedSubstringCalls': before - after,
                      'fullWurstTests': 671, 'nativeStatus': 'not_run'}, sort_keys=True))


if __name__ == '__main__':
    main()
