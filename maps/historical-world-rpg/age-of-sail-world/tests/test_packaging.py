import json
import os
import shutil
import stat
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SHARED = PROJECT_ROOT.parent / "_shared" / "tooling"
sys.path.insert(0, str(SHARED))

from package_wurst_map import PackagingError, build, load_config, validate_inputs  # noqa: E402


class PackagingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.project = Path(self.temp.name) / "project"
        shutil.copytree(PROJECT_ROOT, self.project, ignore=shutil.ignore_patterns("_build", ".wurst"))
        self.config_path = self.project / "package.json"

    def test_paths_and_output_name_are_resolved_from_scenario_config(self):
        config = load_config(self.config_path)
        self.assertEqual(self.project.resolve(), config.project)
        self.assertEqual("AgeOfSailWorld.w3x", config.output.name)
        self.assertEqual(self.project / "_build" / "release" / "AgeOfSailWorld.w3x", config.output)

    def test_path_escape_is_rejected(self):
        raw = json.loads(self.config_path.read_text())
        raw["sourceMap"] = "../other-map"
        self.config_path.write_text(json.dumps(raw))
        with self.assertRaisesRegex(PackagingError, "escapes"):
            load_config(self.config_path)

    def test_missing_input_and_tool_fail_clearly(self):
        shutil.rmtree(self.project / "scenario")
        config = load_config(self.config_path)
        with self.assertRaisesRegex(PackagingError, "scenario data folder"):
            validate_inputs(config, grill="/bin/true")

    def test_fake_grill_build_produces_named_verified_release(self):
        fake = self.project / "fake-grill"
        fake.write_text("""#!/bin/sh
set -eu
if [ \"$1\" = build ]; then
  mkdir -p _build/work
  printf 'MPQ\\032payload' > _build/work/tool-output.w3x
  printf '%s\\n' 'age-of-sail-world' 'Age of Sail: The World - development bootstrap loaded.' > _build/work/war3map.lua
fi
""")
        fake.chmod(fake.stat().st_mode | stat.S_IXUSR)
        output = build(self.config_path, grill=str(fake))
        self.assertEqual("AgeOfSailWorld.w3x", output.name)
        self.assertTrue(output.is_file())

    def test_generated_artifacts_are_ignored(self):
        ignore = (PROJECT_ROOT.parents[2] / ".gitignore").read_text()
        self.assertIn("**/_build/", ignore)
        self.assertIn("*.w3x", ignore)


if __name__ == "__main__":
    unittest.main()
