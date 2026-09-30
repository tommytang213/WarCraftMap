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
    def __init__(self): self.objects = {"region": "europe", "representations": {"ship"}}; self.calls = []
    def snapshot(self): return copy.deepcopy((self.objects, self.calls))
    def restore(self, value): self.objects, self.calls = copy.deepcopy(value)
    def retire_region(self, region_id): self.calls.append(("retire", region_id)); self.objects.pop("region", None); self.objects["representations"] = set()
    def reconstruct_region(self, region_id, entities): self.calls.append(("reconstruct", region_id, sorted(entities))); self.objects["region"] = region_id; self.objects["representations"] = set(entities)
    def relocate_entity(self, entity_id, region_id, area_id, x, y): self.calls.append(("relocate", entity_id, region_id, area_id, x, y))
    def representation_ids(self): return set(self.objects.get("representations", ()))

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

    def test_all_movement_classes_and_representation_indexes(self):
        for movement, boundary in (("land", "europe_middle_east_boundary"), ("naval", "europe_africa_boundary"), ("amphibious", "europe_africa_boundary"), ("flying", "europe_africa_boundary")):
            with self.subTest(movement=movement):
                world, _, _ = self.make(movement)
                world.transition("ship", boundary)
                state = world.export_state()
                self.assertEqual(state["activePhysicalRegionId"], state["activeLocalRegionId"])
                self.assertEqual("ship", world.representation_indexes["byEntityId"]["ship"]["stableId"])
                self.assertNotIn("representationIndexes", state)

    def test_every_boundary_endpoint_and_long_distance_route(self):
        for boundary in self.geography["boundaries"]:
            endpoints = [(boundary["from"], boundary["to"])]
            if not boundary["directed"]:
                endpoints.append((boundary["to"], boundary["from"]))
            for source, destination in endpoints:
                for movement in boundary["movementClasses"]:
                    with self.subTest(edge=boundary["id"], source=source["regionId"], movement=movement):
                        world, _, _ = self.make(movement, source["regionId"])
                        result = world.transition("ship", boundary["id"])
                        self.assertEqual((destination["regionId"], destination["anchorId"]), (result.region_id, result.anchor_id))
        for route in self.geography["routes"]:
            for movement in route["movementClasses"]:
                with self.subTest(route=route["id"], movement=movement):
                    world, _, _ = self.make(movement, route["from"]["regionId"])
                    world.begin_crossing("ship", route["id"])
                    world.advance(route["durationDays"])
                    self.assertEqual(route["to"]["regionId"], world.state["entities"]["ship"]["regionId"])
                    self.assertEqual(route["to"]["anchorId"], next(anchor["id"] for anchor in self.geography["anchors"] if anchor["areaId"] == world.state["entities"]["ship"]["areaId"] and anchor["position"] == world.state["entities"]["ship"]["position"]))

    def test_activation_only_materializes_local_relevant_entities_and_preserves_authority(self):
        world, runtime, _ = self.make()
        world.state["entities"].update({
            "local_army": {"regionId": "europe", "areaId": "europe_coarse", "position": {"x": 1, "y": 2}, "movementClass": "land", "physicallyActive": True, "transitionState": "idle", "army": {"regiments": ["r1"]}},
            "abstract_city": {"regionId": "europe", "areaId": "europe_coarse", "position": {"x": 3, "y": 4}, "movementClass": "land", "physicallyActive": False, "transitionState": "idle", "structures": ["dock"]},
            "remote_character": {"regionId": "africa", "areaId": "africa_coarse", "position": {"x": 5, "y": 6}, "movementClass": "land", "physicallyActive": True, "transitionState": "idle", "inventory": ["chart"], "quests": ["q1"]},
        })
        authority = copy.deepcopy(world.state["entities"])
        world.activate("europe")
        self.assertEqual(["local_army", "ship"], runtime.calls[-1][2])
        self.assertEqual(authority, world.state["entities"])
        self.assertEqual({"local_army", "ship"}, set(world.representation_indexes["byEntityId"]))
        world.activate("africa")
        self.assertEqual(["remote_character"], runtime.calls[-1][2])
        self.assertEqual(authority, world.state["entities"])

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
        loading, loading_runtime, _ = self.make(); adapter = nav.RegionalSaveAdapter(loading)
        adapter.activate({}, world.export_state())
        self.assertFalse(loading.state["runtimeRegionActive"])
        self.assertNotIn("region", loading_runtime.objects)

    def test_checkpoint_resume_immediately_before_and_after_boundary(self):
        before, _, _ = self.make("land")
        preloaded = nav.RegionalWorld(self.geography, before.export_state(), Runtime())
        preloaded.transition("ship", "europe_middle_east_boundary")
        completed = preloaded.export_state()
        post_runtime = Runtime()
        postloaded = nav.RegionalWorld(self.geography, completed, post_runtime)
        post_runtime.objects.clear()
        self.assertEqual(["ship"], postloaded.recover_representations())
        self.assertEqual("middle_east_india", postloaded.state["activePhysicalRegionId"])
        self.assertEqual(completed, postloaded.export_state())

    def test_stale_or_inconsistent_pending_crossing_is_rejected(self):
        world, _, _ = self.make(); world.begin_crossing("ship", "north_atlantic_crossing")
        for mutate in (
            lambda state: state["pendingCrossings"]["ship"].update(routeId="missing"),
            lambda state: state["entities"]["ship"].update(transitionState="idle"),
            lambda state: state.update(runtimeRegionActive=True),
        ):
            candidate = world.export_state(); mutate(candidate)
            with self.subTest(candidate=candidate), self.assertRaises(nav.RegionalNavigationError):
                nav.RegionalWorld(self.geography, candidate, Runtime())

    def test_representation_loss_reconstruction_and_save_adapter_migration(self):
        world, runtime, _ = self.make(); runtime.objects.clear()
        self.assertEqual(["ship"], world.recover_representations())
        self.assertEqual("europe", runtime.objects["region"])
        world.begin_crossing("ship", "north_atlantic_crossing")
        calls = list(runtime.calls)
        self.assertEqual([], world.recover_representations())
        self.assertEqual(calls, runtime.calls)
        world.advance(35); runtime.objects.clear()
        self.assertEqual(["ship"], world.recover_representations())
        self.assertEqual("americas_caribbean", runtime.objects["region"])
        adapter = nav.RegionalSaveAdapter(world)
        saved = adapter.capture_world({"calendar": {"day": 100}})
        adapter.validate_world(saved)
        self.assertNotIn(nav.REGIONAL_WORLD_STATE_KEY, {"calendar": {"day": 100}})
        self.assertIn(nav.REGIONAL_WORLD_STATE_KEY, adapter.migrate_legacy_world({"calendar": {"day": 100}}))

    def test_failed_arrival_reconstruction_keeps_pending_crossing_at_prior_valid_boundary(self):
        world, runtime, _ = self.make()
        world.begin_crossing("ship", "north_atlantic_crossing"); world.advance(34)
        before = world.export_state(), runtime.snapshot(), copy.deepcopy(world.representation_indexes)
        runtime.reconstruct_region = lambda *_: (_ for _ in ()).throw(RuntimeError("arrival failed"))
        with self.assertRaisesRegex(RuntimeError, "arrival failed"):
            world.advance(1)
        self.assertEqual(before, (world.export_state(), runtime.snapshot(), world.representation_indexes))

    def test_concurrent_request_is_rejected_without_mutation(self):
        world, runtime, _ = self.make()
        original = runtime.reconstruct_region
        def reentrant(region_id, entities):
            with self.assertRaisesRegex(nav.InvalidTransition, "in progress"):
                world.transition("ship", "europe_africa_boundary")
            original(region_id, entities)
        runtime.reconstruct_region = reentrant
        world.transition("ship", "europe_africa_boundary")
        self.assertEqual("africa", world.state["activePhysicalRegionId"])

    def test_active_object_and_transition_time_budgets_rollback(self):
        world, runtime, _ = self.make()
        world.max_active_objects = 0
        before = world.export_state(), runtime.snapshot()
        with self.assertRaisesRegex(nav.RuntimeReconstructionError, "active object budget"):
            world.activate("europe")
        self.assertEqual(before, (world.export_state(), runtime.snapshot()))
        timed, timed_runtime, _ = self.make(); timed.max_transition_milliseconds = 0.000001
        before = timed.export_state(), timed_runtime.snapshot()
        with self.assertRaisesRegex(nav.RuntimeReconstructionError, "ms budget"):
            timed.transition("ship", "europe_africa_boundary")
        self.assertEqual(before, (timed.export_state(), timed_runtime.snapshot()))

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
