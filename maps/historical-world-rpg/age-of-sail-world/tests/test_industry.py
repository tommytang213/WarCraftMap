"""Industry production headless scenarios and generated live-contract guards."""
import copy
from datetime import date
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

PROJECT = Path(__file__).resolve().parents[1]
SHARED = PROJECT.parent / '_shared'
sys.path[:0] = [str(PROJECT / 'tooling'), str(SHARED / 'engine'), str(SHARED / 'tooling')]
from industry_catalog import build
from industry import IndustryRuntime
from technology_institutions import TechnologyInstitutionRuntime

WORLD = json.loads((PROJECT / 'scenario/world/world.json').read_text())
CATALOG = build()['catalog']
DAY = date(1778, 1, 1).toordinal()
REFINE = 'iron_refining:stockholm'
BARREL = 'gun_barrels:milan'


class Fixture:
    def __init__(self, treatment=False, owner='england', world=None, catalog=None):
        self.owner = owner
        self.research = TechnologyInstitutionRuntime(world or WORLD, '1778-01-01')
        goods = {g for s in CATALOG['sites'] for g in (s['inputGood'], s['outputGood'], 'timber', 'tools')}
        self.economy = dict(treasury={p: 1000000 for p in self.research.polity_ids}, cities={
            s['settlementId']: dict(owner=owner, legal=True, administered=True, accessible=True,
                                   manpower=1000, supply=100000, warehouse_service=True, stock={g: 100000 for g in goods},
                                   blocked=set(), capacity=2147483647)
            for s in CATALOG['sites']})
        for node in ('water_powered_machinery', 'cast_cannon'):
            self.complete(node)
        if treatment:
            self.complete('boring_mills')
        self.runtime = IndustryRuntime(catalog or CATALOG, self.research, self.economy)

    def complete(self, node):
        if node not in self.research.completed(self.owner):
            for prerequisite in self.research.nodes[node]['prerequisiteIds']:
                self.complete(prerequisite)
            self.research.advance_research(self.owner, node, 1000000, '1778-01-01')

    def equip(self, ident):
        assert self.runtime.action(self.owner, ident, 'equip', DAY)
        self.runtime.advance(DAY + 90)

    def start(self, ident, day=DAY + 90):
        assert self.runtime.action(self.owner, ident, 'start', day)

    def stock(self, ident, good):
        return self.economy['cities'][self.runtime.sites[ident]['settlementId']]['stock'][good]


