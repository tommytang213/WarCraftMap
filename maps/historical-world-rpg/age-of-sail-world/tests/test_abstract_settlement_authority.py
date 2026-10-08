"""Authority membership must not be inferred from object presentation."""
import json
from collections import Counter
from pathlib import Path
import re
import shutil
import sys
import tempfile
import unittest

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT.parent / '_shared/tooling'))
from package_wurst_map import generate, load_config
from scenario_inputs import settlement_sources


class AbstractSettlementAuthorityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temp.cleanup)
        cls.out = Path(cls.temp.name) / 'generated'
        generate(load_config(PROJECT / 'package.json'), cls.out)
        cls.runtime = json.loads((cls.out / 'scenario-runtime.json').read_text())
        cls.source = (cls.out / 'ScenarioData.wurst').read_text()
        cls.world = json.loads((PROJECT / 'scenario/world/world.json').read_text())
        cls.profiles = {r['settlementId']: r for r in json.loads((PROJECT / 'scenario/integration/release-scale-settlements.json').read_text())['settlements']}

    def test_complete_world_is_registered_in_live_authority_and_markets(self):
        expected = {r['id'] for r in self.world['settlements']}
        authority = re.findall(r'runtime.registerSettlement\(new SettlementRuntimeState\("([^"]+)"', self.source)
        markets = set(re.findall(r'runtime.registerMarketProfile\("([^"]+)"', self.source))
        officials = re.findall(r'runtime.appoint\("([^"]+)"', self.source)
        self.assertEqual(len(expected), len(authority))
        self.assertEqual(expected, set(authority))
        self.assertEqual(expected, set(officials))
        self.assertEqual(expected, markets)
        self.assertLessEqual(self.runtime['tradeMarketCount'], 16384)
        detailed = {r['id'] for p, _, _ in settlement_sources(PROJECT) for r in json.loads(p.read_text())['settlements']}
        abstract = expected - detailed
        self.assertEqual(33, len(abstract))
        self.assertEqual(abstract, {k for k, p in self.profiles.items() if p['gameplayRoles']['physicalMap']['modelId'] == 'abstract_regional_projection'})
        for ident in abstract:
            with self.subTest(id=ident):
                row = next(r for r in self.runtime['settlementRuntimeStates'] if r['id'] == ident)
                self.assertFalse(row['projectMilitary'])
                self.assertEqual(self.profiles[ident]['official'], row['official'])
                expected_goods = set(self.profiles[ident]['economy']['availableGoodIds'])
                actual = set(re.findall(r'runtime.registerMarketProfile\("' + ident + r'","([^"]+)"', self.source))
                self.assertEqual(expected_goods, actual)
                self.assertIn(f'new TradeStore("warehouse:{ident}",12000,1000)', self.source)
                point = next(p for p in self.runtime['interactionLocations'] if p['id'] == ident and p['kind'] == 'settlement')
                self.assertEqual([row['x'], row['y']], point['world'])
                self.assertEqual(row['regionId'], point['mapId'])

    def test_governance_exceptions_never_generate_a_capture_projection(self):
        projected = Counter()
        for row in self.runtime['settlementRuntimeStates']:
            profile = self.profiles[row['id']]
            self.assertEqual(profile['captureModel'] == 'city_core', row['capturable'])
            self.assertEqual('city_core' in profile['physicalRepresentationKinds'], row['projectMilitary'])
            if row['projectMilitary']:
                projected[row['regionId']] += 2  # core and authored primary defense
            if not row['capturable']:
                self.assertEqual('community_collective_authority', row['governanceExceptionId'])
                self.assertNotIn('new RuntimeForce("defense:' + row['id'] + ':', self.source)
        budget = json.loads((PROJECT / 'scenario/integration/release-scale-settlements.json').read_text())['performanceBudgets']['maximumActiveSettlementObjects']
        self.assertTrue(all(count <= budget for count in projected.values()))

    def test_content_only_presentation_change_keeps_authority_and_economy(self):
        fixture = PROJECT.parent / 'conformance-campaign'
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / 'fixture'
            shutil.copytree(PROJECT.parent / '_shared', Path(tmp) / '_shared', ignore=shutil.ignore_patterns('__pycache__'))
            shutil.copytree(fixture, project, ignore=shutil.ignore_patterns('_build', '__pycache__'))
            # Only scenario data changes; both variants execute the shared generator.
            source = json.loads((project / 'scenario/world/world.json').read_text())
            ident = source['settlements'][0]['id']
            profile = {'settlementId': ident, 'captureModel': 'city_core',
                       'physicalRepresentationKinds': ['discovery_marker', 'city_core'],
                       'gameplayRoles': {'physicalMap': {'modelId': 'physical'}}}
            integration = project / 'scenario/integration/release-scale-settlements.json'
            integration.parent.mkdir(parents=True, exist_ok=True)
            variants = []
            for abstract in (False, True):
                if abstract:
                    profile['physicalRepresentationKinds'] = ['discovery_marker']
                    profile['gameplayRoles']['physicalMap']['modelId'] = 'abstract_regional_projection'
                integration.write_text(json.dumps({'settlements': [profile]}))
                out = Path(tmp) / str(abstract)
                generate(load_config(project / 'package.json'), out)
                data = json.loads((out / 'scenario-runtime.json').read_text())
                wurst = (out / 'ScenarioData.wurst').read_text()
                row = next(r for r in data['settlementRuntimeStates'] if r['id'] == ident)
                self.assertEqual(not abstract, row['projectMilitary'])
                for key in ('projectMilitary', 'physicalRepresentationKinds', 'presentationModelId'):
                    row.pop(key)
                variants.append((row, data['tradeStoreDefinitions'], re.findall(r'\s+runtime.registerMarketProfile\([^\n]+', wurst)))
            self.assertEqual(variants[0], variants[1])


if __name__ == '__main__':
    unittest.main()
