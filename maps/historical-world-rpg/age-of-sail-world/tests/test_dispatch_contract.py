"""Dispatch generation/evidence guards; production outcomes run in DispatchTests."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT.parent / '_shared/tooling'))
from dispatch_contract import configuration, verified_bindings, verify_registration


class DispatchContractTests(unittest.TestCase):
    def setUp(self):
        self.world = json.loads((PROJECT / 'scenario/world/world.json').read_text())
        self.data = json.loads((PROJECT / 'scenario/progression/dispatch-contract.json').read_text())

    def test_generated_dispatch_keeps_exact_research_identity_and_historical_costs(self):
        lines, effects, sources = configuration(PROJECT, self.world)
        self.assertEqual([self.data['effect']], effects)
        self.assertIn('\tledger.dispatchOperatingBasisPoints = 25', lines)
        self.assertIn('\tledger.addDispatchLink("lisbon", "goa")', lines)
        self.assertEqual(6, len(self.data['relayLinks']))
        self.assertEqual(2, len(sources))
        node = next(n for n in self.world['technologies'] if n['id'] == 'ciphered_dispatches')
        self.assertEqual(['courier_relays'], node['prerequisiteIds'])
        self.assertEqual({'preferredYear': 1480, 'baseCost': 104, 'aheadOfTimeCostMultiplier': 8,
                          'additionalMultiplierPerYearAhead': .08}, node['timeCost'])
        self.assertEqual([{'kind': 'modifier', 'contentId': 'progression_ciphered_dispatches'}], node['unlocks'])
        self.assertEqual(set(), verified_bindings(PROJECT))
        self.assertEqual(set(), verified_bindings(PROJECT, {}, 'not evidence', '0' * 40))

    def test_missing_unlock_and_relay_prerequisite_fail_closed(self):
        for node_id, field in [('ciphered_dispatches', 'unlocks'), ('ciphered_dispatches', 'prerequisiteIds'),
                               ('courier_relays', 'unlocks')]:
            world = copy.deepcopy(self.world)
            next(n for n in world['technologies'] if n['id'] == node_id)[field] = []
            with self.subTest(node=node_id, field=field), self.assertRaises(ValueError):
                configuration(PROJECT, world)

    def test_invalid_effect_cost_and_network_fail_closed(self):
        changes = []
        for value in (0, -1, True, 1001):
            data = copy.deepcopy(self.data)
            data['effect']['bonusBasisPoints'] = value
            changes.append(data)
        for value in (0, -1, True, 101):
            data = copy.deepcopy(self.data)
            data['operatingBasisPoints'] = value
            changes.append(data)
        for links in ([], self.data['relayLinks'] * 2, [{'originId': 'unknown', 'recipientId': 'goa'}],
                      [{'originId': 'goa', 'recipientId': 'goa'}]):
            data = copy.deepcopy(self.data)
            data['relayLinks'] = links
            changes.append(data)
        original = Path.read_text
        for data in changes:
            def read(path, *args, **kwargs):
                if path.name == 'dispatch-contract.json':
                    return json.dumps(data)
                return original(path, *args, **kwargs)
            with self.subTest(data=data), patch.object(Path, 'read_text', read), self.assertRaises(ValueError):
                configuration(PROJECT, self.world)

    def test_executable_and_runtime_tampering_fail_even_with_resealed_hashes(self):
        lines, effects, _ = configuration(PROJECT, self.world)
        source = '\n'.join(lines + [
            '\tresearch.register(new CivicEffect("modifier", "progression_ciphered_dispatches", '
            '"remote_survey_dispatch_time_reduction", 1000))']) + '\n'
        catalog = {'effects': effects}
        verify_registration(PROJECT, self.world, source, catalog)
        for broken in (source.replace('1000))', '1100))'),
                       source.replace('("lisbon", "goa")', '("unknown", "goa")'),
                       source + '\tledger.addDispatchLink("london", "goa")\n',
                       source.replace('dispatchOperatingBasisPoints = 25', 'dispatchOperatingBasisPoints = 0')):
            with self.subTest(source=broken), self.assertRaisesRegex(ValueError, 'registration differs'):
                verify_registration(PROJECT, self.world, broken, catalog)
        with self.assertRaises(ValueError):
            verify_registration(PROJECT, self.world, source, {'effects': []})

    def test_other_scenarios_have_no_implicit_dispatch_entitlement(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(([], [], []), configuration(Path(tmp), {}))

    def test_scenario_edits_change_executable_registration(self):
        data = copy.deepcopy(self.data)
        data['effect']['bonusBasisPoints'] = 500
        data['operatingBasisPoints'] = 30
        data['relayLinks'] = data['relayLinks'][:1]
        original = Path.read_text
        def read(path, *args, **kwargs):
            if path.name == 'dispatch-contract.json':
                return json.dumps(data)
            return original(path, *args, **kwargs)
        with patch.object(Path, 'read_text', read):
            lines, effects, _ = configuration(PROJECT, self.world)
        self.assertEqual(500, effects[0]['bonusBasisPoints'])
        self.assertIn('\tledger.dispatchOperatingBasisPoints = 30', lines)
        self.assertEqual(1, sum('addDispatchLink' in line for line in lines))


if __name__ == '__main__':
    unittest.main()
