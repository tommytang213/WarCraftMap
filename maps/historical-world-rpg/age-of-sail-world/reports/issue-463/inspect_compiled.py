#!/usr/bin/env python3
"""Compare executable research registrations with every authored typed unlock."""
import argparse
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re
import sys

PROJECT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(PROJECT.parent/'_shared/tooling'),str(PROJECT.parent/'_shared/engine')]
from integration_evidence import source_identity
from package_wurst_map import research_time_cost
from requirement_traceability import lua_code_mask
from technology_institutions import research_unlock_definitions, research_integration_blockers
from warcraft_campaign import MpqReader


def compiled_research(script):
    body=re.search(r'(?ms)^function configureGeneratedRpg\([^\n]+\).*?(?=^function |\Z)',script)
    assert body, 'compiled scenario configuration is missing'
    objects,found={},{}
    variable=r'(?:__wurst_locals\[\d+\]|\w+)'
    literal=r'"(?:[^"\\]|\\.)*"'
    for raw,masked in zip(body[0].splitlines(),lua_code_mask(body[0]).splitlines()):
        raw,masked=raw.strip(),masked.strip()
        new=re.fullmatch(rf'({variable})\s*=\s*RuntimeTechnology:create\d+\(\)',masked)
        ctor=re.fullmatch(rf'({variable})\s*=\s*RuntimeTechnology_new_RuntimeTechnology\d*\(({literal}), {literal}, (-?\d+), ({literal}), ({literal}), ({literal})(?:, {literal})?\)',raw)
        if new or ctor:
            match=new or ctor
            value={'prerequisites':[],'unlocks':[]}
            if ctor:
                value.update(id=json.loads(ctor[2]),historicalYear=int(ctor[3]),baseCost=json.loads(ctor[4]),
                             aheadOfTimeCostMultiplier=json.loads(ctor[5]),additionalMultiplierPerYearAhead=json.loads(ctor[6]))
            objects[match[1]]=value
            continue
        alias=re.fullmatch(rf'({variable})\s*=\s*({variable})',masked)
        if alias and alias[2] in objects: objects[alias[1]]=objects[alias[2]]
        field=re.fullmatch(rf'RuntimeTechnology_(id|kind|historicalYear|baseCost|aheadOfTimeCostMultiplier|additionalMultiplierPerYearAhead|expectedUnlockCount)_storage\[({variable})\]\s*=\s*({literal}|-?\d+)',raw)
        if field and field[2] in objects: objects[field[2]][field[1]]=json.loads(field[3])
        prerequisite=re.fullmatch(rf'RuntimeTechnology_RuntimeTechnology_addPrerequisite\(({variable}), ({literal})(?:, {literal})?\)',raw)
        if prerequisite: objects[prerequisite[1]]['prerequisites'].append(json.loads(prerequisite[2]))
        unlock=re.fullmatch(rf'RuntimeTechnology_RuntimeTechnology_addUnlock\(({variable}), ({literal}), ({literal}), ({literal})(?:, {literal})?\)',raw)
        if unlock: objects[unlock[1]]['unlocks'].append(tuple(json.loads(unlock[i]) for i in (2,3,4)))
        register=re.fullmatch(rf'TechnologyRuntime_TechnologyRuntime_register\([^,]+, ({variable})(?:, {literal})?\)',raw)
        if register:
            value=objects[register[1]]
            assert value['id'] not in found, 'duplicate compiled research registration'
            found[value['id']]=value
    return found


def expected_research(world):
    result={}
    for kind,rows in (('technology',world['technologies']),('institution',world['institutions'])):
        for row in rows:
            year,base,ahead,annual=research_time_cost(row['timeCost'],row['id'])
            result[row['id']]=dict(id=row['id'],kind=kind,historicalYear=year,baseCost=base,
                aheadOfTimeCostMultiplier=ahead,additionalMultiplierPerYearAhead=annual,
                prerequisites=row['prerequisiteIds'],expectedUnlockCount=len(row['unlocks']),
                unlocks=[(row['id'],u['kind'],u['contentId']) for u in row['unlocks']])
    return result


def inspect(archive):
    mpq=MpqReader(archive)
    script_bytes=mpq.read('war3map.lua'); script=script_bytes.decode()
    identity=json.loads(mpq.read('runtime/build-identity.json'))
    assert identity==source_identity(PROJECT,identity['sourceRevision']), 'source mismatch'
    runtime=json.loads(mpq.read('runtime/scenario-runtime.json'))
    world=json.loads((PROJECT/'scenario/world/world.json').read_text(),parse_float=Decimal)
    expected=expected_research(world); actual=compiled_research(script)
    assert actual==expected, {n:(expected.get(n),actual.get(n)) for n in expected.keys()|actual.keys() if expected.get(n)!=actual.get(n)}
    assert list(actual)==list(expected), 'compiled research registration order changed'
    assert runtime['researchUnlockDefinitions']==research_unlock_definitions(world)
    assert runtime['researchIntegrationBlockers']==research_integration_blockers(world)
    dropped=re.sub(r'^[ \t]*RuntimeTechnology_RuntimeTechnology_addUnlock\([^\n]+\)[ \t]*$', '',script,count=1,flags=re.M)
    lost_kind=re.sub(r'(RuntimeTechnology_RuntimeTechnology_addUnlock\([^\n]+, )"policy", "mass_conscription"',r'\1"modifier", "mass_conscription"',script,count=1)
    assert compiled_research(dropped)!=expected, 'dropped compiled unlock was not detected'
    assert compiled_research(lost_kind)!=expected, 'lost compiled kind was not detected'
    for command in ('research','technology'):
        assert re.search(r'\bCommandRegistry_CommandRegistry_register\([^,\n]+,\s*"'+command+'",',script),command
    assert re.search(r'\bCommandRegistry_CommandRegistry_register\([^,\n]+,\s*"research",\s*"unlock,institution",',script)
    assert 'UnboundResearchEffects_UnboundResearchEffects_replaceResearchEntitlements(' in script
    assert 'Unbound research unlocks have no gameplay effect yet.' in script
    assert 'PLAYER_STATE_RESOURCE_FOOD_CAP' not in script, 'food-cap fallback survived compilation'
    return dict(status='pass',sourceIdentity=identity,archiveSha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
        luaSha256=hashlib.sha256(script_bytes).hexdigest(),nodes=len(actual),
        prerequisiteEdges=sum(len(r['prerequisites']) for r in actual.values()),
        unlocks=sum(len(r['unlocks']) for r in actual.values()),multiUnlockNodes=sum(len(r['unlocks'])>1 for r in actual.values()),
        negativeControls=['dropped_compiled_unlock','lost_compiled_kind'],
        unboundConsumers=len(runtime['researchIntegrationBlockers']),foodCapacityFallback=False,
        gameplayConsumers='blocked_pending_gameplay_consumers',nativeClient='not_run',releaseReady=False)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    args.output.write_text(json.dumps(inspect(args.archive),indent=2,sort_keys=True)+'\n')
