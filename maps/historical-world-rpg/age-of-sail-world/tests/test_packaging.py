import json, shutil, stat, sys, tempfile, unittest, zipfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT.parent / "_shared" / "tooling"))
from package_wurst_map import (PackagingError, build, generate, load_config, verify_generated)  # noqa: E402

FAKE_GRILL = r'''#!/usr/bin/env python3
import pathlib, sys, zipfile
root = pathlib.Path.cwd()
log = root.parent / "commands.txt"
with log.open("a") as output: output.write(" ".join(sys.argv[1:]) + "\n")
if sys.argv[1] == "build":
    source = root / sys.argv[2]
    out = root / "_build"; out.mkdir(parents=True, exist_ok=True)
    generated = (root / "wurst/ScenarioData.wurst").read_text()
    bootstrap = (root / "wurst/Bootstrap.wurst").read_text()
    lua = "Age of Sail: The World - development bootstrap loaded.\nWC3Compatibility: required Warcraft III v3.0\n" + generated + bootstrap
    (out / "war3map.lua").write_text(lua)
    with zipfile.ZipFile(out / "tool-output.w3x", "w") as archive:
        for path in sorted(source.rglob("*")):
            if path.is_file(): archive.write(path, path.relative_to(source).as_posix())
        archive.writestr("war3map.lua", lua)
'''

class PackagingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        category = Path(self.temp.name) / "historical-world-rpg"; self.project = category / "age-of-sail-world"
        shutil.copytree(PROJECT_ROOT.parent / "_shared", category / "_shared")
        shutil.copytree(PROJECT_ROOT, self.project, ignore=shutil.ignore_patterns("_build", ".wurst"))
        self.fake = self.project / "fake-grill"; self.fake.write_text(FAKE_GRILL, encoding="utf-8"); self.fake.chmod(self.fake.stat().st_mode | stat.S_IXUSR)

    def test_paths_and_output_name_are_resolved_from_scenario_config(self):
        config = load_config(self.project / "package.json")
        self.assertEqual(self.project.resolve(), config.project)
        self.assertEqual("AgeOfSailWorld.w3x", config.output.name)
        self.assertEqual(self.project / "_build/release/AgeOfSailWorld.w3x", config.output)

    def test_path_escape_is_rejected(self):
        config_path = self.project / "package.json"
        raw = json.loads(config_path.read_text(encoding="utf-8"))
        raw["sourceMap"] = "../other-map"
        config_path.write_text(json.dumps(raw), encoding="utf-8")
        with self.assertRaisesRegex(PackagingError, "escapes"):
            load_config(config_path)

    def test_clean_build_contains_generated_data_lua_metadata_and_no_fixtures(self):
        output = build(self.project / "package.json", grill=str(self.fake))
        self.assertEqual(["install", "typecheck", "build map/AgeOfSailWorld.w3x"], (self.project / "_build/commands.txt").read_text().splitlines())
        with zipfile.ZipFile(output) as archive:
            names = set(archive.namelist()); lua = archive.read("war3map.lua").decode(); runtime = json.loads(archive.read("runtime/scenario-runtime.json")); terrain = json.loads(archive.read("runtime/terrain-europe.json")); africa = json.loads(archive.read("runtime/terrain-africa.json"))
        self.assertIn("war3map.w3i", names); self.assertIn("runtime/provenance.json", names)
        self.assertIn("runtime/terrain-europe.json", names)
        self.assertIn("runtime/terrain-africa.json", names)
        self.assertEqual("europe", terrain["regionId"]); self.assertEqual("africa", africa["regionId"])
        self.assertIn("SCENARIO_RUNTIME_JSON", lua); self.assertIn("england", runtime["ids"]["polities"])
        self.assertEqual(49,len(runtime["polityDefinitions"])); self.assertTrue({"england","france","byzantine_empire"}.issubset(item["id"] for item in runtime["polityDefinitions"]))
        self.assertEqual(62,len(runtime["provinceDefinitions"])); self.assertTrue({"greater_london","kent","ile_de_france","normandy"}.issubset(item["id"] for item in runtime["provinceDefinitions"]))
        self.assertEqual(62,len(runtime["provinceHoldings"]))
        self.assertEqual("london",next(x for x in runtime["polityDefinitions"] if x["id"]=="england")["capitalSettlementId"])
        self.assertFalse(any(name.startswith(("tests/", "fixtures/", "scenario/", "wurst/")) for name in names))

    def test_generation_is_deterministic_and_clean_rebuilds_match(self):
        first_path = build(self.project / "package.json", grill=str(self.fake))
        with zipfile.ZipFile(first_path) as archive:
            first = {name: archive.read(name) for name in sorted(archive.namelist())}
        second_path = build(self.project / "package.json", grill=str(self.fake))
        with zipfile.ZipFile(second_path) as archive:
            second = {name: archive.read(name) for name in sorted(archive.namelist())}
        self.assertEqual(first, second)

    def test_stale_output_is_rejected(self):
        config = load_config(self.project / "package.json"); generated = self.project / "_build/generated"
        generate(config, generated)
        generated_wurst = (generated / "ScenarioData.wurst").read_text()
        self.assertIn("public constant int SCENARIO_SCHEMA_VERSION", generated_wurst)
        self.assertIn("public function getScenarioRuntimeData", generated_wurst)
        (generated / "scenario-runtime.json").write_text("stale")
        with self.assertRaisesRegex(PackagingError, "stale generated data"):
            verify_generated(config, generated)

    def test_changed_authoritative_input_is_rejected(self):
        config = load_config(self.project / "package.json"); generated = self.project / "_build/generated"
        generate(config, generated)
        with (self.project / "wurst.build").open("a", encoding="utf-8") as build_file:
            build_file.write("\n# changed after generation\n")
        with self.assertRaisesRegex(PackagingError, "stale generated data.*wurst.build"):
            verify_generated(config, generated)

    def test_changed_terrain_source_is_rejected(self):
        config = load_config(self.project / "package.json"); generated = self.project / "_build/generated"
        generate(config, generated)
        terrain = self.project / "scenario/terrain/europe.json"
        terrain.write_text(terrain.read_text(encoding="utf-8") + "\n", encoding="utf-8")
        with self.assertRaisesRegex(PackagingError, "stale generated data.*europe.json"):
            verify_generated(config, generated)

    def test_invalid_scenario_reports_validation_stage(self):
        world = self.project / "scenario/world/world.json"; data = json.loads(world.read_text()); data["schemaVersion"] = -1; world.write_text(json.dumps(data))
        with self.assertRaisesRegex(PackagingError, "scenario validation stage failed"):
            build(self.project / "package.json", grill=str(self.fake))

    def test_missing_stage_input_is_actionable(self):
        (self.project / "wurst.build").unlink()
        with self.assertRaisesRegex(PackagingError, "inputs stage failed.*wurst.build"):
            build(self.project / "package.json", grill=str(self.fake))

    def test_generated_artifacts_are_ignored(self):
        ignore = (PROJECT_ROOT.parents[2] / ".gitignore").read_text(encoding="utf-8")
        self.assertIn("**/_build/", ignore)
        self.assertIn("*.w3x", ignore)

if __name__ == "__main__": unittest.main()
