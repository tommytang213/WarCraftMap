import copy, importlib.util, json, sys, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORLD = Path(__file__).resolve().parents[1] / "scenario/world/world.json"
spec = importlib.util.spec_from_file_location("regional_navigation", ROOT / "_shared/engine/regional_navigation.py")
nav = importlib.util.module_from_spec(spec); sys.modules[spec.name] = nav; spec.loader.exec_module(nav)
EUROPE = Path(__file__).resolve().parents[1] / "scenario/geography/europe.json"
europe_spec = importlib.util.spec_from_file_location("europe_geography", Path(__file__).resolve().parents[1] / "tooling/europe_geography.py")
europe_geo = importlib.util.module_from_spec(europe_spec); europe_spec.loader.exec_module(europe_geo)

class Runtime:
    def __init__(self): self.objects = {"region": "europe"}; self.calls = []
    def snapshot(self): return copy.deepcopy((self.objects, self.calls))
    def restore(self, value): self.objects, self.calls = copy.deepcopy(value)
    def retire_region(self, region_id): self.calls.append(("retire", region_id)); self.objects.pop("region", None)
    def reconstruct_region(self, region_id, entities): self.calls.append(("reconstruct", region_id, sorted(entities))); self.objects["region"] = region_id
    def relocate_entity(self, entity_id, region_id, area_id, x, y): self.calls.append(("relocate", entity_id, region_id, area_id, x, y))

class Persistence:
    def __init__(self): self.states = []; self.fail = False
    def checkpoint(self, state):
        if self.fail: raise RuntimeError("storage failed")
        self.states.append(copy.deepcopy(state))

class RegionalNavigationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.geography = json.loads(WORLD.read_text())["regionalGeography"]
    def make(self, movement="naval", region="europe", hook=None):
        state = {"activeRegionId": region, "campaignTime": 100, "entities": {"ship": {"regionId": region, "areaId": f"{region}_coarse", "position": {"x": 50, "y": 50}, "movementClass": movement, "physicallyActive": True, "transitionState": "idle", "strength": 77}}, "pendingCrossings": {}}
        runtime, persistence = Runtime(), Persistence()
        return nav.RegionalWorld(self.geography, state, runtime, persistence, hook), runtime, persistence

    def test_complete_global_graph_and_stable_ids(self):
        expected = {"europe", "africa", "middle_east_india", "southeast_asia", "east_asia", "americas_caribbean", "pacific"}
        self.assertEqual(expected, {r["id"] for r in self.geography["regions"]})
        ids = [x["id"] for group in self.geography.values() for x in group]
        self.assertEqual(len(ids), len(set(ids)))

    def test_valid_land_and_sea_boundaries_use_deterministic_anchor(self):
        world, runtime, _ = self.make("land")
        result = world.transition("ship", "europe_middle_east_boundary")
        self.assertEqual(("middle_east_india", "middle_east_india_west"), (result.region_id, result.anchor_id))
        self.assertEqual(77, world.state["entities"]["ship"]["strength"])
        sea, _, _ = self.make("naval")
        self.assertEqual("africa_north", sea.transition("ship", "europe_africa_boundary").anchor_id)
        self.assertIn(("retire", "europe"), runtime.calls)

    def test_invalid_stale_disconnected_and_incompatible_rejected_atomically(self):
        for entity, edge in (("missing", "europe_africa_boundary"), ("ship", "southeast_east_asia_boundary")):
            world, runtime, persistence = self.make()
            before = world.export_state(), runtime.snapshot()
            with self.assertRaises(nav.InvalidTransition): world.transition(entity, edge)
            self.assertEqual(before, (world.export_state(), runtime.snapshot()))
            self.assertFalse(persistence.states)
        world, runtime, _ = self.make("land")
        before = world.export_state(), runtime.snapshot()
        with self.assertRaises(nav.InvalidTransition): world.transition("ship", "europe_africa_boundary")
        self.assertEqual(before, (world.export_state(), runtime.snapshot()))

    def test_runtime_or_persistence_failure_rolls_back(self):
        world, runtime, persistence = self.make()
        persistence.fail = True; before = world.export_state(), runtime.snapshot()
        with self.assertRaises(RuntimeError): world.transition("ship", "europe_africa_boundary")
        self.assertEqual(before, (world.export_state(), runtime.snapshot()))
        persistence.fail = False
        runtime.reconstruct_region = lambda *_: (_ for _ in ()).throw(RuntimeError("spawn failed"))
        before = world.export_state(), runtime.snapshot()
        with self.assertRaises(RuntimeError): world.transition("ship", "europe_africa_boundary")
        self.assertEqual(before, (world.export_state(), runtime.snapshot()))

    def test_crossing_hooks_order_time_and_accelerated_equivalence(self):
        hooks = []
        world, _, _ = self.make(hook=lambda hook, crossing: hooks.append((hook, crossing["elapsedDays"])))
        world.begin_crossing("ship", "north_atlantic_crossing"); world.advance(35)
        self.assertEqual(["ocean_weather", "open_ocean_encounter"], [x[0] for x in hooks])
        self.assertEqual((135, "americas_caribbean", {}), (world.state["campaignTime"], world.state["entities"]["ship"]["regionId"], world.state["pendingCrossings"]))
        other, _, _ = self.make(); other.begin_crossing("ship", "north_atlantic_crossing")
        for _ in range(35): other.advance(1)
        self.assertEqual(world.export_state(), other.export_state())

    def test_crossing_cancel_and_hook_failure_are_atomic(self):
        world, runtime, _ = self.make(); original = world.export_state()
        world.begin_crossing("ship", "north_atlantic_crossing"); world.cancel_crossing("ship")
        self.assertEqual(original["entities"], world.state["entities"]); self.assertFalse(world.state["pendingCrossings"])
        failing, failed_runtime, _ = self.make(hook=lambda *_: (_ for _ in ()).throw(RuntimeError("encounter failed")))
        failing.begin_crossing("ship", "north_atlantic_crossing"); failing.advance(11)
        before = failing.export_state(), failed_runtime.snapshot()
        with self.assertRaises(RuntimeError): failing.advance(1)
        self.assertEqual(before, (failing.export_state(), failed_runtime.snapshot()))

    def test_save_resume_mid_crossing_and_headless_inactive_simulation(self):
        world, _, _ = self.make(); world.begin_crossing("ship", "north_atlantic_crossing"); world.advance(17)
        resumed = nav.RegionalWorld(self.geography, world.export_state(), Runtime()); resumed.advance(18)
        baseline, _, _ = self.make(); baseline.begin_crossing("ship", "north_atlantic_crossing"); baseline.advance(35)
        self.assertEqual(baseline.export_state(), resumed.export_state())
        inactive = []
        resumed.simulate_inactive(3, lambda state, region, days: inactive.append((region, days)))
        self.assertNotIn(resumed.state["activeRegionId"], {r for r, _ in inactive})
        self.assertEqual(6, len(inactive))

    def test_europe_spatial_source_and_deterministic_generation(self):
        source = json.loads(EUROPE.read_text()); world = json.loads(WORLD.read_text())
        instances, anchors = europe_geo.validate(source, world)
        self.assertEqual((8, 19), (len(instances), len(anchors)))
        self.assertEqual(europe_geo.generate(source, world), europe_geo.generate(copy.deepcopy(source), copy.deepcopy(world)))
        feature = json.loads(europe_geo.generate(source, world))["instances"][0]["features"][0]
        self.assertTrue(feature["sourcePoints"] and feature["localPoints"])

    def test_europe_seams_distortions_and_budgets_are_enforced(self):
        source = json.loads(EUROPE.read_text()); world = json.loads(WORLD.read_text())
        broken = copy.deepcopy(source); broken["boundaryAnchors"][1]["source"][0] += 1; broken["boundaryAnchors"][1]["local"][0] += 5
        with self.assertRaisesRegex(europe_geo.GeographyError, "seam discontinuity"): europe_geo.validate(broken, world)
        broken = copy.deepcopy(source); broken["distortions"][0]["orientationDeltaDegrees"] = 13
        with self.assertRaisesRegex(europe_geo.GeographyError, "orientation exceeds"): europe_geo.validate(broken, world)
        broken = copy.deepcopy(source); broken["instances"][0]["budget"]["maxControlPoints"] = 1
        with self.assertRaisesRegex(europe_geo.GeographyError, "control points exceed"): europe_geo.validate(broken, world)

if __name__ == "__main__": unittest.main()
