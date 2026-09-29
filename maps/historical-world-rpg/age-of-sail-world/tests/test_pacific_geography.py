import copy
import importlib.util
import json
import sys
import unittest
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
SOURCE = PROJECT / "scenario/geography/pacific.json"
WORLD = PROJECT / "scenario/world/world.json"
MAPS = PROJECT / "physical-maps.json"
spec = importlib.util.spec_from_file_location("pacific_geography", PROJECT / "tooling/pacific_geography.py")
geography = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = geography
spec.loader.exec_module(geography)


class PacificGeographyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = json.loads(SOURCE.read_text())
        cls.world = json.loads(WORLD.read_text())
        cls.maps = json.loads(MAPS.read_text())
        cls.adjoining = {key: json.loads(path.read_text()) for key, path in geography.ADJOINING_SOURCES.items()}

    def test_authoritative_inventory_coordinates_density_and_budgets_validate(self):
        instances, anchors = geography.validate(copy.deepcopy(self.source), copy.deepcopy(self.world), copy.deepcopy(self.maps), copy.deepcopy(self.adjoining))
        self.assertEqual(6, len(instances))
        self.assertEqual(14, len(anchors))
        self.assertEqual(49, sum(len(item["features"]) for item in instances.values()))
        self.assertEqual(set(geography._base.KINDS) | geography.EXTRA_KINDS, set(self.source["requiredFeatureIds"]))
        for instance in instances.values():
            self.assertLessEqual(len(instance["features"]), instance["budget"]["maxFeatures"])
            self.assertIn("complexity", instance)

    def test_required_features_owned_once_and_physical_maps_cover_instances(self):
        owned = [(feature["id"], feature["kind"]) for instance in self.source["instances"] for feature in instance["features"]]
        declared = {(feature_id, kind) for kind, ids in self.source["requiredFeatureIds"].items() for feature_id in ids}
        self.assertEqual(len(owned), len({item[0] for item in owned}))
        self.assertEqual(declared, set(owned))
        assigned = [instance_id for item in self.maps["physicalMaps"] for instance_id in item.get("assignments", {}).get("regionalInstanceIds", []) if instance_id.startswith("pacific_")]
        self.assertEqual({item["id"] for item in self.source["instances"]}, set(assigned))
        self.assertEqual(len(assigned), len(set(assigned)))

    def test_external_routes_correspond_to_adjoining_boundary_contracts(self):
        routes = {item["id"]: item for item in self.world["regionalGeography"]["routes"]}
        self.assertTrue(geography.REQUIRED_GLOBAL_ROUTES <= set(routes))
        for region_id, anchor_id in geography.EXPECTED_ADJOINING_BINDINGS.items():
            self.assertIn(anchor_id, {a.get("globalAnchorId") for a in self.adjoining[region_id]["boundaryAnchors"]})
        self.assertEqual({"pacific_west", "pacific_east"}, {a.get("globalAnchorId") for a in self.source["boundaryAnchors"] if a.get("globalAnchorId")})

    def test_navigation_connects_routes_and_rejects_land_across_water(self):
        nodes = {item["id"]: item for item in self.source["navigationTopology"]["nodes"]}
        links = self.source["navigationTopology"]["links"]
        for corridor in self.source["requiredTraversalConnections"]:
            for mode in corridor["movementClasses"]:
                self.assertIn(corridor["toNodeId"], geography._reachable(nodes, links, corridor["fromNodeId"], mode))
        self.assertIn("node_americas_approach", geography._reachable(nodes, links, "node_north_pacific", "naval"))
        self.assertIn("node_new_zealand_land", geography._reachable(nodes, links, "node_north_pacific", "amphibious"))
        self.assertIn("node_americas_approach", geography._reachable(nodes, links, "node_new_guinea_land", "flying"))
        self.assertNotIn("node_new_zealand_land", geography._reachable(nodes, links, "node_new_guinea_land", "land"))
        self.assertNotIn("node_decorative_open_ocean", geography._reachable(nodes, links, "node_north_pacific", "naval"))
        self.assertNotIn("node_great_barrier_reef", geography._reachable(nodes, links, "node_melanesia_sea", "naval"))

    def test_generation_is_deterministic_normalized_and_transform_exact(self):
        first = geography.generate(copy.deepcopy(self.source), copy.deepcopy(self.world), copy.deepcopy(self.maps), copy.deepcopy(self.adjoining))
        second = geography.generate(copy.deepcopy(self.source), copy.deepcopy(self.world), copy.deepcopy(self.maps), copy.deepcopy(self.adjoining))
        self.assertEqual(first, second)
        self.assertEqual(first, json.dumps(json.loads(first), indent=2, sort_keys=True, separators=(",", ": ")) + "\n")
        for output in json.loads(first)["instances"]:
            owner = next(item for item in self.source["instances"] if item["id"] == output["id"])
            originals = {item["id"]: item for item in owner["features"]}
            for feature in output["features"]:
                self.assertEqual([geography._base.transform_point(owner, point, 2) for point in originals[feature["id"]]["points"]], feature["localPoints"])

    def test_invalid_contracts_topology_density_distortion_and_complexity_are_diagnostic(self):
        broken = copy.deepcopy(self.source)
        broken["instances"][0]["physicalMapId"] = "east_asia"
        with self.assertRaisesRegex(geography.GeographyError, "physical-map reference"):
            geography.validate(broken, self.world, self.maps, self.adjoining)
        broken = copy.deepcopy(self.source)
        broken["navigationTopology"]["links"][0]["to"] = "node_decorative_open_ocean"
        with self.assertRaisesRegex(geography.GeographyError, "decorative water"):
            geography.validate(broken, self.world, self.maps, self.adjoining)
        broken = copy.deepcopy(self.source)
        broken["instances"][0]["complexity"]["waterBodies"] = 6
        with self.assertRaisesRegex(geography.GeographyError, "complexity budget exceeded"):
            geography.validate(broken, self.world, self.maps, self.adjoining)
        broken = copy.deepcopy(self.source)
        broken["distortions"][0]["adjacencyGapCells"] = 9
        with self.assertRaisesRegex(geography.GeographyError, "adjacency exceeds"):
            geography.validate(broken, self.world, self.maps, self.adjoining)
        broken = copy.deepcopy(self.adjoining)
        broken["east_asia"]["boundaryAnchors"] = []
        with self.assertRaisesRegex(geography.GeographyError, "missing paired global anchor"):
            geography.validate(self.source, self.world, self.maps, broken)


if __name__ == "__main__":
    unittest.main()