class IndustryProductionTests(unittest.TestCase):
    def test_exact_approved_rates_recipient_sites_and_no_generated_assets(self):
        payload = build()
        self.assertEqual({'iron_refining_yield': 700, 'gun_barrel_production_throughput': 600},
                         {e['metric']: e['bonusBasisPoints'] for e in payload['catalog']['effects']})
        self.assertEqual({'stockholm', 'milan', 'vienna', 'nuremberg', 'liaoyang'},
                         {s['settlementId'] for s in payload['catalog']['sites']})
        self.assertNotIn('.unlock(', payload['wurst'])
        self.assertNotIn('new RuntimeForce', payload['wurst'])
        self.assertIn(', 0, 0, ', payload['wurst'])  # missing markets have no goods/cash
        self.assertEqual(payload, build())

    def test_refining_changes_real_output_107_vs_100_for_identical_feedstock(self):
        for treatment, expected in ((False, 100), (True, 107)):
            f = Fixture(treatment)
            f.equip(REFINE)
            before = copy.deepcopy(f.economy)
            f.start(REFINE)
            self.assertFalse(f.runtime.action(f.owner, REFINE, 'start', DAY + 90))
            f.runtime.advance(DAY + 99)
            self.assertEqual(100000, f.stock(REFINE, 'iron_goods'))
            f.runtime.advance(DAY + 100)
            self.assertEqual(100000 + expected, f.stock(REFINE, 'iron_goods'))
            self.assertEqual(99800, f.stock(REFINE, 'iron'))
            self.assertEqual(100000 - 20 - 50, f.stock(REFINE, 'timber'))
            self.assertEqual(100000 - 10 - 2, f.stock(REFINE, 'tools'))
            self.assertEqual(before['treasury'][f.owner] - 20 - 10, f.economy['treasury'][f.owner])
            f.runtime.advance(DAY + 10000)
            self.assertEqual(100000 + expected, f.stock(REFINE, 'iron_goods'))

    def test_barrel_throughput_completes_in_95_vs_100_paid_days_with_same_materials(self):
        for owner in ('england', 'france'):  # player and other governments share rules
            control, treatment = Fixture(owner=owner), Fixture(True, owner)
            for f in (control, treatment):
                f.equip(BARREL)
                f.start(BARREL)
                f.runtime.advance(DAY + 184)
                self.assertEqual(100000, f.stock(BARREL, 'arms'))
                self.assertEqual(99900, f.stock(BARREL, 'iron_goods'))
            treatment.runtime.advance(DAY + 185)
            control.runtime.advance(DAY + 185)
            self.assertEqual(100030, treatment.stock(BARREL, 'arms'))
            self.assertEqual(100000, control.stock(BARREL, 'arms'))
            control.runtime.advance(DAY + 190)
            self.assertEqual(100030, control.stock(BARREL, 'arms'))
            self.assertEqual(5, treatment.economy['treasury'][owner] - control.economy['treasury'][owner])

    def test_rejections_are_atomic_for_unknown_site_wrong_owner_no_gear_or_resources(self):
        for mutation in ('wrong_owner', 'inaccessible', 'illegal', 'no_admin', 'no_tech',
                         'no_money', 'no_tools', 'no_fuel', 'no_workers', 'blocked', 'no_warehouse'):
            with self.subTest(mutation=mutation):
                f = Fixture(True)
                city = f.economy['cities']['stockholm']
                if mutation == 'wrong_owner': city['owner'] = 'france'
                if mutation == 'inaccessible': city['accessible'] = False
                if mutation == 'illegal': city['legal'] = False
                if mutation == 'no_admin': city['administered'] = False
                if mutation == 'no_warehouse': city['warehouse_service'] = False
                if mutation == 'no_tech': f.research.research[f.owner]['completed'].clear()
                if mutation == 'no_money': f.economy['treasury'][f.owner] = 0
                if mutation == 'no_tools': city['stock']['tools'] = 0
                if mutation == 'no_fuel': city['stock']['timber'] = 0
                if mutation == 'no_workers': city['manpower'] = 0
                if mutation == 'blocked': city['blocked'].add('tools')
                before = copy.deepcopy(f.economy), f.runtime.snapshot()
                self.assertFalse(f.runtime.action(f.owner, REFINE, 'equip', DAY))
                self.assertEqual(before, (f.economy, f.runtime.snapshot()))
        f = Fixture(True)
        before = copy.deepcopy(f.economy)
        self.assertFalse(f.runtime.action(f.owner, 'unknown', 'equip', DAY))
        self.assertFalse(f.runtime.action(f.owner, REFINE, 'start', DAY))
        f.equip(REFINE)
        f.economy['cities']['stockholm']['stock']['iron'] = 0
        after_setup = copy.deepcopy(f.economy)
        self.assertFalse(f.runtime.action(f.owner, REFINE, 'start', DAY + 90))
        self.assertEqual(after_setup, f.economy)
        self.assertNotEqual(before, after_setup)

    def test_missing_daily_labor_and_full_or_blocked_output_never_create_or_replay_work(self):
        f = Fixture(True)
        f.equip(REFINE)
        f.start(REFINE)
        city = f.economy['cities']['stockholm']
        city['supply'] = 0
        f.runtime.advance(DAY + 120)
        self.assertEqual(0, f.runtime.states[REFINE].work)
        city['supply'] = 100
        f.runtime.advance(DAY + 129)
        city['capacity'] = 100000
        f.runtime.advance(DAY + 140)
        self.assertEqual(9000000, f.runtime.states[REFINE].work)
        self.assertEqual(91, city['supply'])
        city['capacity'] = 2147483647
        f.runtime.advance(DAY + 141)
        self.assertEqual(100107, f.stock(REFINE, 'iron_goods'))

    def test_delivered_warehouse_materials_can_supply_zero_liquidity_import_markets(self):
        f = Fixture(True)
        city = f.economy['cities']['stockholm']
        city['stock'] = {g: 0 for g in city['stock']}
        city['warehouse'] = {'timber': 70, 'tools': 12, 'iron': 200}
        f.equip(REFINE)
        self.assertEqual(50, city['warehouse']['timber'])
        f.start(REFINE)
        self.assertEqual(0, city['warehouse']['timber'])
        f.runtime.advance(DAY + 100)
        self.assertEqual(107, f.stock(REFINE, 'iron_goods'))

    def test_era_and_current_controller_gate_passives_even_with_future_completion(self):
        f = Fixture(True)
        for metric, year in [('iron_refining_yield', 1500), ('gun_barrel_production_throughput', 1750)]:
            self.assertEqual(0, f.runtime.rate(f.owner, metric, year - 1))
            self.assertGreater(f.runtime.rate(f.owner, metric, year), 0)
            self.assertEqual(0, f.runtime.rate('france', metric, 1778))
        before = copy.deepcopy(f.economy)
        self.assertFalse(f.runtime.action(f.owner, REFINE, 'equip', date(1449, 1, 1).toordinal()))
        self.assertEqual(before, f.economy)

    def test_fixed_point_yield_vectors_floor_and_unsupported_runtime_access_cancels(self):
        for output, expected in ((1, 1), (99, 105), (101, 108), (197, 210)):
            catalog = copy.deepcopy(CATALOG)
            site = next(s for s in catalog['sites'] if s['id'] == REFINE)
            site['outputUnits'] = output
            f = Fixture(True, catalog=catalog)
            f.equip(REFINE); f.start(REFINE)
            f.runtime.advance(DAY + 100)
            self.assertEqual(100000 + expected, f.stock(REFINE, 'iron_goods'))
        f = Fixture(True); f.equip(BARREL); f.start(BARREL)
        f.economy['cities']['milan']['blocked'].add('iron_goods')
        f.runtime.advance(DAY + 95)
        self.assertFalse(f.runtime.states[BARREL].owner)
        self.assertEqual(100000, f.stock(BARREL, 'arms'))

    def test_duplicate_sources_and_named_layer_repair_never_stack_or_produce(self):
        world = copy.deepcopy(WORLD)
        source = copy.deepcopy(next(n for n in world['technologies'] if n['id'] == 'blast_furnace_practice'))
        source.update(id='duplicate_source', prerequisiteIds=[])
        world['technologies'].append(source)
        f = Fixture(True, world=world)
        f.complete('duplicate_source')
        f.runtime.reconcile()
        f.runtime.layers[f.owner].clear()
        self.assertEqual(0, f.runtime.rate(f.owner, 'iron_refining_yield', 1778))
        before = copy.deepcopy(f.economy)
        for _ in range(20): f.runtime.reconcile()
        self.assertEqual(700, f.runtime.rate(f.owner, 'iron_refining_yield', 1778))
        self.assertEqual(before, f.economy)

    def test_save_resume_failed_restore_capture_and_legacy_preserve_durable_authority(self):
        f = Fixture(True)
        f.equip(BARREL)
        f.start(BARREL)
        f.runtime.advance(DAY + 133)
        checkpoint = f.runtime.snapshot(), copy.deepcopy(f.economy), f.research.snapshot()
        f.runtime.advance(DAY + 185)
        expected = f.runtime.snapshot(), copy.deepcopy(f.economy)
        resumed = Fixture(True)
        resumed.research.restore(checkpoint[2])
        resumed.economy.clear(); resumed.economy.update(copy.deepcopy(checkpoint[1]))
        resumed.runtime.restore(checkpoint[0], DAY + 133)
        for day in range(DAY + 134, DAY + 186): resumed.runtime.advance(day)
        self.assertEqual(expected, (resumed.runtime.snapshot(), resumed.economy))
        before = resumed.runtime.snapshot(), copy.deepcopy(resumed.economy)
        bad = copy.deepcopy(checkpoint[0]); bad['states'][BARREL]['work'] = -1
        with self.assertRaises(ValueError): resumed.runtime.restore(bad, DAY + 133)
        self.assertEqual(before, (resumed.runtime.snapshot(), resumed.economy))
        resumed.start(BARREL, DAY + 185)
        resumed.runtime.transfer('milan', 'france', DAY + 185)
        self.assertEqual('france', resumed.runtime.states[BARREL].equipment_owner)
        self.assertFalse(resumed.runtime.states[BARREL].owner)
        resumed.runtime.advance(DAY + 500)
        self.assertEqual(100030, resumed.stock(BARREL, 'arms'))
        resumed.runtime.restore(None, DAY + 500)
        self.assertFalse(resumed.runtime.states[BARREL].equipment_owner)
        g = Fixture(True); g.runtime.action(g.owner, REFINE, 'equip', DAY)
        g.runtime.transfer('stockholm', 'france', DAY + 89)
        self.assertFalse(g.runtime.states[REFINE].equipment_owner)

    def test_long_campaign_is_bounded_by_paid_feedstock_and_never_multiplies_wealth(self):
        f = Fixture(True)
        f.equip(REFINE)
        before = copy.deepcopy(f.economy)
        for batch in range(200):
            day = DAY + 90 + batch * 10
            f.start(REFINE, day)
            f.runtime.advance(day + 10)
        city = f.economy['cities']['stockholm']
        self.assertEqual(100000 + 200 * 107, city['stock']['iron_goods'])
        self.assertEqual(100000 - 200 * 200, city['stock']['iron'])
        self.assertEqual(before['treasury'][f.owner] - 200 * 30, f.economy['treasury'][f.owner])
        city['stock']['iron'] = 0
        before = copy.deepcopy(f.economy)
        self.assertFalse(f.runtime.action(f.owner, REFINE, 'start', DAY + 2090))
        f.runtime.advance(DAY + 20000)
        self.assertEqual(before, f.economy)


