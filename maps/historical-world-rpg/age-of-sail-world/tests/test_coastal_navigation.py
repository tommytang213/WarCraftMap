"""Exact arithmetic and detached migration; paid production gates run in Wurst."""
import copy
import json
from pathlib import Path
import sys
import unittest

PROJECT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(PROJECT / 'tooling'), str(PROJECT.parent / '_shared/engine')]
from navigation_efficiency import build, consumers, wurst
from voyage_navigation import VoyageCatalog, VoyageError

SHIP = 'english_patrol_ship'
ROUTE = 'channel_position_finding_circuit'


class CoastalNavigationTests(unittest.TestCase):
    def setUp(self):
        self.catalog, self.world = build()

    def run_voyages(self, qualified, split=False):
        state = self.catalog.empty()
        supply = 1000
        for i in range(5):
            supply = self.catalog.start(SHIP, state, ROUTE, i * 10, supply)
            if split:
                for day in range(i * 10 + 1, i * 10 + 11):
                    supply += self.catalog.resolve(state, day, qualified)
                    supply += self.catalog.resolve(state, day, qualified)
            else:
                supply += self.catalog.resolve(state, (i + 1) * 10, qualified)
            state = self.catalog.validate({'schemaVersion': 2, 'ships': {SHIP: state}})['ships'][SHIP]
        return supply, state

    def test_exact_coastal_and_combined_sources_charge_one_common_overhead_bucket(self):
        for sources, expected in [([], 750), (['coastal_triangulation'], 758),
                                  (['celestial_navigation'], 760),
                                  (['celestial_navigation', 'coastal_triangulation'], 768),
                                  (['coastal_triangulation'] * 3, 758)]:
            with self.subTest(sources=sources):
                supply, state = self.run_voyages(sources)
                self.assertEqual(expected, supply)
                self.assertEqual(0, state['creditBasisPoints'])
                self.assertEqual((supply, state), self.run_voyages(sources, split=True))

    def test_fractional_source_attribution_and_shared_refund_resume_exactly(self):
        state = self.catalog.empty()
        self.catalog.start(SHIP, state, ROUTE, 0, 1000)
        self.assertEqual(1, self.catalog.resolve(state, 3, self.catalog.sources))
        self.assertEqual({'celestial_navigation': 6000, 'coastal_triangulation': 4800}, state['sourceCredits'])
        self.assertEqual(800, state['creditBasisPoints'])
        state = self.catalog.validate({'schemaVersion': 2, 'ships': {SHIP: state}})['ships'][SHIP]
        self.assertEqual(2, self.catalog.resolve(state, 10, self.catalog.sources))
        self.assertEqual(6000, state['creditBasisPoints'])
        self.assertEqual(0, self.catalog.resolve(state, 10, self.catalog.sources))

    def test_mixed_and_open_ocean_days_have_no_coastal_contribution(self):
        for mask, expected in [([False] * 10, (0, 0)), ([True] + [False] * 9, (0, 1600)),
                               ([True] * 5 + [False] * 5, (0, 8000))]:
            self.catalog.routes[ROUTE]['coastalBearingDays'] = mask
            state = self.catalog.empty(); self.catalog.start(SHIP, state, ROUTE, 0, 70)
            released = self.catalog.resolve(state, 10, ['coastal_triangulation'])
            self.assertEqual(expected, (released, state['creditBasisPoints']))

    def test_interruption_returns_only_unused_provisions_and_keeps_fraction(self):
        state = self.catalog.empty(); supply = self.catalog.start(SHIP, state, ROUTE, 0, 70)
        supply += self.catalog.resolve(state, 3, ['coastal_triangulation'])
        supply += self.catalog.interrupt(state)
        self.assertEqual(55, supply)
        self.assertEqual(4800, state['creditBasisPoints'])
        self.assertEqual(0, self.catalog.interrupt(state))
        self.assertEqual(0, self.catalog.resolve(state, 100, ['coastal_triangulation']))
        with self.assertRaises(VoyageError): self.catalog.start(SHIP, state, ROUTE, 3, 49)

    def test_legacy_v1_retains_celestial_equipment_pending_voyage_and_credit(self):
        old = dict(equipment=True, routeId=ROUTE, elapsedDays=3, lastDay=3, reserved=35, creditBasisPoints=6000)
        saved = {'schemaVersion': 1, 'ships': {SHIP: old}}
        before = copy.deepcopy(saved)
        migrated = self.catalog.validate(saved)
        self.assertEqual(before, saved)
        state = migrated['ships'][SHIP]
        self.assertEqual(old, {k: state[k] for k in old})
        self.assertEqual({'celestial_navigation': 6000, 'coastal_triangulation': 0}, state['sourceCredits'])
        self.assertNotIn('equipmentOwner', state)

    def test_missing_unknown_or_inconsistent_source_accounting_rejects(self):
        saved = self.catalog.initial_state()
        for mutation in [lambda s: s.pop('coastal_triangulation'),
                         lambda s: s.update(foreign=0),
                         lambda s: s.update(coastal_triangulation=1),
                         lambda s: s.update(coastal_triangulation=10000),
                         lambda s: s.update(coastal_triangulation=True)]:
            invalid = copy.deepcopy(saved); mutation(invalid['ships'][SHIP]['sourceCredits'])
            with self.assertRaises(VoyageError): self.catalog.validate(invalid)

    def test_catalog_requires_explicit_bearing_days_and_unique_typed_sources(self):
        for mutation in [lambda d: d['sources'].append(d['sources'][1]),
                         lambda d: d['sources'][1].update(id='coastal_copy', entitlement=d['sources'][0]['entitlement']),
                         lambda d: d['routes'][0].update(coastalBearingDays=[True]),
                         lambda d: d['routes'][0].update(coastalBearings=''),
                         lambda d: d['ships'][0].pop('coastalBearingCapable')]:
            data = copy.deepcopy(self.catalog.data); mutation(data)
            with self.assertRaises(VoyageError): VoyageCatalog(data, self.world)

    def test_metadata_identifies_exact_consumer_costs_and_generated_source(self):
        rows = consumers(self.catalog)
        coast = rows[1]
        self.assertEqual(('coastal_triangulation', 'modifier', 'progression_coastal_triangulation', 800),
                         (coast['nodeId'], coast['kind'], coast['contentId'], coast['reductionBasisPoints']))
        for text in ('120 treasury minor units', '2 cloth', '7 preparation days', 'shoreline', 'full undiscounted'):
            self.assertIn(text, coast['inspection'])
        self.assertIn('"coastal_triangulation", "modifier", "progression_coastal_triangulation", 800', wurst(self.catalog, self.world))
        node = next(n for n in self.world['technologies'] if n['id'] == 'coastal_triangulation')
        self.assertEqual(['pilot_books'], node['prerequisiteIds'])
        self.assertEqual((1480, 104), (node['timeCost']['preferredYear'], node['timeCost']['baseCost']))
