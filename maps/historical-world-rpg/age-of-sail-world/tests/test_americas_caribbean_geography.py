import copy
import importlib.util
import json
import sys
import unittest
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
SOURCE = PROJECT / "scenario/geography/americas_caribbean.json"
WORLD = PROJECT / "scenario/world/world.json"
MAPS = PROJECT / "physical-maps.json"
spec = importlib.util.spec_from_file_location("americas_caribbean_geography", PROJECT / "tooling/americas_caribbean_geography.py")
geography = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = geography
spec.loader.exec_module(geography)


class AmericasCaribbeanGeographyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = json.loads(SOURCE.read_text())
        cls.world = json.loads(WORLD.read_text())
        cls.maps = json.loads(MAPS.read_text())

    def test_authoritative_inventory_coordinates_density_and_budgets_validate(self):
        instances, anchors = geography.validate(copy.deepcopy(self.source), copy.deepcopy(self.world), copy.deepcopy(self.maps))
        self.assertEqual(8, len(instances))
        self.assertEqual(16, len(anchors))
        self.assertEqual(54, sum(len(item["features"]) for item in instances.values()))
        self.assertEqual(set(geography._base.KINDS) | geography.EXTRA_KINDS, set(self.source["requiredFeatureIds"]))
        for instance in instances.values():
            self.assertIn("complexity", instance)
            self.assertLessEqual(len(instance["features"]), instance["budget"]["maxFeatures"])

    def test_required_features_are_owned_once_and_maps_cover_every_instance(self):
        owned = [(feature["id"], feature["kind"]) for instance in self.source["instances"] for feature in instance["features"]]
        declared = {(feature_id, kind) for kind, ids in self.source["requiredFeatureIds"].items() for feature_id in ids}
        self.assertEqual(len(owned), len({item[0] for item in owned}))
        self.assertEqual(declared, set(owned))
        assigned = [instance_id for item in self.maps["physicalMaps"] for instance_id in item.get("assignments", {}).get("regionalInstanceIds", []) if instance_id.startswith("americas_")]
        self.assertEqual(set(assigned), {item["id"] for item in self.source["instances"]})
        self.assertEqual(len(assigned), len(set(assigned)))

    def test_external_stubs_correspond_to_europe_africa_and_pacific_contracts(self):
        bindings = {anchor.get("globalAnchorId") for anchor in self.source["boundaryAnchors"] if anchor.get("globalAnchorId")}
        self.assertEqual({"americas_caribbean_east", "americas_caribbean_west"}, bindings)
        edges = {edge["id"]: edge for group in ("boundaries", "routes") for edge in self.world["regionalGeography"][group]}
        self.assertTrue(geography.REQUIRED_GLOBAL_EDGES <= set(edges))
        self.assertEqual("europe", edges["north_atlantic_crossing"]["from"]["regionId"])
        self.assertEqual("africa", edges["south_atlantic_crossing"]["from"]["regionId"])
        self.assertEqual("pacific", edges["pacific_americas_crossing"]["from"]["regionId"])

    def test_all_movement_modes_connect_and_forbidden_nodes_remain_isolated(self):
        nodes = {item["id"]: item for item in self.source["navigationTopology"]["nodes"]}
        links = self.source["navigationTopology"]["links"]
        for corridor in self.source["requiredTraversalConnections"]:
            for mode in corridor["movementClasses"]:
                self.assertIn(corridor["toNodeId"], geography._reachable(nodes, links, corridor["fromNodeId"], mode))
        self.assertIn("node_southern_cone_land", geography._reachable(nodes, links, "node_north_america_east_land", "land"))
        self.assertIn("node_south_pacific", geography._reachable(nodes, links, "node_north_atlantic", "naval"))
        self.assertIn("node_caribbean_islands", geography._reachable(nodes, links, "node_north_america_east_land", "amphibious"))
        self.assertIn("node_south_pacific", geography._reachable(nodes, links, "node_north_america_east_land", "flying"))
        self.assertNotIn("node_isolated_crater_lake", geography._reachable(nodes, links, "node_north_atlantic", "naval"))
        self.assertNotIn("node_rockies_barrier", geography._reachable(nodes, links, "node_north_america_east_land", "land"))
        self.assertNotIn("node_andes_barrier", geography._reachable(nodes, links, "node_north_andes_land", "land"))

    def test_generation_is_deterministic_normalized_and_transform_exact(self):
        first = geography.generate(copy.deepcopy(self.source), copy.deepcopy(self.world), copy.deepcopy(self.maps))
        second = geography.generate(copy.deepcopy(self.source), copy.deepcopy(self.world), copy.deepcopy(self.maps))
        self.assertEqual(first, second)
        self.assertEqual(first, json.dumps(json.loads(first), indent=2, sort_keys=True, separators=(",", ": ")) + "\n")
        for output in json.loads(first)["instances"]:
            owner = next(item for item in self.source["instances"] if item["id"] == output["id"])
            originals = {item["id"]: item for item in owner["features"]}
            for feature in output["features"]:
                expected = [geography._base.transform_point(owner, point, 2) for point in originals[feature["id"]]["points"]]
                self.assertEqual(expected, feature["localPoints"])

    def test_invalid_seams_maps_routes_density_distortion_and_complexity_are_diagnostic(self):
        broken = copy.deepcopy(self.source)
        broken["boundaryAnchors"][1]["source"][0] += 0.1
        with self.assertRaisesRegex(geography.GeographyError, "seam discontinuity"):
            geography.validate(broken, self.world, self.maps)
        broken = copy.deepcopy(self.source)
        broken["instances"][0]["physicalMapId"] = "east_asia"
        with self.assertRaisesRegex(geography.GeographyError, "physical-map reference"):
            geography.validate(broken, self.world, self.maps)
        broken = copy.deepcopy(self.source)
        broken["navigationTopology"]["links"][0]["to"] = "node_rockies_barrier"
        with self.assertRaisesRegex(geography.GeographyError, "impassable barriers"):
            geography.validate(broken, self.world, self.maps)
        broken = copy.deepcopy(self.source)
        broken["instances"][0]["budget"]["maxControlPoints"] = 1
        with self.assertRaisesRegex(geography.GeographyError, "control points exceed"):
            geography.validate(broken, self.world, self.maps)
        broken = copy.deepcopy(self.source)
        broken["instances"][0]["complexity"]["generationWeight"] = 1.1
        with self.assertRaisesRegex(geography.GeographyError, "complexity budget exceeded"):
            geography.validate(broken, self.world, self.maps)
        broken = copy.deepcopy(self.source)
        broken["distortions"][0]["adjacencyGapCells"] = 9
        with self.assertRaisesRegex(geography.GeographyError, "adjacency exceeds"):
            geography.validate(broken, self.world, self.maps)


if __name__ == "__main__":
    unittest.main()
