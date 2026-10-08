#!/usr/bin/env python3
"""Recheck PR #423's artifact gate, scoped receipts and packaged recovery grids."""
import gzip
import hashlib
import json
from pathlib import Path
import sys
import tempfile

PROJECT = Path(__file__).resolve().parents[2]
DESTINATION = Path(__file__).resolve().parent
sys.path[:0] = [str(PROJECT / 'tooling'), str(PROJECT.parent / '_shared/tooling')]
from boundary_arrival import verify_packaged_navigation
from integration_evidence import source_identity, verify_execution_coverage
from package_release_candidate import verify_campaign_runtime
from package_wurst_campaign import load_campaign_config
from requirement_traceability_audit import build_report
from warcraft_campaign import MpqReader
from wurst_execution import source_revision


def save(name, value):
    data = (json.dumps(value, indent=2, sort_keys=True) + '\n').encode()
    (DESTINATION / name).write_bytes(gzip.compress(data, mtime=0))


def main():
    revision = source_revision(PROJECT)
    identity = source_identity(PROJECT, revision)
    artifact = PROJECT / '_build/release/AgeOfSailWorldCampaign.w3n'
    evidence = json.loads((PROJECT / '_build/wurst-tests/results.json').read_text())
    transcript = (PROJECT / '_build/wurst-tests/execution.log').read_bytes()
    verify_execution_coverage(evidence, transcript, PROJECT, revision)
    config = load_campaign_config(PROJECT / 'physical-maps.json')
    # Run the exact RC gate missed by the earlier diagnostic packaging driver.
    compiled = verify_campaign_runtime(artifact, config, revision=revision,
                                       source_tree_sha256=identity['sourceTreeSha256'])
    assert compiled['status'] == 'pass', compiled
    save('ci-repair-runtime-artifact.json.gz', compiled)

    report = build_report(artifact, evidence, transcript, revision)
    scope = {f'REQ-{number:04}.01' for number in range(191, 203)}
    rows = [row for row in report['requirements'] if row['id'] in scope]
    assert not report['executionErrors'], report['executionErrors']
    assert {row['id'] for row in rows} == scope
    assert all(row['status'] == 'pass' for row in rows), rows
    receipts = [json.loads(line.removeprefix('TRACEABILITY ')) for line in transcript.decode().splitlines()
                if line.startswith('TRACEABILITY ')]
    receipts = [row for row in receipts if row['requirement'] in scope]
    assert len(receipts) == 4 * len(scope)
    assert {(row['requirement'], row['case']) for row in receipts} == {
        (requirement, case) for requirement in scope for case in ('success', 'failure', 'stale', 'replay')}
    save('ci-repair-scoped-traceability.json.gz', {
        'sourceIdentity': identity, 'requirements': rows, 'productionReceipts': receipts,
        'blockers': [row for row in report['blockers'] if row['id'] in scope],
        'outOfScopeBlockerCount': sum(row['id'] not in scope for row in report['blockers']),
    })

    campaign = MpqReader(artifact)
    navigation = []
    with tempfile.TemporaryDirectory(dir=PROJECT / '_build') as temporary:
        path = Path(temporary) / 'map.w3x'
        for physical in config.maps:
            if physical.bootstrap:
                continue
            path.write_bytes(campaign.read(physical.package_path))
            reader = MpqReader(path)
            runtime = json.loads(reader.read('runtime/scenario-runtime.json'))
            grids = runtime['recoveryNavigation'][physical.id]
            assert len(grids) == 4
            verify_packaged_navigation(runtime['boundaryNavigation'], physical.id,
                                      reader.read('war3map.w3i'), reader.read('war3map.wpm'),
                                      runtime['partyNavigation'][physical.id], grids)
            navigation.append({
                'mapId': physical.id, 'mapSha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                'movementClasses': len(grids),
                'transforms': [{key: grid[key] for key in ('minX', 'minY', 'width', 'height')} for grid in grids],
                'anchorCounts': [len(grid['anchors']) for grid in grids],
            })
    assert len(navigation) == sum(not physical.bootstrap for physical in config.maps)
    assert source_identity(PROJECT, revision) == identity, 'sources changed during verification'
    save('ci-repair-packaged-navigation.json.gz', {
        'sourceIdentity': identity, 'artifactSha256': compiled['artifactSha256'], 'maps': navigation,
    })
    print(f"PASS: {len(compiled['maps'])} maps pass the RC artifact gate; {len(rows)} scoped obligations, "
          f"{len(receipts)} production receipts, and {len(navigation)} maps with four recovery grids verified against WPM.")


if __name__ == '__main__':
    main()
