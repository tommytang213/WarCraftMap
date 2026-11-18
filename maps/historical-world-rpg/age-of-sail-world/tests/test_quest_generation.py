"""Authored graphs must survive the production packager, including negative controls."""
import copy
from dataclasses import replace
import json
from pathlib import Path
import re
import sys
import tempfile
import unittest
from unittest.mock import patch

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT.parent / '_shared/tooling'))
from package_wurst_map import PackagingError, generate, load_config
from quest_codegen import validate_graphs, emit_quests, trade_quest_bindings, consultation_quest_bindings


class QuestGenerationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = load_config(PROJECT / 'package.json')
        cls.world = json.loads(cls.config.scenario_file.read_text())
        cls.bindings = json.loads((PROJECT / 'scenario/quest-condition-bindings.json').read_text())
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            generate(cls.config, root)
            cls.source = (root / 'ScenarioData.wurst').read_text()
            cls.runtime = json.loads((root / 'scenario-runtime.json').read_text())

    def test_every_authored_graph_and_prerequisite_survives_both_outputs(self):
        self.assertEqual(self.world['quests'], self.runtime['questDefinitions'])
        self.assertEqual(304, sum(len(q['stages']) > 1 for q in self.world['quests']))
        records = re.findall(r'let (quest\d+)=new RuntimeQuest\("([^"]+)"', self.source)
        self.assertEqual([q['id'] for q in self.world['quests']], [q for _, q in records])
        def tokens(values):
            return ''.join(x + '~' for x in values)
        for (name, ident), q in zip(records, self.world['quests']):
            with self.subTest(quest=ident):
                self.assertIn(f'{name}.graph=new QuestGraph("{q["initialStageId"]}","{tokens([p["id"] for p in q["prerequisites"]])}")', self.source)
                stages = re.findall(re.escape(name) + r'\.graph.addStage\(new QuestStage\("([^"]+)","[^\n]*?","([^"]*)","([^"]*)"\)\)', self.source)
                self.assertEqual([(s['id'], tokens(s['objectiveIds']), tokens(s['nextStageIds'])) for s in q['stages']], stages)
                objectives = re.findall(r'let ' + re.escape(name) + r'objective\d+=new QuestObjective\("([^"]+)","[^\n]*?","([^"]+)","([^"]*)","([^"]+)"\)', self.source)
                expected = [(o['id'], o['conditionId'], ''.join(f'{r["kind"]}:{r["id"]}~' for r in sorted(o['entityRefs'], key=lambda r:(r['kind'], r['id']))), self.runtime['questConditionBindings'][ident + ':' + o['id']]) for o in q['objectives']]
                self.assertEqual(expected, objectives)

    def reject_world(self, world, diagnostic):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            scenario = root / 'world.json'
            scenario.write_text(json.dumps(world))
            with self.assertRaisesRegex(PackagingError, diagnostic):
                generate(replace(self.config, scenario_file=scenario), root / 'generated')
            self.assertFalse((root / 'generated/ScenarioData.wurst').exists())

    def test_nonexact_guidance_retains_authored_point_for_earned_knowledge_only(self):
        quest = copy.deepcopy(self.world['quests'][0])
        objective = quest['objectives'][0]['id']
        for precision in ('region', 'hidden', 'approximate'):
            quest['journal']['destinations'][objective] = dict(
                precision=precision, regionId='europe', locationId='quest_location_london',
                requiredClueIds=['sealed_chart'], searchAreas=[dict(x=1, y=2, radius=3)])
            generated = '\n'.join(emit_quests([quest], self.runtime['questConditionBindings'], lambda x: x.replace('"', '\\"')))
            self.assertIn(f'new QuestGuidance("{precision}","europe","quest_location_london",', generated)
            self.assertIn('"sealed_chart~")', generated)
        # Missing authored location never falls back to condition entity refs.
        quest['journal']['destinations'][objective] = dict(precision='region', regionId='europe')
        generated = '\n'.join(emit_quests([quest], self.runtime['questConditionBindings'], lambda x: x.replace('"', '\\"')))
        self.assertIn('new QuestGuidance("region","europe","",', generated)

    def test_generation_rejects_omitted_authored_stage(self):
        world = copy.deepcopy(self.world)
        q = next(q for q in world['quests'] if q['id'] == 'europe_printed_compact')
        q['stages'] = q['stages'][:1]
        q['stages'][0]['nextStageIds'] = []
        q['objectives'] = q['objectives'][:1]
        self.reject_world(world, 'authored quest projection mismatch')

    def test_generation_rejects_omitted_prerequisites(self):
        world = copy.deepcopy(self.world)
        next(q for q in world['quests'] if q['prerequisites'])['prerequisites'] = []
        self.reject_world(world, 'authored quest projection mismatch')

    def test_missing_or_unsupported_condition_bindings_fail_closed(self):
        for change in ('missing', 'generic'):
            bindings = copy.deepcopy(self.bindings)
            if change == 'missing':
                del bindings['conditions']['quest_diplomacy_satisfied']
            else:
                bindings['conditions']['quest_diplomacy_satisfied']['adapter'] = 'generic_interaction'
            with self.assertRaisesRegex(ValueError, 'unsupported condition binding'):
                validate_graphs(self.world['quests'], bindings)
        config = load_config(PROJECT.parent / 'conformance-campaign/package.json')
        world = json.loads(config.scenario_file.read_text())
        world['quests'][0]['objectives'][0]['conditionId'] = 'unsupported_condition'
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            scenario = root / 'world.json'
            scenario.write_text(json.dumps(world))
            with self.assertRaisesRegex(PackagingError, 'unsupported condition binding'):
                generate(replace(config, scenario_file=scenario), root / 'generated')

    def test_unimplemented_conditions_are_explicit_and_never_bound_to_visits(self):
        blockers = self.runtime['questIntegrationBlockers']
        self.assertTrue(blockers)
        for row in blockers:
            self.assertEqual('domain_receipt', self.runtime['questConditionBindings'][row['questId'] + ':' + row['objectiveId']])
            self.assertTrue(row['reason'])
        for row in self.world['quests']:
            for obj in row['objectives']:
                binding = self.runtime['questConditionBindings'][row['id'] + ':' + obj['id']]
                if obj['conditionId'] == 'quest_travel_satisfied':
                    self.assertEqual('physical_visit', binding)
                if obj['id'] == 'protect_home':
                    self.assertEqual('domain_receipt', binding)

    def test_paid_player_research_has_one_explicit_objective_binding(self):
        key = 'india_stars_and_pepper:advance_navigation'
        self.assertEqual('research_unlocked', self.runtime['questConditionBindings'][key])
        self.assertNotIn(key, {row['questId'] + ':' + row['objectiveId'] for row in self.runtime['questIntegrationBlockers']})
        self.assertIn('"research_unlocked"', self.source)
        for authority in ('other', None):
            bindings = copy.deepcopy(self.bindings)
            bindings['objectives'][key]['authority'] = authority
            with self.assertRaisesRegex(ValueError, 'research unlock requires'):
                validate_graphs(self.world['quests'], bindings)
        world = copy.deepcopy(self.world['quests'])
        quest = next(q for q in world if q['id'] == 'india_stars_and_pepper')
        next(o for o in quest['objectives'] if o['id'] == 'advance_navigation')['entityRefs'] = [{'kind': 'settlement', 'id': 'calicut'}]
        with self.assertRaisesRegex(ValueError, 'research unlock requires'):
            validate_graphs(world, self.bindings)
        # Other research-looking objectives still need independent gameplay
        # conditions. One real consumer must not clear their blockers.
        self.assertEqual('domain_receipt', self.runtime['questConditionBindings']['east_asia_coastal_record:improve_charts'])

    def test_committed_trade_binding_is_objective_scoped_and_uses_real_market(self):
        key = 'india_stars_and_pepper:trade_pepper'
        self.assertEqual('domain_receipt', self.runtime['questConditionBindings'][key])
        self.assertEqual([dict(questId='india_stars_and_pepper', stageId='market_measure',
                               objectiveId='trade_pepper', marketId='calicut', commodityId='pepper')],
                         self.runtime['questTradeBindings'])
        blockers = {row['questId'] + ':' + row['objectiveId'] for row in self.runtime['questIntegrationBlockers']}
        self.assertNotIn(key, blockers)
        self.assertNotIn('india_stars_and_pepper:consult_pilot_guild', blockers)
        self.assertIn('india_stars_and_pepper:meet_krishnadevaraya', blockers)
        self.assertIn('runtime.registerMarketProfile("calicut","pepper",', self.source)
        self.assertIn('runtime.registerQuestTrade(new QuestTradeBinding("india_stars_and_pepper", "market_measure", "trade_pepper", "calicut", "pepper"))', self.source)
        for field, value in [('stageId', 'consult_pilots'), ('marketId', 'cochin'),
                             ('commodityId', 'bad-id'), ('consumer', 'generic_trade')]:
            changed = copy.deepcopy(self.bindings)
            changed['objectives'][key][field] = value
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'committed trade'):
                validate_graphs(self.world['quests'], changed)
        changed = copy.deepcopy(self.bindings)
        changed['objectives']['unknown:trade_pepper'] = changed['objectives'].pop(key)
        with self.assertRaisesRegex(ValueError, 'does not exist'):
            validate_graphs(self.world['quests'], changed)
        changed = copy.deepcopy(self.bindings)
        changed['conditions']['quest_trade_satisfied'] = changed['objectives'].pop(key)
        with self.assertRaisesRegex(ValueError, 'objective-specific'):
            validate_graphs(self.world['quests'], changed)

    def test_packager_rejects_syntactically_valid_missing_trade_commodity(self):
        rows = copy.deepcopy(self.runtime['questTradeBindings'])
        rows[0]['commodityId'] = 'nonexistent_commodity'
        with tempfile.TemporaryDirectory() as directory, patch('package_wurst_map.trade_quest_bindings', return_value=rows):
            with self.assertRaisesRegex(PackagingError, 'no generated market/commodity'):
                generate(self.config, Path(directory))

    def test_binding_prepasses_reject_non_object_rows_with_the_key(self):
        for value in (None, [], "invalid", 1, True):
            changed = copy.deepcopy(self.bindings)
            changed['objectives']['unused:objective'] = value
            for check in (trade_quest_bindings, consultation_quest_bindings, validate_graphs):
                with self.subTest(value=value, check=check.__name__), self.assertRaisesRegex(ValueError, 'unused:objective.*object'):
                    check(self.world['quests'], changed)

    def test_same_stage_trade_objectives_must_not_share_an_ambiguous_receipt(self):
        quests = copy.deepcopy(self.world['quests'])
        bindings = copy.deepcopy(self.bindings)
        q = next(q for q in quests if q['id'] == 'india_stars_and_pepper')
        objective = copy.deepcopy(next(o for o in q['objectives'] if o['id'] == 'trade_pepper'))
        objective['id'] = 'second_trade'
        q['objectives'].append(objective)
        next(s for s in q['stages'] if s['id'] == 'market_measure')['objectiveIds'].append('second_trade')
        bindings['objectives'][q['id'] + ':second_trade'] = copy.deepcopy(bindings['objectives'][q['id'] + ':trade_pepper'])
        with self.assertRaisesRegex(ValueError, 'cannot share a committed trade binding'):
            validate_graphs(quests, bindings)

    def test_packager_accepts_an_actual_industry_only_market_pair(self):
        market, good = next(pair for pair in self.runtime['industry']['markets']
                            if f'runtime.registerMarketProfile("{pair[0]}","{pair[1]}",' not in self.source)
        rows = copy.deepcopy(self.runtime['questTradeBindings'])
        rows[0].update(marketId=market, commodityId=good)
        with tempfile.TemporaryDirectory() as directory, patch('package_wurst_map.trade_quest_bindings', return_value=rows):
            generate(self.config, Path(directory))
            generated = (Path(directory) / 'ScenarioData.wurst').read_text()
            self.assertIn(f'"{market}", "{good}"))', generated)

    def test_local_consultation_binding_is_exact_and_has_a_real_location(self):
        key = 'india_stars_and_pepper:consult_pilot_guild'
        rows = self.runtime['questConsultationBindings']
        self.assertEqual([dict(questId='india_stars_and_pepper', stageId='consult_pilots',
                              objectiveId='consult_pilot_guild', providerId='calicut_pilot_guild',
                              providerName="Calicut's pilot guild", locationId='calicut',
                              institutionId='renaissance_humanism')], rows)
        rpg_function = self.source.split('public function configureGeneratedRpg(WarcraftRpgRuntime runtime)', 1)[1].split('\npublic function ', 1)[0]
        arguments = ', '.join(json.dumps(rows[0][key]) for key in
                              ('questId', 'stageId', 'objectiveId', 'providerId', 'providerName', 'locationId', 'institutionId'))
        self.assertIn('runtime.registerConsultation(new QuestConsultationBinding(' + arguments + '))', rpg_function)
        for field, value in [('stageId', 'consult_king'), ('institutionId', 'missing'),
                             ('providerId', 'bad-id'), ('providerId', 'a' * 57), ('providerName', 'bad\\nname')]:
            changed = copy.deepcopy(self.bindings)
            changed['objectives'][key][field] = value.replace('\\n', '\n')
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'consultation'):
                validate_graphs(self.world['quests'], changed)
        changed = copy.deepcopy(self.bindings)
        changed['objectives'][key]['providerId'] = 'a' * 56
        validate_graphs(self.world['quests'], changed)
        changed['objectives']['missing:consult'] = changed['objectives'].pop(key)
        with self.assertRaisesRegex(ValueError, 'does not exist'):
            validate_graphs(self.world['quests'], changed)
        rows = copy.deepcopy(rows)
        rows[0]['locationId'] = 'nonexistent_location'
        with tempfile.TemporaryDirectory() as directory, patch('package_wurst_map.consultation_quest_bindings', return_value=rows):
            with self.assertRaisesRegex(PackagingError, 'no generated settlement location'):
                generate(self.config, Path(directory))

    def test_generated_reward_batches_are_scoped_and_leave_unsupported_siblings_explicit(self):
        catalog = self.runtime['questRewardIntegration']
        self.assertEqual({'india_stars_and_pepper', 'ocean_of_accounts'}, set(catalog['batches']))
        self.assertEqual(302, len(catalog['legacyGenericRewardQuestIds']))
        registrations = re.findall(r'([a-zA-Z0-9]+)\.authoredRewards=new QuestRewardBatch\("([^"\n]+)",runtime.technologies\)', self.source)
        self.assertEqual(set(catalog['batches']), {ident for _, ident in registrations})
        self.assertEqual(2, len(registrations))
        for name, ident in registrations:
            self.assertEqual(len(catalog['batches'][ident]), self.source.count(name + '.authoredRewards.add('))
        self.assertIn('unsupported_quest_economy_adjust_treasury', self.source)

    def test_graph_validator_rejects_unknown_and_cyclic_edges_or_duplicate_objectives(self):
        for kind in ('missing', 'cycle', 'duplicate', 'prerequisite'):
            quests = copy.deepcopy(self.world['quests'])
            q = next(q for q in quests if q['id'] == 'europe_printed_compact')
            if kind == 'missing': q['stages'].pop()
            if kind == 'cycle': q['stages'][-1]['nextStageIds'] = [q['initialStageId']]
            if kind == 'duplicate': q['stages'][1]['objectiveIds'] = q['stages'][0]['objectiveIds']
            if kind == 'prerequisite': q['prerequisites'] = [{'kind':'quest_completed', 'id':'missing'}]
            with self.assertRaises(ValueError): validate_graphs(quests, self.bindings)


if __name__ == '__main__': unittest.main()
