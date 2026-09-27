import shutil
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "tooling"))

from validate_map_source import (  # noqa: E402
    ValidationError,
    validate,
    validate_compatibility_boundary,
)


class MapSourceValidationTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        source = PROJECT_ROOT / "map"
        self.map_root = Path(self.temp_dir.name) / "map"
        shutil.copytree(source, self.map_root)
        self.manifest = self.map_root / "map-source.json"

    def test_canonical_source_map_is_valid(self):
        map_dir = validate(self.manifest)
        self.assertEqual("AgeOfSailWorld.w3x", map_dir.name)

    def test_missing_required_binary_is_rejected(self):
        (self.map_root / "AgeOfSailWorld.w3x" / "war3map.w3i").unlink()
        with self.assertRaisesRegex(ValidationError, "war3map.w3i"):
            validate(self.manifest)

    def test_malformed_terrain_header_is_rejected(self):
        terrain = self.map_root / "AgeOfSailWorld.w3x" / "war3map.w3e"
        terrain.write_bytes(b"not a terrain file")
        with self.assertRaisesRegex(ValidationError, "war3map.w3e"):
            validate(self.manifest)

    def test_compatibility_boundary_is_present_and_guarded(self):
        validate_compatibility_boundary(PROJECT_ROOT)

    def test_direct_wrapped_native_use_is_rejected(self):
        project = Path(self.temp_dir.name) / "compat-project"
        wurst = project / "wurst"
        wurst.mkdir(parents=True)
        shutil.copy(PROJECT_ROOT / "wurst" / "WC3Compatibility.wurst", wurst)
        shutil.copy(PROJECT_ROOT / "wurst" / "WC3CompatibilityCompileFixture.wurst", wurst)
        (wurst / "Gameplay.wurst").write_text(
            "package Gameplay\nfunction bad(unit u, item i)\n\tUnitEquipItem(u, i)\n",
            encoding="utf-8",
        )
        with self.assertRaisesRegex(ValidationError, "Gameplay.wurst:3: UnitEquipItem"):
            validate_compatibility_boundary(project)


if __name__ == "__main__":
    unittest.main()
