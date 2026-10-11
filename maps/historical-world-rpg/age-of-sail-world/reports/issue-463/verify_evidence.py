#!/usr/bin/env python3
"""Bind scoped entitlement receipts and compiled definitions to the same source."""
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys

from inspect_compiled import PROJECT, inspect
sys.path.insert(0,str(PROJECT/'tooling'))
from integration_evidence import verify_execution_coverage, source_identity
from wurst_execution import source_revision
import requirement_traceability_audit as trace
from technology_institutions import research_integration_blockers


def verify(artifact, execution_dir):
    revision=source_revision(PROJECT)
    identity=source_identity(PROJECT,revision)
    evidence=json.loads((execution_dir/'results.json').read_text())
    log=(execution_dir/'execution.log').read_bytes()
    coverage=verify_execution_coverage(evidence,log,PROJECT,revision)
    assert any(name.endswith(':generatedMassArmyResearchDeliversAllTypedEntitlementsToItsController') for name in coverage.get('technology_institutions',[]))
    compiled=inspect(artifact)
    assert compiled['sourceIdentity']==identity
    wanted={
        'success':'generatedMassArmyResearchDeliversAllTypedEntitlementsToItsController',
        'failure':'malformedTypedResearchDefinitionsRejectBeforeChargesAndCompletion',
        'stale':'institutionsPreserveSharedContentProvenanceAndAllFiveUnlockKinds',
        'replay':'typedResearchReconstructsSupportedSavesWithoutGrantsOrStaleLayers'}
    text=log.decode(); receipts=[]
    for case,name in wanted.items():
        matches=re.findall(r'(?ms)^Running [^\n]+ - '+re.escape(name)+r'\.\.\s*\n(.*?)(?=^Running |\Z)',text)
        assert len(matches)==1 and '\tOK!' in matches[0],name
        body=matches[0].split('\tOK!')[0]
        rows=[json.loads(s) for s in re.findall(r'^TRACEABILITY (\{[^\n]+\})$',body,re.M)]
        matching=[r for r in rows if r.get('entryPoint')=='live-typed-research-entitlements']
        assert len(matching)==1 and matching[0]['case']==case and matching[0]['requirement']=='ROAD-0045.01'
        assert matching[0]['scope']=='definitions_and_entitlement_delivery'
        receipts+=matching
    selected=[t for t in evidence['tests'] if t['id'].startswith('wurst/ResearchRuntimeTests.wurst:')
              or t['id'].endswith(':rejectedLoadsRestoreTypedResearchLayersForEveryController')]
    assert all(t['status']=='pass' for t in selected)
    assert any(t['id'].endswith(':productionUnboundResearchNeverChangesWarcraftFoodCapacity') for t in selected)
    current=trace.build_report()
    tracked=json.loads(trace.REPORT.with_suffix('.json').read_text())
    assert current==tracked,'tracked traceability report is stale'
    baseline=json.loads(subprocess.check_output(['git','show','HEAD:maps/historical-world-rpg/age-of-sail-world/reports/traceability/requirements.json'],cwd=PROJECT))
    prior={r['id']:r for r in baseline['requirements']}
    for row in current['requirements']:
        if row['id']!='ROAD-0045.01':
            assert row['blockerClasses']==prior[row['id']]['blockerClasses'],row['id']
    assert current['dependencies']==baseline['dependencies'],'unrelated dependency status changed'
    road=next(r for r in current['requirements'] if r['id']=='ROAD-0045.01')
    assert road['status']=='fail' and not current['candidateReady']
    blockers=research_integration_blockers(json.loads((PROJECT/'scenario/world/world.json').read_text()))
    return dict(status='pass',sourceIdentity=identity,scope='ROAD-0045.01 definitions and entitlement delivery only',
                compiledDefinitions=compiled,executedTests=selected,receipts=receipts,
                researchProductionTests=coverage.get('technology_institutions',[]),
                fullPinnedSuite=dict(passed=evidence['succeeded'],discovered=evidence['discovered'],compiler=evidence['compiler']),
                remainingConsumers=blockers,broaderRoadmapStatus=road['status'],unrelatedBlockersUnchanged=True,
                nativeClient='blocked_pending_real_forsaken_kingdom_launch_smoke',releaseReady=False)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--artifact',type=Path,required=True)
    parser.add_argument('--execution-dir',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    args.output.write_text(json.dumps(verify(args.artifact,args.execution_dir),indent=2,sort_keys=True)+'\n')
    print('PASS: same-source research definitions, entitlement receipts, binding blockers and compiled registrations')
