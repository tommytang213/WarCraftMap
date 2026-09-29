import copy
import importlib.util
import json
import sys
import unittest
from collections import defaultdict
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
SOURCE = PROJECT / "scenario/geography/east_asia.json"
WORLD = PROJECT / "scenario/world/world.json"
SOUTHEAST = PROJECT / "scenario/geography/southeast_asia.json"
spec = importlib.util.spec_from_file_location("east_asia_geography", PROJECT / "tooling/east_asia_geography.py")
geography = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = geography
spec.loader.exec_module(geography)


class EastAsiaGeographyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = json.loads(SOURCE.read_text())
        cls.world = json.loads(WORLD.read_text())
        cls.southeast = json.loads(SOUTHEAST.read_text())

    def test_authoritative_inventory_coordinates_and_budgets_validate(self):
        instances, anchors = geography.validate(copy.deepcopy(self.source), copy.deepcopy(self.world))
        self.assertEqual(6, len(instances))
        self.assertEqual(15, len(anchors))
        self.assertEqual(35, sum(len(item["features"]) for item in instances.values()))
        self.assertEqual(set(geography._base.KINDS) | geography.EXTRA_KINDS, set(self.source["requiredFeatureIds"]))
        for instance in instances.values():
            self.assertIn("complexity", instance)
            self.assertLessEqual(len(instance["features"]), instance["budget"]["maxFeatures"])

    def test_required_physical_geography_and_corridors_are_owned_once(self):
        owned = [(feature["id"], feature["kind"]) for instance in self.source["instances"] for feature in instance["features"]]
        self.assertEqual(len(owned), len({item[0] for item in owned}))
        declared = {(feature_id, kind) for kind, ids in self.source["requiredFeatureIds"].items() for feature_id in ids}
        self.assertEqual(declared, set(owned))
        self.assertEqual(geography.REQUIRED_CORRIDORS, {item["id"] for item in self.source["requiredTraversalConnections"]})

    def test_external_stubs_pair_with_southeast_central_asian_pacific_and_americas_contracts(self):
        bindings = {anchor.get("globalAnchorId") for anchor in self.source["boundaryAnchors"] if anchor.get("globalAnchorId")}
        self.assertEqual({"east_asia_west", "east_asia_south", "east_asia_east"}, bindings)
        southeast_bindings = {anchor.get("globalAnchorId") for anchor in self.southeast["boundaryAnchors"]}
        self.assertIn("southeast_asia_north", southeast_bindings)
        edges = {edge["id"]: edge for group in ("boundaries", "routes") for edge in self.world["regionalGeography"][group]}
        self.assertTrue(geography.REQUIRED_GLOBAL_EDGES <= set(edges))
        self.assertEqual("pacific", edges["east_asia_pacific_crossing"]["to"]["regionId"])
        self.assertEqual("americas_caribbean", edges["pacific_americas_crossing"]["to"]["regionId"])

    def test_all_movement_modes_and_forbidden_nodes(self):
        nodes = {item["id"]: item for item in self.source["navigationTopology"]["nodes"]}
        links = self.source["navigationTopology"]["links"]
        for corridor in self.source["requiredTraversalConnections"]:
            for mode in corridor["movementClasses"]:
                self.assertIn(corridor["toNodeId"], geography._reachable(nodes, links, corridor["fromNodeId"], mode))
        self.assertIn("node_north_china", geography._reachable(nodes, links, "node_central_asia_gate", "land"))
        self.assertIn("node_north_pacific", geography._reachable(nodes, links, "node_south_china_sea", "naval"))
        self.assertIn("node_japan_coast", geography._reachable(nodes, links, "node_korea_land", "amphibious"))
        self.assertIn("node_north_pacific", geography._reachable(nodes, links, "node_central_asia_gate", "flying"))
        self.assertNotIn("node_gobi_isolated_water", geography._reachable(nodes, links, "node_south_china_sea", "naval"))
        self.assertNotIn("node_tibetan_barrier", geography._reachable(nodes, links, "node_central_asia_gate", "land"))

    def test_generation_is_deterministic_and_normalized(self):
        first = geography.generate(copy.deepcopy(self.source), copy.deepcopy(self.world))
        second = geography.generate(copy.deepcopy(self.source), copy.deepcopy(self.world))
        self.assertEqual(first, second)
        self.assertEqual(first, json.dumps(json.loads(first), indent=2, sort_keys=True, separators=(",", ": ")) + "\n")
        generated = json.loads(first)
        for output in generated["instances"]:
            owner = next(item for item in self.source["instances"] if item["id"] == output["id"])
            originals = {item["id"]: item for item in owner["features"]}
            for feature in output["features"]:
                expected = [geography._base.transform_point(owner, point, 2) for point in originals[feature["id"]]["points"]]
                self.assertEqual(expected, feature["localPoints"])

    def test_invalid_seams_routes_density_and_complexity_have_bounded_diagnostics(self):
        broken = copy.deepcopy(self.source)
        broken["boundaryAnchors"][1]["source"][0] += 0.1
        with self.assertRaisesRegex(geography.GeographyError, "seam discontinuity"):
            geography.validate(broken, self.world)
        broken = copy.deepcopy(self.source)
        broken["navigationTopology"]["links"][0]["to"] = "node_tibetan_barrier"
        with self.assertRaisesRegex(geography.GeographyError, "impassable barriers"):
            geography.validate(broken, self.world)
        broken = copy.deepcopy(self.source)
        broken["instances"][0]["budget"]["maxControlPoints"] = 1
        with self.assertRaisesRegex(geography.GeographyError, "control points exceed"):
            geography.validate(broken, self.world)
        broken = copy.deepcopy(self.source)
        broken["instances"][0]["complexity"]["generationWeight"] = 1.1
        with self.assertRaisesRegex(geography.GeographyError, "complexity budget exceeded"):
            geography.validate(broken, self.world)


if __name__ == "__main__":
    unittest.main()
