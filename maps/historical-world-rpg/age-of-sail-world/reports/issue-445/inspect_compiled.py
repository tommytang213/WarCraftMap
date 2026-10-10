#!/usr/bin/env python3
"""Compare actual MPQ Lua quest registrations and graph data to authored content.

Handles the pinned compiler's constructor calls and inlined storage assignments.
This is a static definition inspection, not native Warcraft execution evidence.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

PROJECT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT.parent / '_shared/tooling'))
from warcraft_campaign import MpqReader
from integration_evidence import source_identity

STRING = r'"(?:\\.|[^"\\])*"'


def unpack(value):
    return json.loads(value)


def rows(block, kind, fields):
    constructor = re.compile(r'\b' + kind + '_new_' + kind + r'\(\s*(' + STRING + ')' + ''.join(r',\s*(' + STRING + ')' for _ in fields[1:]))
    calls = [dict(zip(fields, map(unpack, m.groups()))) for m in constructor.finditer(block)]
    if calls:
        return calls
    inline = re.compile(r'\b' + kind + r'_(' + '|'.join(fields) + r')_storage\[([^\]]+)\]\s*=\s*(' + STRING + r')')
    records = []
    current = None
    for match in inline.finditer(block):
        field, owner, value = match.groups()
        if field == fields[0]:
            current = {}
            records.append(current)
        if current is not None:
            current[field] = unpack(value)
    return records


def inspect(archive, world):
    reader = MpqReader(archive)
    lua_bytes = reader.read('war3map.lua')
    lua = lua_bytes.decode()
    runtime = json.loads(reader.read('runtime/scenario-runtime.json'))
    assert runtime['questDefinitions'] == world['quests'], 'archive graph JSON differs from authoritative projection'
    starter = re.compile(r'\bRuntimeQuest_new_RuntimeQuest\(\s*(?P<call>' + STRING + r')|\bRuntimeQuest_id_storage\[[^\]]+\]\s*=\s*(?P<inline>' + STRING + ')')
    authored = {q['id']: q for q in world['quests']}
    starts = [(m, unpack(m['call'] or m['inline'])) for m in starter.finditer(lua)]
    starts = [(m, ident) for m, ident in starts if ident]
    assert sorted(ident for _, ident in starts) == sorted(authored), 'compiled quest identity membership differs'
    result = []
    def tokens(values):
        return ''.join(v + '~' for v in values)
    for n, (start, ident) in enumerate(starts):
        q = authored[ident]
        block = lua[start.start():starts[n+1][0].start() if n+1 < len(starts) else len(lua)]
        graphs = rows(block, 'QuestGraph', ['initialStageId', 'prerequisiteQuestIds'])
        stages = rows(block, 'QuestStage', ['id', 'title', 'objectiveIds', 'nextStageIds'])
        objectives = rows(block, 'QuestObjective', ['id', 'description', 'conditionId', 'entityRefs', 'binding'])
        assert graphs == [{'initialStageId':q['initialStageId'], 'prerequisiteQuestIds':tokens([p['id'] for p in q['prerequisites']])}], (ident, 'initial stage/prerequisites', graphs)
        assert stages == [{**s, 'objectiveIds':tokens(s['objectiveIds']), 'nextStageIds':tokens(s['nextStageIds'])} for s in q['stages']], (ident, 'stages', stages)
        expected = [{**o, 'entityRefs':''.join(f'{r["kind"]}:{r["id"]}~' for r in sorted(o['entityRefs'], key=lambda r:(r['kind'], r['id']))), 'binding':runtime['questConditionBindings'][ident + ':' + o['id']]} for o in q['objectives']]
        assert objectives == expected, (ident, 'objectives', objectives)
        assert 'QuestGraph_QuestGraph_addStage(' in block and 'QuestGraph_QuestGraph_addObjective(' in block, (ident, 'graph not registered')
        assert 'QuestJournalRuntime_QuestJournalRuntime_register(' in block, (ident, 'quest not registered')
        result.append({'id':ident, 'stages':len(stages), 'objectives':len(objectives), 'prerequisites':[p['id'] for p in q['prerequisites']]})
    return {'status':'pass', 'scope':'Static same-source MPQ Lua graph registrations; no native execution claim.',
            'sourceIdentity':json.loads(reader.read('runtime/build-identity.json')),
            'archiveSha256':hashlib.sha256(archive.read_bytes()).hexdigest(),
            'luaSha256':hashlib.sha256(lua_bytes).hexdigest(),
            'worldSha256':runtime['sourceSha256'], 'quests':result,
            'questCount':len(result), 'stageCount':sum(x['stages'] for x in result),
            'objectiveCount':sum(x['objectives'] for x in result),
            'conditionIntegrationBlockerCount':len(runtime['questIntegrationBlockers'])}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    parser.add_argument('--world', type=Path, default=PROJECT/'scenario/world/world.json')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = inspect(args.archive, json.loads(args.world.read_text()))
    identity = result['sourceIdentity']
    assert source_identity(args.world.resolve().parents[2], identity['sourceRevision']) == identity, 'archive source identity differs from current sources'
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(f'Compared {result["questCount"]} quests, {result["stageCount"]} stages and {result["objectiveCount"]} objectives in actual compiled Lua.')