class IndustryGenerationTests(unittest.TestCase):
    def mutation(self, change, relative='scenario/progression/industry.json'):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for folder in ('scenario/progression', 'scenario/economy', 'scenario/settlements', 'scenario/world'):
                shutil.copytree(PROJECT / folder, root / folder)
            data = json.loads((root / relative).read_text()); change(data)
            (root / relative).write_text(json.dumps(data))
            return build(root)

    def test_invalid_costs_materials_recipients_and_bindings_fail_closed(self):
        changes = [lambda d: d['setup'].update(workers=0), lambda d: d['daily'].update(money=True),
                   lambda d: d['recipes'][0].update(inputGood='invented_ore'),
                   lambda d: d['recipes'][0].update(outputGood='iron'),
                   lambda d: d['recipes'][0].update(outputUnits=200),
                   lambda d: d['recipes'][0].update(prerequisite='unknown'),
                   lambda d: d['recipes'][1].update(metric='iron_refining_yield')]
        for change in changes:
            with self.subTest(change=change), self.assertRaises(ValueError): self.mutation(change)
        def wrong_unlock(d):
            next(e for e in d['effects'] if e['metric'] == 'iron_refining_yield')['unlock']['kind'] = 'ability'
        with self.assertRaises(ValueError): self.mutation(wrong_unlock, 'scenario/progression/gameplay-effect-design.json')

    def test_absent_local_warehouse_infrastructure_removes_facility(self):
        def remove(d):
            next(s for s in d['settlements'] if s['id'] == 'stockholm')['services'].remove('warehouse')
        changed = self.mutation(remove, 'scenario/settlements/europe-1450.json')
        self.assertNotIn(REFINE, {s['id'] for s in changed['catalog']['sites']})

    def test_release_findings_require_current_executed_production_evidence(self):
        import release_blocker_audit as audit
        self.assertEqual(set(), audit._verified_industry_bindings())
        self.assertEqual(set(), audit._verified_industry_bindings({}, b'', 'a' * 40))
        comparative = 'wurst/IndustryTests.wurst:industryRegisteredResearchAndPaidActionsProduceExactYieldAndFasterBarrelsAgainstControl'
        # Synthetic protocol checks only; never written as release evidence.
        for coverage, closes in [({}, False), ({'industry': ['grant_only']}, False),
                                 ({'industry': [comparative]}, True)]:
            with patch.object(audit.runtime_acceptance, 'verify_execution_coverage', return_value=coverage):
                self.assertEqual(closes, bool(audit._verified_industry_bindings({}, b'', 'a' * 40)))

    def test_scenario_cost_and_rate_changes_reach_the_live_definitions(self):
        changed = self.mutation(lambda d: d['setup'].update(money=155))
        self.assertIn('ledger.setupMoney = 155', changed['wurst'])
        def bonus(d): next(e for e in d['effects'] if e['metric'] == 'iron_refining_yield').update(bonusBasisPoints=750)
        self.assertIn('"iron_refining_yield", 750', self.mutation(bonus, 'scenario/progression/gameplay-effect-design.json')['wurst'])
        def remove(d):
            next(s for s in d['settlements'] if s['id'] == 'stockholm')['productionRefs'] = []
        changed = self.mutation(remove, 'scenario/settlements/europe-1450.json')
        self.assertNotIn(REFINE, {s['id'] for s in changed['catalog']['sites']})

    def test_packaging_verifies_executable_contract_even_with_rehashed_provenance(self):
        import package_wurst_map as maps
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            config = maps.load_config(PROJECT / 'package.json')
            maps.generate(config, output)
            maps.verify_generated(config, output)
            source = output / maps.GENERATED_WURST
            self.assertEqual(1, source.read_text().count(build()['wurst']))
            source.write_text(source.read_text().replace('"iron_refining_yield", 700', '"iron_refining_yield", 7000'))
            provenance = output / maps.PROVENANCE
            data = json.loads(provenance.read_text())
            data['outputs'][maps.GENERATED_WURST] = hashlib.sha256(source.read_bytes()).hexdigest()
            provenance.write_text(json.dumps(data))
            with self.assertRaisesRegex(maps.PackagingError, 'industry bindings'): maps.verify_generated(config, output)


if __name__ == '__main__':
    unittest.main()
