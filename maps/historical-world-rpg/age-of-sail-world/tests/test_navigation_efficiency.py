import copy
import json
import hashlib
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent / '_shared/engine'))
sys.path.insert(0, str(ROOT.parent / '_shared/tooling'))
sys.path.insert(0, str(ROOT / 'tooling'))
from military import MilitaryRuntime, MilitaryError, MilitarySaveAdapter, RecordingMilitaryAdapter
from technology_institutions import TechnologyInstitutionRuntime, ResearchError
from voyage_navigation import VoyageCatalog, VoyageError
from navigation_efficiency import build, wurst
from package_wurst_map import generate, load_config, verify_generated, PackagingError

SHIP = 'english_patrol_ship'
ROUTE = 'channel_position_finding_circuit'


class Fixture:
    def __init__(self, researched=True, equipment=True, active=True):
        self.catalog, self.world = build()
        self.research = TechnologyInstitutionRuntime(self.world, '1500-01-01')
        if researched:
            for node in ('oceanic_seamanship', 'celestial_navigation'):
                self.research.advance_research('england', node, 100000, '1500-01-01')
        self.day = 0
        self.known = True
        self.adapter = RecordingMilitaryAdapter()
        self.runtime = MilitaryRuntime(self.world, self.adapter, lambda a,b: False,
            voyage_catalog=self.catalog, research_runtime=self.research,
            campaign_day=lambda: self.day, known_region=lambda r: self.known)
        self.runtime.set_locally_relevant(SHIP, active)
        if equipment:
            assert self.runtime.set_navigation_equipment(SHIP, 'england', True, 1000) == 880

    def start(self):
        self.runtime.start_voyage(SHIP, ROUTE, 'england')

    def advance(self, day):
        self.day = day
        self.runtime.advance_voyages(day)

    def supply(self):
        return self.runtime.unit(SHIP).supply

    def progress(self):
        return self.runtime.snapshot()['voyages']['ships'][SHIP]


