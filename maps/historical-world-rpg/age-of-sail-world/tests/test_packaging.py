import shutil
import stat
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT.parent / "_shared" / "tooling"))

from package_wurst_map import build  # noqa: E402


class PackagingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.project = Path(self.temp.name) / "project"
        shutil.copytree(PROJECT_ROOT, self.project, ignore=shutil.ignore_patterns("_build", ".wurst"))

    def test_fixture_build_contains_map_files_and_lua_bootstrap(self):
        fake = self.project / "fake-grill"
        fake.write_text(
            """#!/usr/bin/env python3
import pathlib, sys, zipfile
pathlib.Path('_build/commands.txt').parent.mkdir(parents=True, exist_ok=True)
with pathlib.Path('_build/commands.txt').open('a') as log:
    log.write(' '.join(sys.argv[1:]) + '\\n')
if sys.argv[1] == 'build':
    root = pathlib.Path('_build/work')
    root.mkdir(parents=True, exist_ok=True)
    lua = 'Age of Sail: The World - development bootstrap loaded.\\n'
    (root / 'war3map.lua').write_text(lua)
    with zipfile.ZipFile(root / 'tool-output.w3x', 'w') as archive:
        for name in ('war3map.w3i', 'war3map.w3e', 'war3map.wpm'):
            archive.writestr(name, b'fixture')
        archive.writestr('war3map.lua', lua)
""",
            encoding="utf-8",
        )
        fake.chmod(fake.stat().st_mode | stat.S_IXUSR)

        output = build(self.project / "package.json", grill=str(fake))

        self.assertEqual("AgeOfSailWorld.w3x", output.name)
        self.assertEqual(
            ["install", "typecheck", "build map/AgeOfSailWorld.w3x"],
            (self.project / "_build/commands.txt").read_text().splitlines(),
        )
        with zipfile.ZipFile(output) as archive:
            self.assertTrue({"war3map.w3i", "war3map.w3e", "war3map.wpm", "war3map.lua"}.issubset(archive.namelist()))
            lua = archive.read("war3map.lua").decode()
        self.assertIn("Age of Sail: The World - development bootstrap loaded.", lua)


if __name__ == "__main__":
    unittest.main()
