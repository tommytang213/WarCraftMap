"""Scenario compiler rejects missing multilingual references and mismatched consumers."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT.parent / '_shared/tooling'))
from science_exploration import configuration, validate_comparison


class ComparativeCompilationTests(unittest.TestCase):
    def setUp(self):
        self.contract = json.loads((PROJECT / 'scenario/progression/comparative-linguistics.json').read_text())
        self.world = json.loads((PROJECT / 'scenario/world/world.json').read_text())
        self.nodes = {n['id']: n for n in self.world['technologies'] + self.world['institutions']}

    def test_exact_authored_source_is_400_bp_and_target_is_available_after_full_chain(self):
        validate_comparison(self.contract, self.nodes)
        self.assertEqual(400, self.contract['bonusBasisPoints'])
        self.assertEqual(['metric_metrology'], self.nodes['comparative_linguistics']['prerequisiteIds'])
        self.assertEqual(['geological_survey', 'skirmisher_doctrine'], self.nodes['metric_metrology']['prerequisiteIds'])
        target = 'systematic_natural_history'
        def ancestors(id):
            return {v for pre in self.nodes[id]['prerequisiteIds'] for v in {pre} | ancestors(pre)}
        self.assertNotIn(target, ancestors('comparative_linguistics'))
        self.assertEqual(['scientific_societies', 'standardized_charts'], self.nodes[target]['prerequisiteIds'])
        self.assertEqual(280, self.nodes[target]['timeCost']['baseCost'])
        self.assertEqual(1735, self.nodes[target]['timeCost']['preferredYear'])
        self.assertEqual(83, (9000 + 108) // 109)
        self.assertEqual(80, (9000 + 112) // 113)

    def test_missing_monolingual_unknown_duplicate_or_mistyped_definitions_reject(self):
        changes = [lambda d: d.update(bonusBasisPoints=True),
                   lambda d: d.update(bonusBasisPoints=399),
                   lambda d: d.update(metric='research_generation_efficiency'),
                   lambda d: d['unlock'].update(kind='policy'),
                   lambda d: d.update(minimumAdministration=0),
                   lambda d: d.update(corpora=[]),
                   lambda d: d['corpora'][1].update(language='latin'),
                   lambda d: d['corpora'].append(d['corpora'][0]),
                   lambda d: d['targets'][0].update(sourceLanguages=['latin']),
                   lambda d: d['targets'][0].update(corpusIds=['missing']),
                   lambda d: d['targets'][0].update(corpusIds=['linnaeus_systema_naturae']),
                   lambda d: d['targets'][0].update(id='unknown'),
                   lambda d: d['targets'].append(d['targets'][0])]
        for change in changes:
            data = copy.deepcopy(self.contract)
            change(data)
            with self.subTest(data=data), self.assertRaises(ValueError):
                validate_comparison(data, self.nodes)

    def test_generated_requirements_and_consumer_metadata_share_authority(self):
        from test_science_exploration import ScienceCompilationTests
        f = ScienceCompilationTests(); f.setUp()
        source, catalog, paths = f.compile()
        self.assertIn('site2.corpora = "|linnaeus_systema_naturae:latin|sloane_jamaica:english|"', source)
        self.assertIn('"|systematic_natural_history|", "linnaeus_systema_naturae:latin|sloane_jamaica:english|"', source)
        consumer, = catalog['consumers']
        for field in ('nodeId', 'unlock', 'metric', 'bonusBasisPoints', 'siteId', 'corpora', 'targets'):
            self.assertEqual(self.contract[field], consumer[field])
        self.assertEqual('comparative_scholarship', consumer['executionSystem'])
        self.assertIn(PROJECT / 'scenario/progression/comparative-linguistics.json', paths)
        self.assertNotIn('unlock(', source)

class ComparativeGeneratedVerificationTests(unittest.TestCase):
    def test_resealed_runtime_metadata_and_executable_requirements_must_match_scenario(self):
        import hashlib
        from package_wurst_map import generate, load_config, verify_generated, PackagingError
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = load_config(PROJECT / 'package.json')
            generate(config, root)
            source = (root / 'ScenarioData.wurst').read_text()
            runtime = json.loads((root / 'scenario-runtime.json').read_text())
            provenance = json.loads((root / 'provenance.json').read_text())
            def reseal(name, content):
                (root / name).write_text(content)
                provenance['outputs'][name] = hashlib.sha256(content.encode()).hexdigest()
                (root / 'provenance.json').write_text(json.dumps(provenance))
            registration = next(line for line in source.splitlines() if 'new ScienceWorkSource(' in line)
            for changed in (source.replace(registration + '\n', ''),
                            source.replace(registration, registration + '\n' + registration),
                            source.replace('"linnaeus_systema_naturae:latin|sloane_jamaica:english|"', '"linnaeus_systema_naturae:latin|"')):
                reseal('ScenarioData.wurst', changed)
                with self.assertRaisesRegex(PackagingError, 'science bindings'):
                    verify_generated(config, root)
            reseal('ScenarioData.wurst', source)
            for mutate in (lambda d: d['scienceExploration']['consumers'][0].update(bonusBasisPoints=500),
                           lambda d: d['scienceExploration']['consumers'][0].update(targets=[])):
                damaged = copy.deepcopy(runtime); mutate(damaged)
                reseal('scenario-runtime.json', json.dumps(damaged))
                with self.assertRaisesRegex(PackagingError, 'science bindings'):
                    verify_generated(config, root)


if __name__ == '__main__':
    unittest.main()
