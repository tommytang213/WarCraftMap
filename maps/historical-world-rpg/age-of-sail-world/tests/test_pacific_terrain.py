import copy
import importlib.util
import json
import sys
import unittest
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
SOURCE = PROJECT / "scenario/terrain/pacific.json"
AUTHORITY = PROJECT / "scenario/geography/pacific.json"
WORLD = PROJECT / "scenario/world/world.json"
MAPS = PROJECT / "physical-maps.json"
spec = importlib.util.spec_from_file_location("pacific_terrain_generator", PROJECT.parent / "_shared/tooling/generate_regional_terrain.py")
generator = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = generator
spec.loader.exec_module(generator)


class PacificTerrainTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = json.loads(SOURCE.read_text())
        cls.authority = json.loads(AUTHORITY.read_text())
        cls.regional = json.loads(WORLD.read_text())["regionalGeography"]
        cls.maps = json.loads(MAPS.read_text())

    def generate(self, source=None, authority=None):
        return generator.generate(copy.deepcopy(source or self.source), copy.deepcopy(self.regional), copy.deepcopy(authority or self.authority))

    def test_clean_generation_is_deterministic_normalized_complete_and_provenanced(self):
        first = generator.canonical_bytes(self.generate())
        second = generator.canonical_bytes(self.generate())
        self.assertEqual(first, second)
        result = json.loads(first)
        self.assertEqual({item["id"] for item in self.authority["instances"]}, {item["id"] for item in result["instances"]})
        self.assertEqual(6, result["statistics"]["instanceCount"])
        self.assertEqual(64, len(result["provenance"]["terrainSourceSha256"]))
        self.assertEqual(64, len(result["provenance"]["authoritySha256"]))

    def test_islands_navigable_sea_and_isolated_water_are_materialized_within_budgets(self):
        result = self.generate()
        for item in result["instances"]:
            policy = next(row for row in self.source["instancePolicies"] if row["id"] == item["id"])
            self.assertGreater(item["surfaceCounts"]["land"], 0, item["id"])
            self.assertGreater(item["surfaceCounts"]["navigable_sea"], 0, item["id"])
            self.assertGreater(item["surfaceCounts"]["decorative_water"], 0, item["id"])
            self.assertLessEqual(item["statistics"]["cellCount"], policy["budget"]["maximumCells"])
            self.assertLessEqual(item["statistics"]["encodedRuns"], policy["budget"]["maximumEncodedRuns"])
            self.assertLessEqual(item["statistics"]["outputBytes"], policy["budget"]["maximumOutputBytes"])

    def test_routes_landfalls_barriers_island_separation_and_all_movement_classes(self):
        graph = self.generate()["navigation"]["connectivity"]
        for corridor in self.authority["requiredTraversalConnections"]:
            for movement in corridor["movementClasses"]:
                self.assertIn(corridor["toNodeId"], graph[movement][corridor["fromNodeId"]], corridor["id"])
        self.assertEqual(["node_great_barrier_reef"], graph["naval"]["node_great_barrier_reef"])
        self.assertEqual(["node_decorative_open_ocean"], graph["naval"]["node_decorative_open_ocean"])
        self.assertNotIn("node_new_zealand_land", graph["land"]["node_new_guinea_land"])
        self.assertIn("node_new_zealand_land", graph["amphibious"]["node_new_guinea_land"])
        self.assertIn("node_americas_approach", graph["flying"]["node_hawaii_coast"])

    def test_feature_transform_order_orientation_seams_and_entry_anchors_match_authority(self):
        result = self.generate()
        generated = {item["id"]: item for item in result["instances"]}
        for instance in self.authority["instances"]:
            actual = generated[instance["id"]]["features"]
            self.assertEqual([f["id"] for f in instance["features"]], [f["id"] for f in actual])
            origin, scale, offset = instance["transform"]["sourceOrigin"], instance["transform"]["scale"], instance["transform"]["offset"]
            for original, transformed in zip(instance["features"], actual):
                expected = [[round((p[0]-origin[0])*scale[0]+offset[0], 2), round((p[1]-origin[1])*scale[1]+offset[1], 2)] for p in original["points"]]
                self.assertEqual(expected, transformed["points"])
        anchors = {item["id"]: item for item in result["transitionAnchors"]}
        for anchor in anchors.values():
            if anchor.get("pairId"):
                self.assertEqual(anchor["source"], anchors[anchor["pairId"]]["source"])
                self.assertEqual(anchor["movementClasses"], anchors[anchor["pairId"]]["movementClasses"])
        self.assertEqual({"pacific_west", "pacific_east"}, {a["globalAnchorId"] for a in anchors.values() if a.get("globalAnchorId")})

    def test_every_assigned_physical_map_fixture_has_pacific_terrain_and_budget(self):
        generated = self.generate()
        for item in self.maps["physicalMaps"]:
            if "pacific" not in item["assignments"]["logicalRegionIds"] or not item["assignments"]["regionalInstanceIds"]:
                continue
            self.assertEqual(["pacific"], item["assignments"]["generatedTerrainIds"])
            self.assertLessEqual(generated["statistics"]["cellCount"], item["terrainBudget"]["maximumCells"], item["id"])
            self.assertLessEqual(len(generator.canonical_bytes(generated)), item["terrainBudget"]["maximumOutputBytes"], item["id"])

    def test_stale_authority_and_map_scoped_limits_are_rejected(self):
        broken = copy.deepcopy(self.authority)
        broken["boundaryAnchors"][1]["source"] = [0, 0]
        with self.assertRaisesRegex(generator.TerrainGenerationError, "seam correspondence"):
            self.generate(authority=broken)
        broken = copy.deepcopy(self.source)
        broken["instancePolicies"][0]["budget"]["maximumCells"] = 1
        with self.assertRaisesRegex(generator.TerrainGenerationError, "pacific_north_hawaii: cells budget exceeded"):
            self.generate(source=broken)


if __name__ == "__main__":
    unittest.main()
