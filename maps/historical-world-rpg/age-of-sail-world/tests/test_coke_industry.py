"""Paid mineral fuel chain, compatible retrofits, conservation and migrations."""
import copy
from datetime import date
import unittest
from test_industry import Fixture, DAY, CATALOG, REFINE, IndustryGenerationTests

MINERAL = 'mineral_iron_refining:stockholm'
MINE = 'coal_extraction:bristol'
COKER = 'coke_preparation:bristol'


def fixture(coke=False, blast=False, owner='england', catalog=None):
    f = Fixture(owner=owner, catalog=catalog)
    f.complete('experimental_method')
    if coke:
        f.complete('coke_smelted_iron')
    if blast:
        f.complete('blast_furnace_practice')
    f.runtime.reconcile()
    return f


class CokeIndustryTests(unittest.TestCase):
    def test_isolated_research_106_control_100_and_independent_blast_113(self):
        for owner in ('england', 'france'):
            for coke, blast, output in ((False, False, 100), (True, False, 106), (False, True, 107), (True, True, 113)):
                f = fixture(coke, blast, owner)
                f.equip(MINERAL)
                before = copy.deepcopy(f.economy)
                f.start(MINERAL)
                for at in range(91, 101):
                    f.runtime.advance(DAY + at)
                    f.runtime.advance(DAY + at)  # replay is inert
                city = f.economy['cities']['stockholm']
                self.assertEqual(100000 + output, city['stock']['iron_goods'])
                self.assertEqual(99800, city['stock']['iron'])
                self.assertEqual(99950, city['stock']['coke'])
                self.assertEqual(99980, city['stock']['timber'])  # setup only
                self.assertEqual(99988, city['stock']['tools'])
                self.assertEqual(before['treasury'][owner] - 30, f.economy['treasury'][owner])
                self.assertEqual(0, f.runtime.states[MINERAL].yield_remainder)
                self.assertEqual(700 if blast else 0, f.runtime.rate(owner, 'iron_refining_yield', 1778, 'timber'))

    def test_paid_extraction_processing_and_delivery_conserve_fuel_and_never_create_cash(self):
        f = fixture(True)
        f.complete('deep_mine_drainage')
        f.runtime.reconcile()
        for city in f.economy['cities'].values():
            city['stock']['coal'] = city['stock']['coke'] = 0
        for ident in (MINE, COKER, MINERAL):
            self.assertTrue(f.runtime.action(f.owner, ident, 'equip', DAY))
        f.runtime.advance(DAY + 90)
        before = copy.deepcopy(f.economy)
        f.start(MINE)
        f.runtime.advance(DAY + 100)
        self.assertEqual(100, f.stock(MINE, 'coal'))
        self.assertEqual(100, f.runtime.states[MINE].extracted_units)
        f.start(COKER, DAY + 100)
        self.assertEqual(0, f.stock(MINE, 'coal'))
        f.runtime.advance(DAY + 110)
        self.assertEqual(50, f.stock(COKER, 'coke'))
        # A delivery moves the produced units, including into empty import markets.
        f.economy['cities']['bristol']['stock']['coke'] -= 50
        f.economy['cities']['stockholm']['warehouse'] = {'coke': 50}
        f.start(MINERAL, DAY + 110)
        f.runtime.advance(DAY + 120)
        self.assertEqual(0, f.economy['cities']['stockholm']['warehouse']['coke'])
        self.assertEqual(0, sum(c['stock']['coke'] for c in f.economy['cities'].values()))
        self.assertEqual(100113, f.stock(MINERAL, 'iron_goods'))
        self.assertEqual(before['treasury'][f.owner] - 90, f.economy['treasury'][f.owner])
        self.assertEqual(before['cities']['stockholm']['stock']['iron'] - 200, f.stock(MINERAL, 'iron'))
        for sid in ('bristol', 'stockholm'):
            self.assertLess(f.economy['cities'][sid]['stock']['tools'], before['cities'][sid]['stock']['tools'])

    def test_retrofit_and_operating_rejections_are_atomic(self):
        for mutation in ('ore', 'coke', 'tools', 'money', 'technology', 'admin', 'legal', 'warehouse', 'blockade'):
            f = fixture(True)
            f.equip(MINERAL)
            city = f.economy['cities']['stockholm']
            if mutation in ('ore', 'coke', 'tools'): city['stock'][{'ore': 'iron'}.get(mutation, mutation)] = 0
            if mutation == 'money': f.economy['treasury'][f.owner] = 0
            if mutation == 'technology': f.research.research[f.owner]['completed'].remove('experimental_method')
            if mutation == 'admin': city['administered'] = False
            if mutation == 'legal': city['legal'] = False
            if mutation == 'warehouse': city['warehouse_service'] = False
            if mutation == 'blockade': city['blocked'].add('coke')
            before = copy.deepcopy(f.economy), f.runtime.snapshot()
            self.assertFalse(f.runtime.action(f.owner, MINERAL, 'start', DAY + 90), mutation)
            self.assertEqual(before, (f.economy, f.runtime.snapshot()))
        for good in ('tools', 'timber', 'workers', 'money'):
            f = fixture(True)
            city = f.economy['cities']['stockholm']
            if good in ('tools', 'timber'): city['stock'][good] = 0
            if good == 'workers': city['manpower'] = 9
            if good == 'money': f.economy['treasury'][f.owner] = 119
            before = copy.deepcopy(f.economy)
            self.assertFalse(f.runtime.action(f.owner, MINERAL, 'equip', DAY))
            self.assertEqual(before, f.economy)
        f = fixture(True)
        f.equip(REFINE)
        self.assertFalse(f.runtime.action(f.owner, MINERAL, 'start', DAY + 90))
        self.assertFalse(f.runtime.action(f.owner, 'coal_extraction:stockholm', 'equip', DAY))
        self.assertFalse(f.runtime.action(f.owner, MINERAL, 'equip', date(1709, 1, 1).toordinal()))

    def test_fractional_batches_survive_resume_full_storage_and_funding_without_replay(self):
        catalog = copy.deepcopy(CATALOG)
        next(s for s in catalog['sites'] if s['id'] == MINERAL)['outputUnits'] = 99
        f = fixture(True, catalog=catalog)
        f.equip(MINERAL)
        for batch in range(20):
            day = DAY + 90 + 10 * batch
            f.start(MINERAL, day)
            f.runtime.advance(day + 5)
            saved = f.runtime.snapshot()
            f.runtime.restore(saved, day + 5)
            f.runtime.advance(day + 10)
        self.assertEqual(100000 + 20 * 99 + (20 * 99 * 600 // 10000), f.stock(MINERAL, 'iron_goods'))
        self.assertEqual(8000, f.runtime.states[MINERAL].yield_remainder)
        f.start(MINERAL, DAY + 290)
        city = f.economy['cities']['stockholm']
        city['supply'] = 0
        f.runtime.advance(DAY + 300)
        self.assertEqual(0, f.runtime.states[MINERAL].work)
        city['supply'] = 20
        f.runtime.advance(DAY + 309)
        city['capacity'] = city['stock']['iron_goods']
        before = city['supply'], city['stock']['iron_goods'], f.runtime.states[MINERAL].yield_remainder
        f.runtime.advance(DAY + 320)
        self.assertEqual(before, (city['supply'], city['stock']['iron_goods'], f.runtime.states[MINERAL].yield_remainder))
        city['capacity'] += 200
        f.runtime.advance(DAY + 321)
        self.assertEqual(before[1] + 105, city['stock']['iron_goods'])
        self.assertEqual(7400, f.runtime.states[MINERAL].yield_remainder)

    def test_capture_cancellation_legacy_and_failed_restore_never_grant_fuel_or_retrofit(self):
        f = fixture(True)
        f.equip(MINERAL); f.start(MINERAL)
        f.runtime.advance(DAY + 95)
        before = copy.deepcopy(f.economy)
        self.assertTrue(f.runtime.action(f.owner, MINERAL, 'stop', DAY + 95))
        self.assertEqual(before, f.economy)
        f.start(MINERAL, DAY + 95)
        f.runtime.transfer('stockholm', 'france', DAY + 95)
        self.assertEqual('france', f.runtime.states[MINERAL].equipment_owner)
        self.assertFalse(f.runtime.action('france', MINERAL, 'start', DAY + 95))
        f.runtime.advance(DAY + 120)
        self.assertEqual(100000, f.stock(MINERAL, 'iron_goods'))
        before = f.runtime.snapshot()
        for field, value in [('yield_remainder', 10000), ('extracted_units', 1), ('owner', 'forged')]:
            bad = copy.deepcopy(before); bad['states'][MINERAL][field] = value
            with self.assertRaises(ValueError): f.runtime.restore(bad, DAY + 120)
            self.assertEqual(before, f.runtime.snapshot())
        legacy = dict(schemaVersion=1, states={i: {k: v for k, v in raw.items() if k not in ('yield_remainder', 'extracted_units')}
                     for i, raw in before['states'].items() if f.runtime.sites[i]['recordVersion'] == 1})
        economy = copy.deepcopy(f.economy)
        f.runtime.restore(legacy, DAY + 120)
        self.assertFalse(f.runtime.states[MINERAL].equipment_owner)
        self.assertFalse(f.runtime.states[COKER].owner)
        self.assertEqual(economy, f.economy)

    def test_deposit_exhaustion_and_feedstock_bound_even_with_excessive_rates(self):
        f = fixture(True, True)
        f.complete('deep_mine_drainage')
        self.assertTrue(f.runtime.action(f.owner, MINE, 'equip', DAY))
        f.equip(MINERAL)
        f.runtime.states[MINE].extracted_units = f.runtime.sites[MINE]['depositUnits']
        before = copy.deepcopy(f.economy)
        self.assertFalse(f.runtime.action(f.owner, MINE, 'start', DAY + 90))
        self.assertEqual(before, f.economy)
        f.runtime.sites[MINERAL]['outputUnits'] = 199
        f.start(MINERAL)
        f.runtime.advance(DAY + 100)
        self.assertEqual(100200, f.stock(MINERAL, 'iron_goods'))
        self.assertEqual(0, f.runtime.states[MINERAL].yield_remainder)

    def test_two_hundred_combined_batches_remain_bounded_by_paid_feedstock(self):
        f = fixture(True, True)
        f.equip(MINERAL)
        before = copy.deepcopy(f.economy)
        for batch in range(200):
            at = DAY + 90 + batch * 10
            f.start(MINERAL, at)
            f.runtime.advance(at + 10)
            f.runtime.advance(at + 10)
        city = f.economy['cities']['stockholm']
        self.assertEqual(122600, city['stock']['iron_goods'])
        self.assertEqual(60000, city['stock']['iron'])
        self.assertEqual(90000, city['stock']['coke'])
        self.assertEqual(before['treasury'][f.owner] - 6000, f.economy['treasury'][f.owner])
        city['stock']['iron'] = 0
        frozen = copy.deepcopy(f.economy)
        self.assertFalse(f.runtime.action(f.owner, MINERAL, 'start', DAY + 2090))
        f.runtime.advance(DAY + 10000)
        self.assertEqual(frozen, f.economy)

    def test_generation_rejects_unsupported_geography_fuel_and_processing(self):
        helper = IndustryGenerationTests()
        for change in (lambda d: d['recipes'][3].update(settlementIds=['stockholm']),
                       lambda d: d['evidence'][0].update(bounds=[0, 0, 1, 1]),
                       lambda d: d['recipes'][4].update(inputGood='timber'),
                       lambda d: d['recipes'][2].update(fuelGood='timber'),
                       lambda d: d['recipes'][2].update(firstYear=1709)):
            with self.assertRaises(ValueError): helper.mutation(change)
        def free_import(d):
            next(s for s in d['settlements'] if s['id'] == 'bristol')['importRefs'] = ['coal']
        with self.assertRaises(ValueError): helper.mutation(free_import, 'scenario/settlements/europe-1450.json')
        def free_default(d): d['regionalDefaults']['europe']['tradeGoodIds'].append('coke')
        with self.assertRaises(ValueError): helper.mutation(free_default, 'scenario/economy/global-goods.json')


if __name__ == '__main__': unittest.main()
