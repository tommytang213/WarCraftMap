"""Naval source contracts; mutations execute through production Wurst commands."""
import copy
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / 'tooling'))
from naval_services_catalog import build
sys.path.insert(0, str(PROJECT.parent / '_shared/tooling'))
from package_wurst_map import PackagingError, generate, load_config, verify_generated


class NavalServicesCompilationTests(unittest.TestCase):
    def test_exact_entitlements_and_resolved_roster_bills_are_generated(self):
        data, source = build()
        self.assertEqual({'unlock_recruitment': 0, 'hull_repair_throughput': 1500,
                          'close_range_naval_gunfire_damage': 1000,
                          'voyage_hull_weather_resilience': 800},
                         {e['metric']: e['bonusBasisPoints'] for e in data['effects']})
        self.assertIn('"unit", "ship_of_the_line", "unlock_recruitment", 0', source)
        self.assertIn('1540, 98, 78, 700, 1050', source)
        self.assertIn('|battlefleet_doctrine|public_credit|', source)
        self.assertIn('"ship_of_the_line_generic", \'hbsh\', true, false, true', source)
        self.assertIn('"indigenous_war_canoe", \'hbsh\', false, false, false', source)
        self.assertEqual(source, build()[1])
        self.assertNotIn('.unlock(', source)

    def mutation(self, change, filename='scenario/naval/services.json'):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in ['scenario/naval', 'scenario/world', 'scenario/progression', 'scenario/settlements']:
                shutil.copytree(PROJECT / name, root / name, dirs_exist_ok=True)
            data = json.loads((root / filename).read_text()); change(data)
            (root / filename).write_text(json.dumps(data))
            return build(root)

    def test_invalid_gear_recipient_infrastructure_cost_and_typed_binding_fail_closed(self):
        changes = [lambda d: d.update(schemaVersion=2),
                   lambda d: d['rules'].update(repairCost=0),
                   lambda d: d['rules'].update(stormLoss=True),
                   lambda d: d['rules'].update(weatherDays=6),
                   lambda d: d['carronadeMountProfiles'].append('indigenous_war_canoe'),
                   lambda d: d['carvelBuiltProfiles'].append('missing'),
                   lambda d: d['yards'].append(d['yards'][0]),
                   lambda d: d['yards'][0].update(settlementId='edinburgh'),
                   lambda d: d.update(blueprint='coastal_transport')]
        for change in changes:
            with self.subTest(change=change), self.assertRaises((ValueError, KeyError)):
                self.mutation(change)
        def wrong_unlock(d):
            next(n for n in d['technologies'] if n['id'] == 'battlefleet_doctrine')['unlocks'] = []
        with self.assertRaisesRegex(ValueError, 'typed binding'):
            self.mutation(wrong_unlock, 'scenario/world/world.json')

    def test_scenario_rate_and_cost_sensitivity_reaches_executable_definitions(self):
        _, original = build()
        _, source = self.mutation(lambda d: d['rules'].update(repairOutput=200, mountCost=300))
        self.assertNotEqual(source, original)
        self.assertIn('ledger.repairOutput = 200', source)
        self.assertIn('ledger.mountCost = 300', source)
        def change_rate(d):
            next(e for e in d['effects'] if e['metric'] == 'hull_repair_throughput')['bonusBasisPoints'] = 2000
        _, source = self.mutation(change_rate, 'scenario/progression/gameplay-effect-design.json')
        self.assertIn('"hull_repair_throughput", 2000', source)

    def test_shared_services_have_no_scenario_named_research_or_polity(self):
        source = '\n'.join((PROJECT.parent / '_shared/wurst' / name).read_text()
                           for name in ['NavalServices.wurst', 'NavalCampaignRuntime.wurst'])
        for e in build()[0]['effects']:
            self.assertNotIn(e['nodeId'], source)
            self.assertNotIn(e['unlock']['contentId'], source)
        self.assertNotIn('england', source)
        self.assertNotIn('london', source)

    def test_generated_carvel_consumer_and_metadata_reject_rehashed_tampering(self):
        with tempfile.TemporaryDirectory() as tmp:
            generated = Path(tmp)
            config = load_config(PROJECT / 'package.json')
            generate(config, generated)
            verify_generated(config, generated)
            source = (generated / 'ScenarioData.wurst').read_bytes()
            data = (generated / 'scenario-runtime.json').read_bytes()
            provenance = (generated / 'provenance.json').read_bytes()
            for mutation in ('rate', 'refit', 'duplicate_source', 'metadata', 'metadata_type', 'missing', 'duplicate'):
                with self.subTest(mutation=mutation):
                    text = source.decode()
                    payload = json.loads(data)
                    consumers = payload['navalServices']['consumers']
                    carvel = next(c for c in consumers if c['executionSystem'] == 'naval_carvel')
                    if mutation == 'rate':
                        text = text.replace('"voyage_hull_weather_resilience", 800',
                                            '"voyage_hull_weather_resilience", 900')
                    elif mutation == 'refit':
                        text = text.replace('ledger.carvelCost = 200', 'ledger.carvelCost = 1')
                    elif mutation == 'duplicate_source':
                        text += '\n' + build()[1]
                    elif mutation == 'metadata':
                        carvel['refit']['currency'] = 1
                    elif mutation == 'metadata_type':
                        carvel['bonusBasisPoints'] = 800.0
                    elif mutation == 'missing':
                        consumers.remove(carvel)
                    else:
                        consumers.append(copy.deepcopy(carvel))
                    (generated / 'ScenarioData.wurst').write_text(text)
                    (generated / 'scenario-runtime.json').write_text(json.dumps(payload))
                    hashes = json.loads(provenance)
                    for name in ('ScenarioData.wurst', 'scenario-runtime.json'):
                        hashes['outputs'][name] = hashlib.sha256((generated / name).read_bytes()).hexdigest()
                    (generated / 'provenance.json').write_text(json.dumps(hashes))
                    with self.assertRaisesRegex(PackagingError, 'naval bindings'):
                        verify_generated(config, generated)