class NavigationEfficiencyTests(unittest.TestCase):
    def test_registered_research_exact_same_condition_control_and_no_time_or_geography_mutation(self):
        treatment, control = Fixture(), Fixture(researched=False)
        for f in (treatment, control):
            f.start()
            self.assertEqual(20, f.supply())
            self.assertEqual(0, f.runtime.unit(SHIP).represented_object_count)
            f.advance(10)
            self.assertEqual(10, f.day)
            self.assertEqual('english_channel', f.runtime.unit(SHIP).location_id)
            self.assertFalse(f.progress()['routeId'])
        self.assertEqual((22,20), (treatment.supply(), control.supply()))
        events = treatment.research.snapshot()
        with self.assertRaises(ResearchError):
            treatment.research.advance_research('england','celestial_navigation',100000,'1500-01-01')
        self.assertEqual(events, treatment.research.snapshot())
        before = treatment.runtime.snapshot()
        treatment.advance(10)
        treatment.advance(20)
        self.assertEqual(before, treatment.runtime.snapshot())

    def test_missing_equipment_and_unsupported_vessels_do_not_gain_benefits(self):
        f = Fixture(equipment=False)
        f.start(); f.advance(10)
        self.assertEqual(20, f.supply())
        before = f.runtime.snapshot()
        for ident in ('english_guard_formation','missing_ship'):
            with self.assertRaises(MilitaryError):
                f.runtime.start_voyage(ident, ROUTE, 'england')
        self.assertEqual(before, f.runtime.snapshot())

    def test_illegal_unknown_wrong_controller_insufficient_provisions_and_duplicate_departure_are_atomic(self):
        f = Fixture()
        for operation in (
            lambda: f.runtime.start_voyage(SHIP,'unknown_route','england'),
            lambda: f.runtime.start_voyage(SHIP,ROUTE,'france'),
        ):
            before = f.runtime.snapshot()
            with self.assertRaises(MilitaryError): operation()
            self.assertEqual(before, f.runtime.snapshot())
        f.known = False
        with self.assertRaises(MilitaryError): f.start()
        f.known = True
        f.runtime.update_unit(SHIP,supply=49)
        before = f.runtime.snapshot()
        with self.assertRaises(VoyageError): f.start()
        self.assertEqual(before,f.runtime.snapshot())
        f.runtime.update_unit(SHIP,supply=70); f.start()
        before = f.runtime.snapshot()
        with self.assertRaises(VoyageError): f.start()
        with self.assertRaises(MilitaryError): f.runtime.move(SHIP,'north_sea_atlantic')
        with self.assertRaises(MilitaryError): f.runtime.set_navigation_equipment(SHIP,'england',True,1000)
        self.assertEqual(before,f.runtime.snapshot())
        f = Fixture(); f.runtime.move(SHIP,'north_sea_atlantic')
        with self.assertRaises(MilitaryError): f.start()

    def test_fixed_point_interruption_retains_fractions_without_free_future_travel(self):
        f = Fixture(); f.start(); f.advance(3)
        self.assertEqual(6000,f.progress()['creditBasisPoints'])
        f.runtime.interrupt_voyage(SHIP,'england')
        self.assertEqual(55,f.supply()) # 70 - three full provision days; no future credit
        f.start(); f.advance(5)
        self.assertEqual(6,f.supply()) # reserve 50, release one whole credit
        self.assertEqual(0,f.progress()['creditBasisPoints'])
        f.runtime.interrupt_voyage(SHIP,'england')
        self.assertEqual(46,f.supply()) # five elapsed days total: 70-25+1

    def test_active_abstract_callback_chunking_and_save_resume_parity(self):
        active, abstract, resumed = Fixture(), Fixture(active=False), Fixture()
        for f in (active,abstract,resumed): f.start()
        active.advance(3); resumed.advance(3)
        saved = resumed.runtime.snapshot()
        # Rebuild through the campaign save adapter with independently restored research.
        adapter = MilitarySaveAdapter(resumed.runtime, {})
        world = adapter.capture_world()
        rebuilt = adapter.reconstruct(world)
        resumed.runtime.set_navigation_equipment(SHIP,'england',False,0)
        adapter.activate(world,rebuilt)
        self.assertEqual(saved,resumed.runtime.snapshot())
        for day in range(4,11): active.advance(day)
        abstract.advance(10); resumed.advance(10)
        self.assertEqual((22,22,22),(active.supply(),abstract.supply(),resumed.supply()))
        self.assertEqual(active.progress(),abstract.progress())
        self.assertEqual(active.progress(),resumed.progress())
        self.assertEqual((1,0),(active.runtime.unit(SHIP).represented_object_count,abstract.runtime.unit(SHIP).represented_object_count))

    def test_equipment_and_controller_changes_recompute_eligibility(self):
        f = Fixture(); f.start(); f.advance(3)
        f.runtime.set_navigation_equipment(SHIP,'england',False,0)
        f.advance(8)
        self.assertEqual(6000,f.progress()['creditBasisPoints'])
        f.advance(10)
        self.assertEqual(20,f.supply())
        f = Fixture(); f.start(); f.advance(3)
        f.runtime.set_ownership('english_channel_fleet','france','france')
        f.advance(10)
        self.assertEqual(20,f.supply())
        self.assertEqual(6000,f.progress()['creditBasisPoints'])
        # A later transfer back does not multiply the research layer.
        f.runtime.set_ownership('english_channel_fleet','england','england')
        f.runtime.update_unit(SHIP,supply=70); f.start(); f.advance(20)
        self.assertEqual(22,f.supply())
        self.assertEqual(6000,f.progress()['creditBasisPoints'])

    def test_purchase_and_repeat_install_never_grant_free_equipment(self):
        f = Fixture(equipment=False)
        before = f.runtime.snapshot()
        with self.assertRaises(MilitaryError): f.runtime.set_navigation_equipment(SHIP,'england',True,119)
        self.assertEqual(before,f.runtime.snapshot())
        self.assertEqual(0,f.runtime.set_navigation_equipment(SHIP,'england',True,120))
        with self.assertRaises(MilitaryError): f.runtime.set_navigation_equipment(SHIP,'england',True,120)
        self.assertEqual(0,f.runtime.set_navigation_equipment(SHIP,'england',False,0))

    def test_rejected_load_and_late_projection_failure_roll_back_every_input(self):
        f = Fixture(); f.start(); f.advance(3)
        before = f.runtime.snapshot()
        for field,value in [('reserved',34),('creditBasisPoints',10000),('elapsedDays',10),('equipment',1),('routeId','unknown')]:
            candidate=copy.deepcopy(before); candidate['voyages']['ships'][SHIP][field]=value
            with self.assertRaises((VoyageError,MilitaryError)): f.runtime.restore(candidate)
            self.assertEqual(before,f.runtime.snapshot())
        f.advance(10)
        checkpoint = f.runtime.snapshot()
        original = f.adapter.create
        f.adapter.create = lambda *_args: (_ for _ in ()).throw(RuntimeError('injected projection failure'))
        candidate = copy.deepcopy(checkpoint); candidate['voyages']['ships'][SHIP]['equipment']=False
        with self.assertRaises(RuntimeError): f.runtime.restore(candidate)
        f.adapter.create = original
        self.assertEqual(checkpoint,f.runtime.snapshot())

    def test_legacy_migration_is_pure_and_never_copies_live_equipment_or_credit(self):
        f = Fixture(); f.start(); f.advance(3)
        legacy = MilitaryRuntime(f.world,RecordingMilitaryAdapter(),lambda a,b:False).snapshot()
        migrated = f.runtime.validate_snapshot(legacy)
        self.assertEqual(1,legacy['schemaVersion'])
        self.assertEqual(2,migrated['schemaVersion'])
        self.assertEqual(f.catalog.empty(),migrated['voyages']['ships'][SHIP])
        self.assertTrue(f.progress()['equipment'])

    def test_catalog_rejects_disconnected_boundary_and_incompatible_ship(self):
        catalog,world=build()
        for mutation in ('edge','vessel','duration','provisions'):
            data=copy.deepcopy(catalog.data)
            if mutation=='edge': data['routes'][0]['zoneCircuit']=['english_channel','decorative_lake','english_channel']
            if mutation=='vessel': data['ships'][0]['forceId']='english_guard_formation'
            if mutation=='duration': data['routes'][0]['days']=61
            if mutation=='provisions': data['routes'][0]['dailyPositionFindingProvisions']=6
            with self.assertRaises(VoyageError): VoyageCatalog(data,world)

    def test_generated_contract_and_blockers_preserve_pricing_and_other_consumers(self):
        with tempfile.TemporaryDirectory() as tmp:
            generate(load_config(ROOT/'package.json'),Path(tmp))
            verify_generated(load_config(ROOT/'package.json'),Path(tmp))
            source=(Path(tmp)/'ScenarioData.wurst').read_text()
            payload=json.loads((Path(tmp)/'scenario-runtime.json').read_text())
        catalog,world=build()
        self.assertEqual(1,source.count(wurst(catalog,world)))
        self.assertIn('new RuntimeForce("english_patrol_ship", "england", "europe_west", "sailing_naval", FORCE_FLEET, \'hbot\', 1, 70, 4160, -6720)',source)
        self.assertEqual(catalog.data,payload['voyageNavigation'])
        blocked={x['contentId'] for x in payload['researchIntegrationBlockers']}
        self.assertNotIn(catalog.content,blocked)
        self.assertIn('fleet_navigation_efficiency',blocked)
        celestial=next(t for t in world['technologies'] if t['id']=='celestial_navigation')
        self.assertEqual((1480,110),(celestial['timeCost']['preferredYear'],celestial['timeCost']['baseCost']))


    def test_generated_navigation_calls_and_payload_reject_tampering_even_with_rehashed_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            generated=Path(tmp); config=load_config(ROOT/'package.json')
            generate(config,generated)
            original_source=(generated/'ScenarioData.wurst').read_bytes()
            original_data=(generated/'scenario-runtime.json').read_bytes()
            for mutation in ('magnitude','duplicate','payload'):
                (generated/'ScenarioData.wurst').write_bytes(original_source)
                (generated/'scenario-runtime.json').write_bytes(original_data)
                source=original_source.decode()
                if mutation=='magnitude':
                    source=source.replace('"progression_celestial_navigation", 1000, 120','"progression_celestial_navigation", 5000, 120')
                if mutation=='duplicate':
                    source += '\npublic function badVoyageGrant()\n\tlet contract = new VoyageContract("modifier", "progression_celestial_navigation", 1000, 120)\n'
                (generated/'ScenarioData.wurst').write_text(source)
                if mutation=='payload':
                    payload=json.loads(original_data); payload['voyageNavigation']['positionFindingReductionBasisPoints']=5000
                    (generated/'scenario-runtime.json').write_text(json.dumps(payload))
                provenance=json.loads((generated/'provenance.json').read_text())
                for name in ('ScenarioData.wurst','scenario-runtime.json'):
                    provenance['outputs'][name]=hashlib.sha256((generated/name).read_bytes()).hexdigest()
                (generated/'provenance.json').write_text(json.dumps(provenance))
                with self.assertRaises(PackagingError): verify_generated(config,generated)


if __name__ == '__main__': unittest.main()
