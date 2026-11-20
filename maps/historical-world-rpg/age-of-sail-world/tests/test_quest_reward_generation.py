"""Scoped authored-reward generation; live commits run in QuestRewardTests."""
import copy
import json
from pathlib import Path
import sys
import unittest

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT.parent / '_shared/tooling'))
sys.path.insert(0, str(PROJECT.parent / '_shared/engine'))
from quest_rewards import configuration, emit, RESEARCH
from historical_events import apply_effects


class QuestRewardGenerationTests(unittest.TestCase):
    def setUp(self):
        self.world = json.loads((PROJECT / 'scenario/world/world.json').read_text())
        self.stars = next(q for q in self.world['quests'] if q['id'] == 'india_stars_and_pepper')

    def test_only_research_bearing_batches_are_selected_and_other_gap_is_explicit(self):
        result = configuration(self.world)
        self.assertEqual({'india_stars_and_pepper', 'ocean_of_accounts'}, set(result['batches']))
        self.assertEqual(302, len(result['legacyGenericRewardQuestIds']))
        self.assertIn('europe_printed_compact', result['legacyGenericRewardQuestIds'])
        self.assertIn('not implemented', result['scope'])
        self.assertEqual(5, len(result['blockers']))
        self.assertEqual(['standardized_charts'], [r['targetId'] for r in result['batches'][self.stars['id']] if r['supported']])
        self.assertTrue(any(r['outcomeId'] == 'calicut_credit' for r in result['blockers']))
        source = '\n'.join(emit('example', self.stars['id'], result['batches'][self.stars['id']], lambda s: s))
        self.assertIn('new QuestRewardBatch("india_stars_and_pepper",runtime.technologies)', source)
        self.assertIn('unsupported_quest_economy_adjust_treasury', source)

    def test_known_target_direct_grant_matches_python_without_invented_prerequisites(self):
        state = dict(knownResearchIds=['standardized_charts', 'movable_type_printing'], completedResearchIds=[])
        granted = apply_effects(state, [dict(kind='complete_research', targetId='standardized_charts')])
        self.assertEqual(['standardized_charts'], granted['completedResearchIds'])
        self.assertEqual([], state['completedResearchIds'])
        self.assertEqual(granted, apply_effects(granted, [dict(kind='complete_research', targetId='standardized_charts')]))
        self.stars['outcomes'] = [o for o in self.stars['outcomes'] if o['outcomeId'] == RESEARCH]
        self.assertFalse(any(r['questId'] == self.stars['id'] for r in configuration(self.world)['blockers']))
        rows = configuration(self.world)['batches'][self.stars['id']]
        self.assertEqual(1, len(rows))
        self.assertTrue(rows[0]['supported'])

    def test_reached_stage_conditions_survive_and_impossible_routes_fail(self):
        reward = next(o for o in self.stars['outcomes'] if o['outcomeId'] == RESEARCH)
        reward['requiresReachedStageIds'] = ['market_measure', 'consult_pilots']
        rows = configuration(self.world)['batches'][self.stars['id']]
        self.assertEqual(['market_measure', 'consult_pilots'], next(r for r in rows if r['supported'])['requiredStages'])
        for stages in [['missing'], ['consult_king', 'consult_pilots'], ['consult_pilots', 'consult_pilots']]:
            reward['requiresReachedStageIds'] = stages
            with self.subTest(stages=stages), self.assertRaises(ValueError):
                configuration(self.world)

    def test_unknown_research_extra_semantics_and_duplicate_ids_fail_closed(self):
        original = copy.deepcopy(self.world)
        for mutation in ['unknown', 'extra', 'duplicate']:
            world = copy.deepcopy(original)
            q = next(q for q in world['quests'] if q['id'] == self.stars['id'])
            reward = next(o for o in q['outcomes'] if o['outcomeId'] == RESEARCH)
            if mutation == 'unknown': reward['entityRefs'][0]['id'] = 'missing_research'
            elif mutation == 'extra': reward['paid'] = 0
            else: q['outcomes'].append(copy.deepcopy(reward))
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                configuration(world)

    def test_unsupported_research_named_kind_cannot_masquerade_as_a_grant(self):
        reward = next(o for o in self.stars['outcomes'] if o['outcomeId'] == RESEARCH)
        reward['kind'] = 'other_outcome'
        rows = configuration(self.world)['batches'][self.stars['id']]
        self.assertTrue(all(not r['supported'] for r in rows))
        source = '\n'.join(emit('example', self.stars['id'], rows, lambda s: s))
        self.assertIn('unsupported_quest_technology_complete_research', source)


if __name__ == '__main__':
    unittest.main()
