import copy
import importlib.util
import json
import sys
import time
import unittest
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
SHARED = PROJECT.parent / "_shared"
SOURCE = PROJECT / "scenario/terrain/europe.json"
WORLD = PROJECT / "scenario/world/world.json"
spec = importlib.util.spec_from_file_location("generate_regional_terrain", SHARED / "tooling/generate_regional_terrain.py")
terrain_generator = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = terrain_generator
spec.loader.exec_module(terrain_generator)


class EuropeTerrainTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = json.loads(SOURCE.read_text(encoding="utf-8"))
        cls.regional = json.loads(WORLD.read_text(encoding="utf-8"))["regionalGeography"]

    def generate(self):
        return terrain_generator.generate(copy.deepcopy(self.source), copy.deepcopy(self.regional))

    @staticmethod
    def cells(generated):
        result = []
        for value, count in generated["surfaceEncoding"]["runs"]:
            result.extend([value] * count)
        return result

    def test_generation_is_byte_deterministic(self):
        first = terrain_generator.canonical_bytes(self.generate())
        second = terrain_generator.canonical_bytes(self.generate())
        self.assertEqual(first, second)

    def test_landmarks_match_reference_within_declared_tolerance(self):
        generated = self.generate()
        cells = self.cells(generated)
        legend = generated["surfaceEncoding"]["legend"]
        width, height = generated["grid"]["width"], generated["grid"]["height"]
        for landmark in generated["landmarks"]:
            x, y = terrain_generator._cell(self.source, landmark["at"])
            tolerance = landmark["toleranceCells"]
            expected = legend[landmark["expectedSurface"]]
            nearby = [cells[cy * width + cx] for cy in range(max(0, y-tolerance), min(height, y+tolerance+1)) for cx in range(max(0, x-tolerance), min(width, x+tolerance+1))]
            self.assertIn(expected, nearby, landmark["id"])
        self.assertGreater(generated["surfaceCounts"]["land"], 4000)
        self.assertGreater(generated["surfaceCounts"]["navigable_sea"], 2500)

    def test_navigation_connectivity_chokepoints_and_isolation(self):
        generated = self.generate()
        naval = generated["navigation"]["connectivity"]["naval"]
        self.assertIn("baltic_navigation", naval["atlantic_navigation"])
        self.assertIn("black_sea_navigation", naval["atlantic_navigation"])
        self.assertNotIn("decorative_lakes", naval)
        amphibious = generated["navigation"]["connectivity"]["amphibious"]
        self.assertIn("british_isles_land", amphibious["europe_mainland_land"])
        self.assertIn("mediterranean_islands_land", amphibious["europe_mainland_land"])
        self.assertEqual({"english_channel", "strait_of_gibraltar", "danish_straits", "bosporus", "strait_of_messina"}, {item["id"] for item in generated["features"]["chokepoints"]})
        self.assertEqual({"rhine_lower_crossing", "danube_vienna_crossing", "danube_lower_crossing"}, {item["id"] for item in generated["features"]["crossings"]})

    def test_transition_seams_align_with_issue_96_runtime(self):
        generated = self.generate()
        runtime = {item["id"]: item for item in self.regional["anchors"]}
        for anchor in generated["transitionAnchors"]:
            runtime_anchor = runtime[anchor.get("runtimeAnchorId", anchor["id"])]
            self.assertEqual("europe", runtime_anchor["regionId"])
            self.assertTrue(set(anchor["movementClasses"]) <= set(runtime_anchor["movementClasses"]))
            if "runtimeAnchorId" not in anchor:
                self.assertEqual(anchor["at"], [runtime_anchor["position"]["x"], runtime_anchor["position"]["y"]])
        first = terrain_generator.canonical_bytes(generated)
        self.assertEqual(first, terrain_generator.canonical_bytes(self.generate()))

    def test_declared_budgets_have_actionable_failures(self):
        started = time.perf_counter()
        generated = self.generate()
        self.assertLess((time.perf_counter() - started) * 1000, self.source["budgets"]["maximumGenerationMilliseconds"])
        self.assertLessEqual(generated["statistics"]["cellCount"], self.source["budgets"]["maximumCells"])
        broken = copy.deepcopy(self.source)
        broken["budgets"]["maximumCells"] = 1
        with self.assertRaisesRegex(terrain_generator.TerrainGenerationError, "budget exceeded: cellCount"):
            terrain_generator.generate(broken, self.regional)

    def test_anchor_drift_and_undeclared_connection_are_rejected(self):
        broken = copy.deepcopy(self.source)
        broken["transitionAnchors"][0]["at"] = [6, 55]
        with self.assertRaisesRegex(terrain_generator.TerrainGenerationError, "does not align"):
            terrain_generator.generate(broken, self.regional)
        broken = copy.deepcopy(self.source)
        broken["connections"][0]["to"] = "missing"
        with self.assertRaisesRegex(terrain_generator.TerrainGenerationError, "missing zone"):
            terrain_generator.generate(broken, self.regional)


if __name__ == "__main__":
    unittest.main()
