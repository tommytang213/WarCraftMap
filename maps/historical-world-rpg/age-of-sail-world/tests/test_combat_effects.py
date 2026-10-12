"""Executable damage contracts, catalogue completeness, and generation parity."""
import copy
from fractions import Fraction
import json
from pathlib import Path
import sys
import unittest

PROJECT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(PROJECT / 'tooling'), str(PROJECT.parent / '_shared/engine')]
from combat_effect_catalog import build, wurst, verify
from combat_effects import CombatCatalogue, CombatBindingError, CombatHit
from military_tradition import MilitaryTraditionRuntime, RecordingTraditionAdapter
from validate_unit_roster import load_catalog
from unit_roster import RosterProjection


class CombatEffectsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = build()
        cls.definitions = json.loads((PROJECT / 'scenario/military-traditions.json').read_text())
        cls.roster = load_catalog()

    def setUp(self):
        self.adapter = RecordingTraditionAdapter()
        self.runtime = MilitaryTraditionRuntime(self.definitions, self.adapter)

    def participant(self, xp, naval=False, controller='player', profile=None):
        category = 'sailing_naval' if naval else 'land_formation'
        state = self.runtime.snapshot()
        next(r for r in state['tracks'] if r['controllerId'] == controller and r['categoryId'] == category)['experience'] = xp
        self.runtime.restore(state)
        profile = profile or ('armed_sailing_warship' if naval else 'european_musket_battalion')
        return self.runtime.view(controller, category), profile, self.catalog.profiles[profile]['unitTypeId']

    def test_all_thresholds_and_unbounded_continuous_growth(self):
        for naval, thresholds, divisor in [(False, (1000, 3000), 10), (True, (1200, 3600), 8)]:
            for controller in ('player', 'england', 'france'):
                for xp in (0, 1, *(v+d for v in thresholds for d in (-1, 0, 1)), 2**31, 2**53+1, 10**100+1):
                    with self.subTest(naval=naval, controller=controller, xp=xp):
                        attacker = self.participant(xp, naval, controller)
                        hit = CombatHit(Fraction(100), 'naval_gunfire' if naval else 'firearm_volley')
                        bonus = 1000 if xp >= thresholds[1] else 500 if xp >= thresholds[0] else 0
                        expected = 100 * (1 + (Fraction(xp, divisor) + bonus)/10000)
                        actual = self.catalog.resolve(hit, attacker, (None, '', ''))
                        self.assertEqual(expected, actual)
                        self.assertEqual(actual, self.catalog.resolve(hit, attacker, (None, '', '')))
                        # Continuous unrelated attributes still grow exactly.
                        attribute = 'maneuver_basis_points' if naval else 'discipline_basis_points'
                        self.assertEqual(Fraction(xp, divisor * 2), attacker[0].modifiers[attribute])
                        self.assertLessEqual(len(attacker[0].effects), 1)

    def test_resistance_uses_rating_and_only_verified_incoming_gunfire(self):
        attacker = self.participant(3600, True, 'france')
        defender = self.participant(3600, True)
        hit = CombatHit(Fraction(7, 3), 'naval_gunfire')
        self.assertEqual(Fraction(1603, 618), self.catalog.resolve(hit, attacker, defender))
        # Gunfire from a controller with no tradition still meets resistance.
        self.assertEqual(Fraction(700, 309), self.catalog.resolve(CombatHit(Fraction(7, 3), 'naval_gunfire'), (None, *attacker[1:]), defender))
        for kind in ('boarding', 'ram', 'collision', 'cargo', 'repair', 'spell', 'unknown'):
            self.assertEqual(100, self.catalog.resolve(CombatHit(Fraction(100), kind), attacker, defender))
        transport = self.participant(3600, True, profile='coastal_transport')
        self.assertEqual(Fraction(229, 2), self.catalog.resolve(CombatHit(Fraction(100), 'naval_gunfire'), attacker, transport))

    def test_no_weapon_inference_or_hostility_bypass(self):
        for profile in ('pike_foot', 'english_longbow_retinue', 'sabre_cavalry', 'field_artillery_battery', 'field_engineers'):
            attacker = self.participant(999999, profile=profile)
            self.assertEqual(100, self.catalog.resolve(CombatHit(Fraction(100), 'firearm_volley'), attacker, (None, '', '')))
        attacker = self.participant(3000)
        for kwargs in ({'legal':False}, {'attack':False}):
            self.assertEqual(100, self.catalog.resolve(CombatHit(Fraction(100), 'firearm_volley'), attacker, (None, '', ''), **kwargs))
        for profile, rawcode in (('', 'hfoo'), ('unknown', 'hfoo'), (attacker[1], 'hrif')):
            self.assertEqual(100, self.catalog.resolve(CombatHit(Fraction(100), 'firearm_volley'), (attacker[0], profile, rawcode), (None, '', '')))

    def test_independent_named_sources_add_once_and_survive_replacement(self):
        for xp, expected in ((1000, 108), (3000, 115)):
            attacker = self.participant(xp)
            hit = CombatHit(Fraction(100), 'firearm_volley')
            self.assertEqual(expected, self.catalog.resolve(hit, attacker, (None, '', ''), other_sources={'research:fixture':{'damage':200}}))
        with self.assertRaises(CombatBindingError):
            self.catalog.resolve(CombatHit(Fraction(100), 'firearm_volley'), attacker, (None, '', ''), other_sources={'military_tradition:platoon_fire':{'damage':1000}})

    def test_restore_migration_transfer_and_rejected_load_keep_derived_damage(self):
        attacker = self.participant(3001)
        checkpoint = self.runtime.snapshot()
        expected = self.catalog.resolve(CombatHit(Fraction(100), 'firearm_volley'), attacker, (None, '', ''))
        for _ in range(3):
            self.runtime.restore(checkpoint)
            restored = self.runtime.view('player', 'land_formation'), *attacker[1:]
            self.assertEqual(expected, self.catalog.resolve(CombatHit(Fraction(100), 'firearm_volley'), restored, (None, '', '')))
        malformed = copy.deepcopy(checkpoint)
        malformed['tracks'][0]['experience'] = -1
        with self.assertRaises(ValueError):
            self.runtime.restore(malformed)
        self.assertEqual(checkpoint, self.runtime.snapshot())
        legacy = copy.deepcopy(checkpoint); legacy['schemaVersion'] = 1
        self.runtime.restore(legacy)
        self.assertEqual(expected, self.catalog.resolve(CombatHit(Fraction(100), 'firearm_volley'), (self.runtime.view('player', 'land_formation'), *attacker[1:]), (None, '', '')))
        self.assertNotIn('platoon_fire', json.dumps(checkpoint))
        self.assertEqual(100, self.catalog.resolve(CombatHit(Fraction(100), 'firearm_volley'), (self.runtime.view('france', 'land_formation'), *attacker[1:]), (None, '', '')))

    def test_every_binding_and_coefficient_matches_and_bad_metadata_blocks(self):
        data = self.catalog.data
        def remove(v): v['effects'].pop()
        def duplicate(v): v['effects'].append(v['effects'][0])
        def identity(v): v['effects'][0]['milestoneId'] = 'naval_practice_one'
        def coefficient(v): v['attributes'][0]['numerator'] = 0
        def missing_attribute(v): v['attributes'].pop()
        def weapon(v): v['attackPredicates'][0]['weaponIds'] = ['sword_invented']
        def ability(v): v['attackPredicates'][0]['abilityIds'] = ['unknown']
        def stat(v): v['effects'][0]['contributions'][0]['stat'] = 'armor'
        def source(v): v['effects'][1]['sourceId'] = v['effects'][0]['sourceId']
        def predicate(v): v['effects'][0]['contributions'][0]['attackId'] = 'unknown'
        def replaced(v): v['effects'][1]['replacesEffectId'] = 'disciplined_gunnery'
        def native_binding(v): v['attackPredicates'][0]['nativeTemplates'] = {}
        for mutation in (remove, duplicate, identity, coefficient, missing_attribute, weapon, ability, stat, source, predicate, replaced, native_binding):
            broken = copy.deepcopy(data); mutation(broken)
            with self.subTest(mutation=mutation.__name__), self.assertRaises(CombatBindingError):
                CombatCatalogue(broken, self.definitions, self.roster)
        source = wurst(self.catalog)
        verify(source, self.catalog)
        for mutated in (source.replace('"1000", "1", "1"', '"1500", "1", "1"'), source.replace('"firearm_volley"', '"sword"'), source+source):
            with self.assertRaises(ValueError):
                verify(mutated, self.catalog)

    def test_headless_roster_adapter_uses_current_authority_across_projection_and_restore(self):
        definitions = copy.deepcopy(self.definitions)
        definitions['unitAssignments'] = [dict(id='source', controllerId='player', categoryId='land_formation'),
                                           dict(id='target', controllerId='france', categoryId='land_formation')]
        traditions = MilitaryTraditionRuntime(definitions, RecordingTraditionAdapter())
        saved = traditions.snapshot()
        next(r for r in saved['tracks'] if r['controllerId'] == 'player' and r['categoryId'] == 'land_formation')['experience'] = 3000
        traditions.restore(saved)
        roster = RosterProjection(self.roster, [dict(id=ident, archetypeId='european_musket_battalion',
            representedStrength=100, regionId='map', active=True, morale=70, discipline=60, supply=50)
            for ident in ('source', 'target')])
        checkpoint = roster.snapshot()
        for region in ('map', 'inactive_map', 'map'):
            roster.project(region, 10)
            hit = CombatHit(Fraction(100), 'firearm_volley')
            self.assertEqual(113, self.catalog.resolve_roster_hit(hit, traditions, roster, 'source', 'target', lambda a,b:a != b))
            self.assertEqual(113, self.catalog.resolve_roster_hit(hit, traditions, roster, 'source', 'target', lambda a,b:a != b))
            traditions.restore(saved); roster.restore(checkpoint)
        traditions.change_unit('source', controller_id='england')
        self.assertEqual(100, self.catalog.resolve_roster_hit(CombatHit(Fraction(100), 'firearm_volley'), traditions, roster,
                         'source', 'target', lambda a,b:a != b))
        traditions.change_unit('source', controller_id='player')
        self.assertEqual(100, self.catalog.resolve_roster_hit(CombatHit(Fraction(100), 'firearm_volley'), traditions, roster,
                         'source', 'target', lambda a,b:False))


if __name__ == '__main__':
    unittest.main()
