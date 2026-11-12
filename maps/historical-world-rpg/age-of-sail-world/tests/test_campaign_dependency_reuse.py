"""Verify physical-map builds reuse the same inputs tested by Grill.

Helper-only checks; neither campaign compilation nor native client execution.
"""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT.parent / "_shared" / "tooling"))
from package_wurst_campaign import _install_map_dependencies  # noqa: E402


class CampaignDependencyReuseTests(unittest.TestCase):
    def test_copies_normalized_inputs_not_compiler_cache(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tested, regional = root / "tested", root / "regional"
            (tested / "_build/dependencies/War3Lib").mkdir(parents=True)
            (tested / "_build/dependencies/War3Lib/library.wurst").write_text("tested library")
            (tested / "_build/interpreter-cache").mkdir()
            (tested / "wurst.build").write_text("normalized build")
            (regional / "_build").mkdir(parents=True)
            with patch("package_wurst_campaign._run") as install:
                _install_map_dependencies("grill", regional, tested, "europe")
            self.assertEqual("tested library",
                             (regional / "_build/dependencies/War3Lib/library.wurst").read_text())
            self.assertEqual("normalized build", (regional / "wurst.build").read_text())
            self.assertFalse((regional / "_build/interpreter-cache").exists())
            install.assert_not_called()

    def test_dependency_free_fallback_keeps_installer(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tested, regional = root / "tested", root / "regional"
            tested.mkdir()
            regional.mkdir()
            with patch("package_wurst_campaign._run") as install:
                _install_map_dependencies("grill", regional, tested, "austria")
            install.assert_called_once_with(
                "Wurst dependency installation [austria]",
                ["grill", "install"], regional)

    def test_incomplete_tested_cache_fails_instead_of_silent_redownload(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tested, regional = root / "tested", root / "regional"
            (tested / "_build/dependencies").mkdir(parents=True)
            (regional / "_build").mkdir(parents=True)
            with patch("package_wurst_campaign._run") as install:
                with self.assertRaises(FileNotFoundError):
                    _install_map_dependencies("grill", regional, tested, "europe")
            install.assert_not_called()


if __name__ == "__main__":
    unittest.main()
