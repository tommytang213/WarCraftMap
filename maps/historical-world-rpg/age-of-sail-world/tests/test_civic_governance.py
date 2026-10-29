"""Scenario compilation guards; real mutations execute in CivicGovernanceTests."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT.parent / '_shared/tooling'))
from civic_governance import configuration


class CivicGovernanceCompilationTests(unittest.TestCase):
    def setUp(self):
        self.world = json.loads((PROJECT / 'scenario/world/world.json').read_text())
        self.data = json.loads((PROJECT / 'scenario/progression/civic-governance.json').read_text())
        self.authored = {}
        for path in (PROJECT / 'scenario/settlements').glob('*-1450.json'):
            for row in json.loads(path.read_text())['settlements']:
                self.authored[row['id']] = ('region', row)
        self.settlements = [{'id': ident} for ident in self.authored]
        self.trade = ['\truntime.registerMarketProfile("hawaii_royal_center","barkcloth",90,1000)']

    def test_all_seven_typed_identities_compile_from_exact_design_without_1450_grants(self):
        source, catalog, paths = configuration(PROJECT, self.world, self.settlements, self.authored, self.trade)
        self.assertEqual(len(self.settlements), catalog['districtCount'])
        self.assertEqual(7, len(catalog['effects']))
        self.assertIn('new CivicEffect("modifier", "progression_civil_service_examinations", "records_tax_collection_efficiency", 500)', source)
        self.assertIn('new CivicEffect("policy", "progression_abolitionist_public_sphere", "civic_reform_diffusion", 500)', source)
        self.assertIn('new CivicEffect("ability", "epidemic_control", "epidemic_losses_avoided", 2500)', source)
        self.assertIn('new CivicEffect("modifier", "progression_cadastral_survey", "land_tax_collection_efficiency", 500)', source)
        self.assertIn('ledger.responseDays = 90', source)
        self.assertIn('ledger.cooldownDays = 90', source)
        self.assertIn('"barkcloth", 4, 1000)', source)
        self.assertNotIn('unlock(', source)
        self.assertNotIn('treasury', source)
        self.assertEqual(8, len(paths))

    def test_districts_retain_authored_provinces_and_economic_asymmetry(self):
        source, _, _ = configuration(PROJECT, self.world, self.settlements, self.authored, self.trade)
        self.assertIn('new CivicDistrict("london", "greater_london", 3341, true', source)
        for ident, (_, row) in self.authored.items():
            self.assertIn(f'new CivicDistrict("{ident}", "{row["provinceId"]}",', source)
        # Static conditions do not claim a country with more compressed map
        # markers has a larger historical army or population.
        self.assertNotIn('manpower', source)

    def test_unavailable_scenario_has_a_safe_empty_registration(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, catalog, paths = configuration(Path(tmp), {}, [], {}, [])
        self.assertIn('\tskip', source)
        self.assertEqual({}, catalog)
        self.assertEqual([], paths)

    def test_missing_typed_unlock_is_rejected_before_compilation(self):
        broken = copy.deepcopy(self.world)
        next(x for x in broken['technologies'] if x['id'] == 'cadastral_survey')['unlocks'] = []
        with self.assertRaisesRegex(ValueError, 'exact typed'):
            configuration(PROJECT, broken, self.settlements, self.authored, self.trade)


if __name__ == '__main__':
    unittest.main()
