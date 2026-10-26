"""Preserve the legacy raster while bounding polygon work, not time budgets."""
import copy
import json
import math
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT.parent / "_shared/tooling"))
import generate_regional_terrain as terrain


def legacy_cells(source):
    """Unbounded, cell-first reference retained from the previous generator."""
    width, height = source["grid"]["width"], source["grid"]["height"]
    minimum_x, minimum_y, maximum_x, maximum_y = source["coordinateSystem"]["bounds"]
    cells = []
    for y in range(height):
        py = minimum_y + (y + 0.5) * (maximum_y - minimum_y) / height
        for x in range(width):
            px = minimum_x + (x + 0.5) * (maximum_x - minimum_x) / width
            surface = "void"
            if any(terrain._point_in_polygon(px, py, item["polygon"]) for item in source["waterBodies"] if item["kind"] == "navigable_sea"):
                surface = "navigable_sea"
            if any(terrain._point_in_polygon(px, py, item["polygon"]) for item in source["surfaces"] if item["kind"] == "land"):
                surface = "land"
            if any(terrain._point_in_polygon(px, py, item["polygon"]) for item in source["waterBodies"] if item["kind"] == "navigable_sea" and item.get("overlaysLand") is True):
                surface = "navigable_sea"
            if any(terrain._point_in_polygon(px, py, item["polygon"]) for item in source["waterBodies"] if item["kind"] == "decorative_water"):
                surface = "decorative_water"
            cells.append(terrain.SURFACES[surface])
    return cells


class TerrainRasterizationTests(unittest.TestCase):
    @staticmethod
    def source(polygons, bounds=(-3.0, -2.0, 7.0, 6.0), grid=(20, 16)):
        return {
            "coordinateSystem": {"bounds": list(bounds)},
            "grid": {"width": grid[0], "height": grid[1]},
            "surfaces": [{"kind": "land", "polygon": polygon} for polygon in polygons],
            "waterBodies": [
                {"kind": "navigable_sea", "polygon": [[-10, -10], [10, -10], [10, 10], [-10, 10]]},
                {"kind": "navigable_sea", "overlaysLand": True,
                 "polygon": [[0.25, -1.75], [2.25, -1.75], [2.25, 4.25], [0.25, 4.25]]},
                {"kind": "decorative_water",
                 "polygon": [[0.75, 0.25], [1.75, 0.25], [1.75, 2.25], [0.75, 2.25]]},
            ],
        }

    def test_edge_clipping_winding_and_layer_precedence_match_legacy(self):
        polygons = [
            [[-2.75, -1.75], [4.25, -1.75], [4.25, 5.75], [-2.75, 5.75]],
            [[-8, -4], [1.25, -4], [1.25, 2.25], [-8, 2.25]],
            [[-1.75, -1.25], [5.25, -1.25], [1.25, 2.25], [5.25, 5.25], [-1.75, 5.25]],
            [[20, 20], [22, 20], [22, 22], [20, 22]],
            [[1.25, 1.25], [1.25, 1.25], [1.25, 1.25]],
            [[-2.75, 0.25], [1.25, 0.25], [4.25, 0.25]],
            [[-2.75, -1.75], [3.25, -1.75], [3.25, 3.25], [3.25, 3.25], [-2.75, 3.25]],
            [[math.nextafter(1.25, -math.inf), -1.75],
             [math.nextafter(1.25, math.inf), -1.75],
             [math.nextafter(1.25, math.inf), 5.75]],
        ]
        for index, polygon in enumerate(polygons):
            for reversed_winding in (False, True):
                with self.subTest(polygon=index, reversed=reversed_winding):
                    source = self.source([list(reversed(polygon)) if reversed_winding else polygon])
                    self.assertEqual(legacy_cells(source), terrain._rasterize_surfaces(source))
        source = self.source(polygons)
        self.assertEqual(legacy_cells(source), terrain._rasterize_surfaces(source))

    def test_authored_v1_rasters_match_unbounded_reference(self):
        for name in ("europe", "africa", "middle-east-india"):
            with self.subTest(region=name):
                source = json.loads((PROJECT / f"scenario/terrain/{name}.json").read_text())
                before = copy.deepcopy(source)
                self.assertEqual(legacy_cells(source), terrain._rasterize_surfaces(source))
                self.assertEqual(before, source)

    def test_crossing_cancellation_outside_vertex_bounds_matches_legacy(self):
        # The closing edge crosses just below 0.1 after subtraction/addition,
        # while the vertical edge crosses at 0.1. Vertex-based X clipping would
        # discard the first sample even though the legacy predicate includes it.
        source = self.source([[[0.1, 1], [0.1, 2], [100, 2]]],
                             bounds=(0.09999999999999998, 0.5, 0.1, 2.5), grid=(2, 2))
        expected = legacy_cells(source)
        self.assertEqual(terrain.SURFACES["land"], expected[0])
        self.assertEqual(expected, terrain._rasterize_surfaces(source))

    def test_sparse_polygons_do_not_test_the_whole_grid(self):
        source = self.source([[[2, 2], [3, 2], [3, 3], [2, 3]]], bounds=(0, 0, 128, 128), grid=(128, 128))
        source["waterBodies"] = [{"kind": "navigable_sea", "polygon": [[64, 64], [65, 64], [65, 65], [64, 65]]}]
        expected = legacy_cells(source)
        with patch.object(terrain, "_point_in_polygon", wraps=terrain._point_in_polygon) as predicate:
            self.assertEqual(expected, terrain._rasterize_surfaces(source))
            self.assertLess(predicate.call_count, 128 * 128 // 16)

    def test_generation_time_budget_is_still_enforced(self):
        source = json.loads((PROJECT / "scenario/terrain/europe.json").read_text())
        self.assertEqual(1500, source["budgets"]["maximumGenerationMilliseconds"])
        with patch.object(terrain.time, "perf_counter", side_effect=[10.0, 12.0]):
            with self.assertRaisesRegex(terrain.TerrainGenerationError, "generation time 2000.0ms > 1500ms"):
                terrain.generate(source)


if __name__ == "__main__":
    unittest.main()
