import copy
import importlib.util
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PROJECT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("map_discovery", ROOT / "_shared/engine/map_discovery.py")
maps = importlib.util.module_from_spec(spec); sys.modules[spec.name] = maps; spec.loader.exec_module(maps)


class MapDiscoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        world = json.loads((PROJECT / "scenario/world/world.json").read_text())
        presentation = json.loads((PROJECT / "scenario/maps/world-map.json").read_text())
        cls.catalog = maps.build_catalog(world, presentation)

    def make(self):
        knowledge = maps.DiscoveryKnowledge(self.catalog)
        knowledge.reveal_region("europe")
        return knowledge, maps.CampaignMap(self.catalog, knowledge, "europe", "africa")

    def test_world_and_region_contexts_distinguish_physical_and_command_regions(self):
        knowledge, view = self.make()
        world = view.open_world()
        self.assertEqual(("world", "europe", "africa", True), (world["context"], world["physicalRegionId"], world["commandRegionId"], world["modal"]))
        regional = view.open_region("europe")
        self.assertEqual(("regional", "europe"), (regional["context"], regional["focusedRegionId"]))
        view.set_command_region("middle_east_india")
        self.assertEqual("europe", view.render()["physicalRegionId"])

    def test_exploring_region_does_not_discover_hidden_locations(self):
        knowledge, view = self.make()
        model = view.open_region("europe")
        self.assertFalse(model["settlements"])
        self.assertFalse(model["landmarks"])
        self.assertFalse(model["pointsOfInterest"])
        with self.assertRaisesRegex(maps.MapDiscoveryError, "unknown location"):
            view.focus_location("uncharted_atlantic_island")

    def test_visit_or_explicit_reveal_makes_settlement_exact(self):
        knowledge, view = self.make()
        knowledge.visit_settlement("london")
        focused = view.focus_location("london")
        self.assertEqual(("exact", "london"), (focused["focus"]["precision"], focused["focus"]["targetId"]))
        self.assertEqual(["london"], [x["id"] for x in focused["settlements"]])

    def test_region_approximate_exact_and_previously_discovered_precedence(self):
        knowledge, view = self.make()
        target = "hidden_desert_ruin"
        knowledge.reveal_region_only(target)
        self.assertEqual("region", view.focus_location(target)["focus"]["precision"])
        knowledge.reveal_approximate(target, [{"id": "desert_clue_a", "regionId": "africa", "shape": "circle", "center": {"x": 40, "y": 60}, "radius": 18}])
        self.assertEqual("desert_clue_a", view.focus_location(target)["focus"]["areas"][0]["id"])
        knowledge.reveal_exact(target)
        knowledge.reveal_approximate(target, [{"id": "weaker_later_clue", "regionId": "africa", "shape": "circle", "center": {"x": 1, "y": 1}, "radius": 50}])
        self.assertEqual("exact", view.focus_location(target)["focus"]["precision"])

    def test_search_areas_can_shrink_move_split_and_resolve(self):
        knowledge, view = self.make(); target = "hidden_desert_ruin"
        knowledge.reveal_approximate(target, [{"id": "clue_wide", "regionId": "africa", "shape": "circle", "center": {"x": 50, "y": 50}, "radius": 30}])
        knowledge.reveal_approximate(target, [
            {"id": "clue_west", "regionId": "africa", "shape": "circle", "center": {"x": 35, "y": 55}, "radius": 8},
            {"id": "clue_east", "regionId": "africa", "shape": "polygon", "points": [{"x": 45, "y": 50}, {"x": 55, "y": 50}, {"x": 50, "y": 60}]},
        ])
        state = knowledge.export_state()
        self.assertNotIn("clue_wide", state["searchAreas"])
        self.assertEqual({"clue_west", "clue_east"}, set(state["locations"][target]["searchAreaIds"]))
        self.assertEqual("clue_west", view.focus_search_area("clue_west")["focus"]["areas"][0]["id"])
        knowledge.reveal_exact(target)
        self.assertFalse(knowledge.export_state()["locations"][target]["searchAreaIds"])

    def test_routes_breadcrumbs_and_secret_filtering_are_explicit(self):
        knowledge, view = self.make()
        knowledge.reveal_transition("europe_africa_boundary")
        knowledge.visit_settlement("london")
        model = view.open_world()
        self.assertEqual(["europe_africa_boundary"], [x["id"] for x in model["boundaries"]])
        self.assertFalse(model["routes"])
        self.assertNotIn("hidden_desert_ruin", json.dumps(model))
        knowledge.reveal_transition("north_atlantic_crossing")
        self.assertEqual(["north_atlantic_crossing"], [x["id"] for x in view.open_world()["routes"]])
        regional = view.open_region("africa")
        self.assertEqual(["europe", "africa"], regional["breadcrumbRegionIds"])

    def test_focus_is_informational_and_does_not_move_entities(self):
        knowledge, view = self.make(); knowledge.visit_settlement("london")
        regional_state = {"entities": {"hero": {"regionId": "europe", "position": {"x": 3, "y": 4}}}}
        before = copy.deepcopy(regional_state)
        view.focus_location("london")
        self.assertEqual(before, regional_state)

    def test_save_load_passive_reconstruction_and_invalid_references(self):
        knowledge, _ = self.make()
        knowledge.reveal_approximate("hidden_desert_ruin", [{"id": "saved_clue", "regionId": "africa", "shape": "circle", "center": {"x": 4, "y": 5}, "radius": 6}])
        restored = maps.DiscoveryKnowledge(self.catalog, json.loads(json.dumps(knowledge.export_state())))
        self.assertEqual(knowledge.export_state(), restored.export_state())
        broken = restored.export_state(); broken["settlements"] = ["missing_city"]
        with self.assertRaisesRegex(maps.MapDiscoveryError, "invalid reference"):
            maps.DiscoveryKnowledge(self.catalog, broken)

    def test_deterministic_render_model(self):
        knowledge, view = self.make(); knowledge.visit_settlement("london")
        self.assertEqual(view.open_world(), view.open_world())


if __name__ == "__main__": unittest.main()
