"""Bounded live reward batches for quests that author complete_research.

Other quests deliberately keep their existing generic path in this change. The
catalog reports that gap rather than representing their outcomes as delivered.
"""
from copy import deepcopy
from quest_codegen import ID, ids

RESEARCH = 'quest_technology_complete_research'


def configuration(world):
    known = {(kind, row['id']) for kind, key in [('technology', 'technologies'), ('institution', 'institutions')]
             for row in world.get(key, [])}
    batches, blockers, legacy = {}, [], []
    for q in world.get('quests', []):
        outcomes = q.get('outcomes', [])
        if not any(o.get('outcomeId') == RESEARCH for o in outcomes):
            if outcomes:
                legacy.append(q['id'])
            continue
        if not 0 < len(outcomes) <= 32:
            raise ValueError('authored reward batch exceeds bounded capacity')
        ids([o['id'] for o in outcomes])
        stages = {s['id']: s for s in q['stages']}
        rows = []
        for o in outcomes:
            required = o.get('requiresReachedStageIds', [])
            ids(required)
            if any(s not in stages for s in required):
                raise ValueError('authored reward names an unknown reached stage')
            def possible(sid, path):
                if sid in path or sid not in stages:
                    return False
                reached = path | {sid}
                next_ids = stages[sid]['nextStageIds']
                return (set(required) <= reached if not next_ids else
                        any(possible(n, reached) for n in next_ids))
            if not possible(q['initialStageId'], set()):
                raise ValueError('authored reward reached stages have no terminal route')
            supported = o.get('kind') == 'scenario_outcome' and o.get('outcomeId') == RESEARCH
            target = ''
            if supported:
                if (set(o) - {'id', 'kind', 'outcomeId', 'entityRefs', 'requiresReachedStageIds'}
                        or len(o.get('entityRefs', [])) != 1
                        or (o['entityRefs'][0]['kind'], o['entityRefs'][0]['id']) not in known):
                    raise ValueError('complete_research reward requires exactly one known research reference and no extra semantics')
                target = o['entityRefs'][0]['id']
            operation = o.get('outcomeId', o.get('kind', 'unsupported'))
            if not isinstance(operation, str) or not ID.fullmatch(operation):
                raise ValueError('authored reward operation is invalid')
            rows.append(dict(id=o['id'], operation=operation, targetId=target,
                             requiredStages=deepcopy(required), supported=supported))
            if not supported:
                blockers.append(dict(questId=q['id'], outcomeId=o['id'], operation=operation,
                                     requiresReachedStageIds=deepcopy(required),
                                     reason='Unsupported eligible outcome blocks the entire authored reward batch.'))
        batches[q['id']] = rows
    return dict(batches=batches, blockers=blockers,
                legacyGenericRewardQuestIds=legacy,
                scope='Only research-bearing quests use atomic authored batches; other authored rewards remain on the existing generic path and are not implemented by this adapter.')


def emit(name, quest_id, rows, ws):
    lines = [f'\t{name}.authoredRewards=new QuestRewardBatch("{ws(quest_id)}",runtime.technologies)']
    for row in rows:
        # Unsupported outcomes retain their identifier, but never masquerade as
        # an implemented direct grant even if they name the research operation.
        operation = row['operation'] if row['supported'] else 'unsupported_' + row['operation']
        lines.append(f'\t{name}.authoredRewards.add(new QuestRewardOutcome("{ws(row["id"])}","{ws(operation)}","{ws(row["targetId"])}","{ids(row["requiredStages"])}"))')
    return lines
