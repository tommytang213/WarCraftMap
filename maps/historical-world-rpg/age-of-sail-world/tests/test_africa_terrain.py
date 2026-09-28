import copy
import importlib.util
import json
import sys
import time
import unittest
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
SHARED = PROJECT.parent / "_shared"
SOURCE = PROJECT / "scenario/terrain/africa.json"
WORLD = PROJECT / "scenario/world/world.json"
spec = importlib.util.spec_from_file_location("africa_terrain_generator", SHARED / "tooling/generate_regional_terrain.py")
generator = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = generator
spec.loader.exec_module(generator)


class AfricaTerrainTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = json.loads(SOURCE.read_text(encoding="utf-8"))
        cls.regional = json.loads(WORLD.read_text(encoding="utf-8"))["regionalGeography"]

    def generate(self):
        return generator.generate(copy.deepcopy(self.source), copy.deepcopy(self.regional))

    @staticmethod
    def cells(result):
        return [value for value, count in result["surfaceEncoding"]["runs"] for _ in range(count)]

    def test_clean_generation_is_byte_deterministic_and_normalized(self):
        first = generator.canonical_bytes(self.generate())
        second = generator.canonical_bytes(self.generate())
        self.assertEqual(first, second)
        self.assertEqual(json.loads(first), json.loads(second))
        self.assertEqual(b"\n", first[-1:])

    def test_landmarks_match_authoritative_reference_within_tolerance(self):
        result = self.generate()
        cells, legend = self.cells(result), result["surfaceEncoding"]["legend"]
        width, height = result["grid"]["width"], result["grid"]["height"]
        for landmark in result["landmarks"]:
            x, y = generator._cell(self.source, landmark["at"])
            tolerance = landmark["toleranceCells"]
            nearby = [cells[cy * width + cx] for cy in range(max(0,y-tolerance),min(height,y+tolerance+1)) for cx in range(max(0,x-tolerance),min(width,x+tolerance+1))]
            self.assertIn(legend[landmark["expectedSurface"]], nearby, landmark["id"])
        self.assertGreater(result["surfaceCounts"]["land"], 6000)
        self.assertGreater(result["surfaceCounts"]["navigable_sea"], 7000)
        self.assertGreater(result["surfaceCounts"]["decorative_water"], 20)

    def test_every_movement_class_and_transition_anchor_is_connected(self):
        result = self.generate()
        graph = result["navigation"]["connectivity"]
        self.assertEqual({"land","naval","amphibious","flying"}, set(graph))
        self.assertIn("africa_mainland_land", graph["land"]["east_transition"])
        self.assertIn("red_sea_navigation", graph["naval"]["north_atlantic_navigation"])
        self.assertIn("madagascar_land", graph["amphibious"]["africa_mainland_land"])
        self.assertIn("indian_islands_land", graph["flying"]["africa_mainland_land"])
        runtime = {anchor["id"]: anchor for anchor in self.regional["anchors"]}
        for anchor in result["transitionAnchors"]:
            target = runtime[anchor.get("runtimeAnchorId", anchor["id"])]
            self.assertEqual("africa", target["regionId"])
            self.assertTrue(set(anchor["movementClasses"]) <= set(target["movementClasses"]))
            if "runtimeAnchorId" not in anchor:
                self.assertEqual(anchor["at"], [target["position"]["x"], target["position"]["y"]])

    def test_corridors_straits_rivers_lakes_and_isolated_water(self):
        result = self.generate()
        features = {item["id"]:item for item in result["features"]["linear"]}
        self.assertEqual({"western_sahara_route","central_sahara_route","nile_sahara_route","red_sea_route"}, {key for key,value in features.items() if value["kind"]=="desert_corridor"})
        self.assertTrue({"sahara","atlas","ethiopian_highlands","east_african_rift","drakensberg"} <= set(features))
        self.assertEqual({"strait_of_gibraltar","bab_el_mandeb","cape_of_good_hope","mozambique_narrows"}, {item["id"] for item in result["features"]["chokepoints"]})
        naval = result["navigation"]["connectivity"]["naval"]
        for river in ("nile_navigation","niger_navigation","congo_navigation"):
            self.assertIn("north_atlantic_navigation", naval[river])
        self.assertEqual(["great_lakes_navigation"], naval["great_lakes_navigation"])
        self.assertNotIn("isolated_water", naval)

    def test_budgets_and_invalid_topology_are_enforced(self):
        started=time.perf_counter(); result=self.generate()
        self.assertLess((time.perf_counter()-started)*1000,self.source["budgets"]["maximumGenerationMilliseconds"])
        self.assertLessEqual(result["statistics"]["encodedRuns"],self.source["budgets"]["maximumEncodedRuns"])
        broken=copy.deepcopy(self.source); broken["transitionAnchors"][0]["zoneId"]="missing"
        with self.assertRaisesRegex(generator.TerrainGenerationError,"zone is missing"): generator.generate(broken,self.regional)
        broken=copy.deepcopy(self.source); broken["chokepoints"][0]["connects"][0]="missing"
        with self.assertRaisesRegex(generator.TerrainGenerationError,"water bodies"): generator.generate(broken,self.regional)

if __name__ == "__main__": unittest.main()
