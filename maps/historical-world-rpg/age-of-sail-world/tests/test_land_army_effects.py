"""Compilation/mutation guards; production transactions execute in Wurst tests."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / 'tooling'))
sys.path.insert(0, str(PROJECT.parent / '_shared/tooling'))
import land_army_catalog as land


class LandArmyCompilationTests(unittest.TestCase):
    def test_exact_approved_values_and_actual_kit_are_compiled(self):
        payload = land.build()
        effects = {e['metric']: e for e in payload['catalog']['effects']}
        self.assertEqual({k: v['bonusBasisPoints'] for k, v in effects.items()}, {
            'firearm_reload_efficiency': 500, 'artillery_production_throughput': 800,
            'artillery_supply_waste_reduction': 800, 'anti_cavalry_melee_defense': 800})
        profiles = {p['id']: p for p in payload['catalog']['profiles']}
        self.assertTrue(profiles['european_late_line_infantry']['bayonet'])
        self.assertFalse(profiles['european_musket_battalion']['bayonet'])
        self.assertTrue(profiles['east_asian_matchlock_infantry']['firearm'])
        self.assertFalse(profiles['field_artillery_battery']['firearm'])
        self.assertTrue(profiles['field_artillery_battery']['artillery'])
        self.assertTrue(profiles['sabre_cavalry']['cavalry'])
        self.assertEqual(1730, profiles['european_late_line_infantry']['firstYear'])
        self.assertEqual(',cast_cannon,', profiles['field_artillery_battery']['requiredResearch'])
        self.assertNotIn('unlock(', payload['wurst'])
        self.assertNotIn('treasury', payload['wurst'])

    def test_invalid_typed_contract_rules_and_equipment_fail_closed(self):
        data = json.loads((PROJECT / 'scenario/progression/land-army.json').read_text())
        design = json.loads((PROJECT / data['designSource']).read_text())
        world = json.loads((PROJECT / 'scenario/world/world.json').read_text())
        cases = []
        for change in ('bad_kind', 'duplicate_metric', 'negative_cost', 'fake_stock', 'unknown_kit', 'missing_reload'):
            d, e = copy.deepcopy(data), copy.deepcopy(design)
            if change == 'bad_kind':
                next(x for x in e['effects'] if x['metric'] == 'firearm_reload_efficiency')['unlock']['kind'] = 'ability'
            elif change == 'duplicate_metric':
                e['effects'].append(next(x for x in e['effects'] if x['metric'] == 'firearm_reload_efficiency'))
            elif change == 'negative_cost':
                d['rules']['armsPerBattery'] = 0
            elif change == 'fake_stock':
                d['rules']['shipmentWaste'] = d['rules']['shipmentArms']
            elif change == 'unknown_kit':
                d['predicates']['bayonetEquipment'] = ['invented_socket_bayonet']
            elif change == 'missing_reload':
                d['predicates']['firearmReloadMillisByTemplate'] = {}
            cases.append((change, d, e))
        for change, d, e in cases:
            with self.subTest(change=change), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                (root / 'scenario/progression').mkdir(parents=True)
                (root / 'scenario/world').mkdir()
                (root / 'scenario/progression/land-army.json').write_text(json.dumps(d))
                (root / data['designSource']).write_text(json.dumps(e))
                (root / 'scenario/world/world.json').write_text(json.dumps(world))
                with self.assertRaises(ValueError):
                    land.build(root)

    def test_removing_real_socket_equipment_removes_bayonet_eligibility(self):
        roster = land.load_catalog()
        roster.archetypes['european_late_line_infantry']['equipmentIds'] = ['flintlock_musket']
        with patch.object(land, 'load_catalog', return_value=roster):
            p = next(p for p in land.build()['catalog']['profiles'] if p['id'] == 'european_late_line_infantry')
        self.assertTrue(p['firearm'])
        self.assertFalse(p['bayonet'])


    def test_mounted_or_siege_weapons_cannot_receive_infantry_reload(self):
        roster = land.load_catalog()
        for ident in ('sabre_cavalry', 'field_artillery_battery'):
            roster.archetypes[ident]['weaponIds'].append('arquebus')
            roster.archetypes[ident]['equipmentIds'] = ['matchlock_firearm']
        with patch.object(land, 'load_catalog', return_value=roster):
            profiles = {p['id']: p for p in land.build()['catalog']['profiles']}
        self.assertFalse(profiles['sabre_cavalry']['firearm'])
        self.assertFalse(profiles['field_artillery_battery']['firearm'])

    def test_generated_artifact_rejects_drift_even_with_rehashed_provenance(self):
        import package_wurst_map as maps
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            config = maps.load_config(PROJECT / 'package.json')
            maps.generate(config, output)
            maps.verify_generated(config, output)
            source = output / maps.GENERATED_WURST
            runtime_path = output / maps.GENERATED_DATA
            provenance_path = output / maps.PROVENANCE
            authored = source.read_text()
            runtime = json.loads(runtime_path.read_text())
            self.assertEqual(['milan', 'nuremberg', 'vienna'], runtime['landArmy']['arsenalIds'])
            payload = land.build()
            self.assertEqual(1, authored.count(payload['wurst']))
            identity = '"progression_arquebus_volley_drill", "firearm_reload_efficiency", 500'
            source.write_text(authored.replace(identity, identity.replace('500', '5000')))
            provenance = json.loads(provenance_path.read_text())
            provenance['outputs'][maps.GENERATED_WURST] = hashlib.sha256(source.read_bytes()).hexdigest()
            provenance_path.write_text(json.dumps(provenance))
            with self.assertRaisesRegex(maps.PackagingError, 'land army bindings'):
                maps.verify_generated(config, output)


if __name__ == '__main__':
    unittest.main()
