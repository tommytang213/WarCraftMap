"""Authored administrative contracts; actual economic mutations run in Wurst."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT.parent / '_shared/tooling'))
from administrative_governance import configuration, verified_bindings


class AdministrativeContractTests(unittest.TestCase):
    def setUp(self):
        self.world = json.loads((PROJECT / 'scenario/world/world.json').read_text())
        self.contract = json.loads((PROJECT / 'scenario/progression/administrative-contracts.json').read_text())

    def test_exact_typed_effects_and_catalogue_adoption_requirements(self):
        lines, effects, urban, sources = configuration(PROJECT, self.world)
        self.assertEqual([500, 400, 500], [e['bonusBasisPoints'] for e in effects])
        self.assertEqual(['modifier', 'policy', 'modifier'], [e['unlock']['kind'] for e in effects])
        self.assertIn('\tledger.municipalMinimumUrbanization = 11', lines)
        self.assertEqual((20, 5), (urban['urbanPercent'], urban['otherPercent']))
        self.assertEqual(3, len(sources))
        # Merely compiling a contract cannot close a release finding.
        self.assertEqual(set(), verified_bindings(PROJECT))

    def test_missing_or_changed_research_unlock_and_prerequisite_fail_closed(self):
        for node_id in ('chancery_archives', 'chartered_municipalities', 'civil_service_examinations'):
            with self.subTest(node=node_id):
                world = copy.deepcopy(self.world)
                node = next(n for n in world['technologies'] + world['institutions'] if n['id'] == node_id)
                node['unlocks'] = []
                with self.assertRaisesRegex(ValueError, 'typed binding'):
                    configuration(PROJECT, world)
        world = copy.deepcopy(self.world)
        next(n for n in world['institutions'] if n['id'] == 'chartered_municipalities')['prerequisiteIds'] = []
        with self.assertRaisesRegex(ValueError, 'adoption requirements'):
            configuration(PROJECT, world)

    def test_invalid_costs_skills_urbanization_and_bonus_reject(self):
        for group, field, value in [('rules', 'minimumAdministration', 101),
                                    ('rules', 'archiveUpkeepBasisPoints', -1),
                                    ('urbanization', 'otherPercent', True),
                                    ('urbanization', 'urbanPercent', 101)]:
            with self.subTest(field=field):
                data = copy.deepcopy(self.contract)
                data[group][field] = value
                original = Path.read_text
                def read(path, *args, **kwargs):
                    if path.name == 'administrative-contracts.json':
                        return json.dumps(data)
                    return original(path, *args, **kwargs)
                with patch.object(Path, 'read_text', read), self.assertRaises(ValueError):
                    configuration(PROJECT, self.world)

    def test_other_scenarios_keep_safe_empty_administrative_contract(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(([], [], {}, []), configuration(Path(tmp), {}))


if __name__ == '__main__':
    unittest.main()
