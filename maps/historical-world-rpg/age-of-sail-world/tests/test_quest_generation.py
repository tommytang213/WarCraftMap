"""Authored graphs must survive the production packager, including negative controls."""
import copy
from dataclasses import replace
import json
from pathlib import Path
import re
import sys
import tempfile
import unittest

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT.parent / '_shared/tooling'))
from package_wurst_map import PackagingError, generate, load_config
from quest_codegen import validate_graphs


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
