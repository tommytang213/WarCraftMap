import re
import unittest
from pathlib import Path


REPOSITORY = Path(__file__).resolve().parents[4]
WORKFLOW = REPOSITORY / ".github" / "workflows" / "map-build.yml"


class MapArtifactWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workflow = WORKFLOW.read_text(encoding="utf-8")

    def test_validation_and_typecheck_precede_upload(self):
        source_validation = self.workflow.index("validate_map_source.py")
        package = self.workflow.index("./tooling/package_release.sh")
        upload = self.workflow.index("actions/upload-artifact@")
        self.assertLess(source_validation, package)
        self.assertLess(package, upload)
        packager = REPOSITORY / "maps/historical-world-rpg/_shared/tooling/package_wurst_map.py"
        self.assertIn('[executable, "typecheck"]', packager.read_text())

    def test_expected_artifact_path_name_and_retention_are_fixed(self):
        self.assertIn("_build/release/AgeOfSailWorld.w3x", self.workflow)
        self.assertIn("name: age-of-sail-world-map", self.workflow)
        self.assertRegex(self.workflow, r"retention-days:\s+14\b")
        self.assertIn("if-no-files-found: error", self.workflow)

    def test_actions_and_wurst_image_are_immutable(self):
        actions = re.findall(r"uses:\s+[^\s@]+@([^\s#]+)", self.workflow)
        self.assertGreaterEqual(len(actions), 2)
        self.assertTrue(all(re.fullmatch(r"[0-9a-f]{40}", revision) for revision in actions))
        self.assertRegex(self.workflow, r"frotty/wurstscript@sha256:[0-9a-f]{64}")
        config = REPOSITORY / "maps/historical-world-rpg/age-of-sail-world/wurst.build"
        self.assertIn("wc3Patch: v3.0", config.read_text())
        self.assertIn("scriptMode: LUA", config.read_text())


if __name__ == "__main__":
    unittest.main()
