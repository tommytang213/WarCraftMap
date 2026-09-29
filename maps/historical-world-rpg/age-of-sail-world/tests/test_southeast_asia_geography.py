import copy
import importlib.util
import json
import re
import sys
import unittest
from collections import defaultdict, deque
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
SOURCE = PROJECT / "scenario/geography/southeast_asia.json"
WORLD = PROJECT / "scenario/world/world.json"
MEI = PROJECT / "scenario/geography/middle_east_india.json"
spec = importlib.util.spec_from_file_location("southeast_asia_geography", PROJECT / "tooling/southeast_asia_geography.py")
geography = importlib.util.module_from_spec(spec); sys.modules[spec.name] = geography; spec.loader.exec_module(geography)


class SoutheastAsiaGeographyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = json.loads(SOURCE.read_text(encoding="utf-8")); cls.world = json.loads(WORLD.read_text(encoding="utf-8"))

    def test_ids_ranges_ownership_density_and_complexity_budgets(self):
        instances, anchors = geography.validate(copy.deepcopy(self.source), copy.deepcopy(self.world))
        ids = list(instances) + list(anchors) + [x["id"] for x in self.source["distortions"]]
        ids += [x["id"] for x in self.source["requiredTraversalConnections"]]
        ids += [x["id"] for x in self.source["navigationTopology"]["nodes"] + self.source["navigationTopology"]["links"]]
        ids += [f["id"] for i in self.source["instances"] for f in i["features"]]
        self.assertEqual(len(ids), len(set(ids))); self.assertTrue(all(re.fullmatch(r"[a-z][a-z0-9]*(?:_[a-z0-9]+)*", x) for x in ids))
        self.assertEqual(7, len(instances))
        for instance in self.source["instances"]:
            self.assertLessEqual(len(instance["features"]), instance["budget"]["maxFeatures"])
            self.assertLessEqual(sum(len(f["points"]) for f in instance["features"]), instance["budget"]["maxControlPoints"])
            self.assertLessEqual(sum(a["instanceId"] == instance["id"] for a in anchors.values()), instance["budget"]["maxBoundaryAnchors"])

    def test_required_geography_and_strategic_corridors(self):
        required = {x for values in self.source["requiredFeatureIds"].values() for x in values}
        self.assertTrue({"strait_malacca", "river_mekong", "island_sumatra", "island_borneo", "archipelago_moluccas", "mountains_annamite"} <= required)
        self.assertEqual(geography.REQUIRED_CORRIDORS, {x["id"] for x in self.source["requiredTraversalConnections"]})

    def test_external_anchors_match_india_east_asia_and_pacific_contracts(self):
        bindings = defaultdict(list)
        for anchor in self.source["boundaryAnchors"]:
            if anchor.get("globalAnchorId"): bindings[anchor["globalAnchorId"]].append(anchor)
        self.assertEqual({"southeast_asia_west", "southeast_asia_north", "southeast_asia_east"}, set(bindings))
        edges = self.world["regionalGeography"]["boundaries"] + self.world["regionalGeography"]["routes"]
        self.assertTrue({"middle_east_southeast_asia_boundary", "southeast_east_asia_boundary", "southeast_asia_pacific_crossing"} <= {e["id"] for e in edges})
        mei = json.loads(MEI.read_text(encoding="utf-8"))
        self.assertIn("middle_east_india_east", {a.get("globalAnchorId") for a in mei["boundaryAnchors"]})
        for edge in edges:
            if edge["id"] in {"middle_east_southeast_asia_boundary", "southeast_east_asia_boundary", "southeast_asia_pacific_crossing"}:
                sea_side = edge["from"] if edge["from"]["regionId"] == "southeast_asia" else edge["to"]
                self.assertIn(sea_side["anchorId"], bindings)

    def test_land_naval_amphibious_and_flying_connectivity(self):
        nodes = {n["id"]: n for n in self.source["navigationTopology"]["nodes"]}; links = self.source["navigationTopology"]["links"]
        for corridor in self.source["requiredTraversalConnections"]:
            for mode in corridor["movementClasses"]:
                self.assertIn(corridor["toNodeId"], geography._reachable(nodes, links, corridor["fromNodeId"], mode))
        self.assertIn("node_eastern_sea", geography._reachable(nodes, links, "node_mainland_east", "amphibious"))
        self.assertIn("node_eastern_sea", geography._reachable(nodes, links, "node_mainland_east", "flying"))
        self.assertIn("node_eastern_sea", geography._reachable(nodes, links, "node_bay_bengal", "naval"))
        self.assertNotIn("node_decorative_inland_water", geography._reachable(nodes, links, "node_bay_bengal", "naval"))
        self.assertNotIn("node_arakan_barrier", geography._reachable(nodes, links, "node_mainland_west", "land"))

    def test_invalid_decorative_water_barrier_and_budget_are_rejected(self):
        broken = copy.deepcopy(self.source); broken["navigationTopology"]["links"][0]["to"] = "node_decorative_inland_water"
        with self.assertRaisesRegex(geography.GeographyError, "decorative water"): geography.validate(broken, self.world)
        broken = copy.deepcopy(self.source); broken["navigationTopology"]["links"][0]["to"] = "node_arakan_barrier"
        with self.assertRaisesRegex(geography.GeographyError, "impassable barriers"): geography.validate(broken, self.world)
        broken = copy.deepcopy(self.source); broken["instances"][0]["budget"]["maxControlPoints"] = 1
        with self.assertRaisesRegex(geography.GeographyError, "control points exceed"): geography.validate(broken, self.world)

    def test_deterministic_transform_and_normalized_output(self):
        first = geography.generate(copy.deepcopy(self.source), copy.deepcopy(self.world)); second = geography.generate(copy.deepcopy(self.source), copy.deepcopy(self.world))
        self.assertEqual(first, second); generated = json.loads(first)
        self.assertEqual(sorted(i["id"] for i in self.source["instances"]), [i["id"] for i in generated["instances"]])

    def test_instance_and_global_graphs_are_connected(self):
        graph = defaultdict(set); anchors = {a["id"]: a for a in self.source["boundaryAnchors"]}
        for anchor in anchors.values():
            if anchor.get("pairId"): graph[anchor["instanceId"]].add(anchors[anchor["pairId"]]["instanceId"])
        pending, found = deque([self.source["instances"][0]["id"]]), set()
        while pending:
            node = pending.popleft()
            if node not in found: found.add(node); pending.extend(graph[node] - found)
        self.assertEqual({i["id"] for i in self.source["instances"]}, found)
        regions = {r["id"] for r in self.world["regionalGeography"]["regions"]}; graph = defaultdict(set)
        for edge in self.world["regionalGeography"]["boundaries"] + self.world["regionalGeography"]["routes"]:
            a, b = edge["from"]["regionId"], edge["to"]["regionId"]; graph[a].add(b); graph[b].add(a)
        pending, found = deque(["southeast_asia"]), set()
        while pending:
            node = pending.popleft()
            if node not in found: found.add(node); pending.extend(graph[node] - found)
        self.assertEqual(regions, found)


if __name__ == "__main__": unittest.main()
