import copy
import importlib.util
import json
import re
import sys
import unittest
from collections import defaultdict, deque
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[1]
SOURCE = PROJECT / "scenario/geography/middle_east_india.json"
WORLD = PROJECT / "scenario/world/world.json"
spec = importlib.util.spec_from_file_location("middle_east_india_geography", PROJECT / "tooling/middle_east_india_geography.py")
geography = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = geography
spec.loader.exec_module(geography)


class MiddleEastIndiaGeographyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = json.loads(SOURCE.read_text(encoding="utf-8"))
        cls.world = json.loads(WORLD.read_text(encoding="utf-8"))

    def test_stable_ids_ranges_inventory_and_budgets(self):
        instances, anchors = geography.validate(copy.deepcopy(self.source), copy.deepcopy(self.world))
        ids = list(instances) + list(anchors) + [d["id"] for d in self.source["distortions"]]
        ids += [f["id"] for instance in self.source["instances"] for f in instance["features"]]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(all(re.fullmatch(r"[a-z][a-z0-9]*(?:_[a-z0-9]+)*", ident) for ident in ids))
        self.assertEqual(7, len(instances))
        for instance in self.source["instances"]:
            self.assertLessEqual(len(instance["features"]), instance["budget"]["maxFeatures"])
            self.assertLessEqual(sum(len(feature["points"]) for feature in instance["features"]), instance["budget"]["maxControlPoints"])
            self.assertLessEqual(sum(a["instanceId"] == instance["id"] for a in anchors.values()), instance["budget"]["maxBoundaryAnchors"])

    def test_required_geographic_coverage_and_adjoining_routes(self):
        expected = {
            "coastline": 6, "island": 5, "strait": 5, "river": 9,
            "mountain_barrier": 7, "desert_barrier": 5,
        }
        self.assertEqual(expected, {kind: len(ids) for kind, ids in self.source["requiredFeatureIds"].items()})
        required = {ident for values in self.source["requiredFeatureIds"].values() for ident in values}
        self.assertTrue({"strait_suez_sinai", "strait_bab_el_mandeb", "strait_hormuz", "river_indus", "river_ganges", "mountains_himalaya", "desert_arabian"} <= required)
        anchors = {anchor["id"]: anchor for anchor in self.source["boundaryAnchors"]}
        bindings = defaultdict(list)
        for anchor in anchors.values():
            if anchor.get("globalAnchorId"):
                bindings[anchor["globalAnchorId"]].append(anchor)
        self.assertEqual({"middle_east_india_west", "middle_east_india_north", "middle_east_india_east"}, set(bindings))
        self.assertEqual(2, len(bindings["middle_east_india_west"]))  # Mediterranean and Red Sea approaches.
        self.assertEqual(geography.REQUIRED_CONNECTIONS, {route["id"] for route in self.source["requiredTraversalConnections"]})
        graph_edges = {edge["id"] for edge in self.world["regionalGeography"]["boundaries"]}
        self.assertTrue({"europe_middle_east_boundary", "africa_middle_east_boundary", "middle_east_central_asia_boundary", "middle_east_southeast_asia_boundary"} <= graph_edges)

    def test_anchor_pairs_seams_movement_and_global_references(self):
        anchors = {anchor["id"]: anchor for anchor in self.source["boundaryAnchors"]}
        graph_anchors = {anchor["id"]: anchor for anchor in self.world["regionalGeography"]["anchors"]}
        for anchor in anchors.values():
            if "pairId" in anchor:
                pair = anchors[anchor["pairId"]]
                self.assertEqual(anchor["id"], pair["pairId"])
                self.assertEqual(anchor["source"], pair["source"])
                self.assertEqual(anchor["movementClasses"], pair["movementClasses"])
            else:
                target = graph_anchors[anchor["globalAnchorId"]]
                self.assertEqual("middle_east_india", target["regionId"])
                self.assertTrue(set(anchor["movementClasses"]) <= set(target["movementClasses"]))

    def test_instance_and_global_graphs_are_connected(self):
        graph = defaultdict(set)
        by_id = {anchor["id"]: anchor for anchor in self.source["boundaryAnchors"]}
        for anchor in by_id.values():
            if "pairId" in anchor:
                graph[anchor["instanceId"]].add(by_id[anchor["pairId"]]["instanceId"])
        pending, found = deque([self.source["instances"][0]["id"]]), set()
        while pending:
            current = pending.popleft()
            if current not in found:
                found.add(current); pending.extend(graph[current] - found)
        self.assertEqual({instance["id"] for instance in self.source["instances"]}, found)
        regions = {item["id"] for item in self.world["regionalGeography"]["regions"]}
        regional = defaultdict(set)
        for edge in self.world["regionalGeography"]["boundaries"] + self.world["regionalGeography"]["routes"]:
            a, b = edge["from"]["regionId"], edge["to"]["regionId"]
            regional[a].add(b); regional[b].add(a)
        pending, found = deque(["middle_east_india"]), set()
        while pending:
            current = pending.popleft()
            if current not in found:
                found.add(current); pending.extend(regional[current] - found)
        self.assertEqual(regions, found)

    def test_deterministic_transform_and_generated_output_equivalence(self):
        first = geography.generate(copy.deepcopy(self.source), copy.deepcopy(self.world))
        second = geography.generate(copy.deepcopy(self.source), copy.deepcopy(self.world))
        self.assertEqual(first, second)
        generated = json.loads(first)
        source_features = {f["id"]: (instance, f) for instance in self.source["instances"] for f in instance["features"]}
        for instance in generated["instances"]:
            for feature in instance["features"]:
                owner, original = source_features[feature["id"]]
                expected = [geography._base.transform_point(owner, point, self.source["coordinateRules"]["precisionDecimals"]) for point in original["points"]]
                self.assertEqual(expected, feature["localPoints"])

    def test_distortion_tolerances_and_invalid_budgets_are_rejected(self):
        broken = copy.deepcopy(self.source)
        broken["distortions"][0]["orientationDeltaDegrees"] = 13
        with self.assertRaisesRegex(geography.GeographyError, "orientation exceeds"):
            geography.validate(broken, self.world)
        broken = copy.deepcopy(self.source)
        broken["instances"][0]["budget"]["maxControlPoints"] = 1
        with self.assertRaisesRegex(geography.GeographyError, "control points exceed"):
            geography.validate(broken, self.world)
        broken = copy.deepcopy(self.source)
        broken["boundaryAnchors"][1]["source"][0] += 0.1
        with self.assertRaisesRegex(geography.GeographyError, "seam discontinuity"):
            geography.validate(broken, self.world)


if __name__ == "__main__":
    unittest.main()
