#!/usr/bin/env python3
"""Read-only integrity check for the retained evidence; runs no map or VM."""
from pathlib import Path
import gzip
import hashlib
import json

ROOT = Path(__file__).resolve().parent


def sha(payload):
    return hashlib.sha256(payload).hexdigest()


def main():
    manifest = json.loads((ROOT / 'manifest.json').read_text())
    decoded = {}
    listed = set()
    for entry in manifest['files']:
        path = ROOT / entry['file']
        assert path.resolve().parent == ROOT, 'Unexpected evidence path'
        assert path.name not in listed, 'Repeated manifest entry'
        listed.add(path.name)
        payload = path.read_bytes()
        assert len(payload) == entry['packagedBytes'], path.name
        assert sha(payload) == entry['packagedSha256'], path.name
        if entry['encoding'] == 'gzip_mtime_0':
            assert payload[:4] == b'\x1f\x8b\x08\x00', 'Unexpected gzip header'
            assert payload[4:8] == b'\x00\x00\x00\x00', 'Nonzero gzip timestamp'
            payload = gzip.decompress(payload)
        else:
            assert entry['encoding'] == 'identity'
        assert len(payload) == entry['originalBytes'], path.name
        assert sha(payload) == entry['originalSha256'], path.name
        decoded[path.name] = payload
    actual = {path.name for path in ROOT.iterdir() if path.is_file() and path.name != 'manifest.json'}
    assert actual == listed, 'Manifest does not cover the exact retained file set'
    assert not any(path.is_dir() for path in ROOT.iterdir()), 'Unexpected subdirectory'

    comparison = json.loads(decoded['startup-exact-source-comparison.json'])
    assert comparison['nativeStatus'] == 'not_run'
    for item in comparison['fullReports'].values():
        name = Path(item['path']).name + '.gz'
        assert sha(decoded[name]) == item['sha256'], 'Original raw report digest differs'
    assert sha(decoded['probe-lua54-initialization.py']) == comparison['frozenHarnessSha256']
    assert sha(decoded['late-startup-stubs.lua']) == comparison['frozenNativeStubsSha256']

    positive = json.loads(decoded['full-scale-lua53.json'])
    assert positive['status'] == 'pass_full_scale_roundtrip_under_explicit_stubs'
    assert positive['nativeStatus'] == 'not_run'
    assert positive['instructionBudgetPerPhase'] == 2_000_000_000
    for key, filename in [('roundtripHarness', 'verify-trade-full-scale.py'),
                          ('roundtripCase', 'full-scale-roundtrip.lua'),
                          ('frozenHarness', 'probe-lua54-initialization.py'),
                          ('frozenNativeStubs', 'late-startup-stubs.lua'),
                          ('buildReceipt', 'build-result.json')]:
        assert positive['inputs'][key]['sha256'] == sha(decoded[filename]), filename
    for phase in positive['execution']['phases'].values():
        assert phase['completed'] and phase['instructions'] <= 2_000_000_000
        assert not phase.get('budgetExhausted')
    assert positive['execution']['startup']['startupReturn'] is True
    assert positive['execution']['startup']['finishStartupReturn'] is True
    scale = positive['execution']['roundtrip']
    assert scale['marketCount'] == scale['mutatedMarkets'] == 8422
    assert scale['storeCount'] == scale['populatedStores'] == scale['mutatedStores'] == 829
    assert scale['populatedLots'] == scale['clearedLots'] == scale['restoredLots'] == 829
    assert scale['reconstructReturned'] and scale['exactCaptureEquality']
    assert positive['captures']['saved'] == positive['captures']['restored']
    assert positive['captures']['saved'] != positive['captures']['mutated']

    negative = json.loads(decoded['full-scale-lua53-negative-control.json'])
    control = json.loads(decoded['negative-control-result.json'])
    assert negative['status'] == 'failed' and negative['nativeStatus'] == 'not_run'
    assert negative['instructionBudgetPerPhase'] == 10_000
    assert negative['execution']['phases']['startup']['budgetExhausted'] is True
    assert '__SCALE_INSTRUCTION_BUDGET_EXHAUSTED:startup' in negative['error']
    assert control['actualProcessExitCode'] == control['expectedProcessExitCode'] == 1
    assert control['rawReportSha256'] == sha(decoded['full-scale-lua53-negative-control.json'])
    print(json.dumps({'status': 'pass_retained_evidence_integrity',
                      'filesVerified': len(listed), 'nativeStatus': 'not_run'}, sort_keys=True))


if __name__ == '__main__':
    main()
