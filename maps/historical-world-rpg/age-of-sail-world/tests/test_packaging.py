import json, re, shutil, stat, sys, tempfile, unittest, zipfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT.parent / "_shared" / "tooling"))
from package_wurst_map import (PackagingError, build, generate, load_config, verify_generated)  # noqa: E402
from wurst_execution_fixture import FAKE_EXECUTION, allow_synthetic_compiler

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
    lua = "function config() end\nfunction main() InitBlizzard() end\nAge of Sail: The World - development bootstrap loaded.\nWC3Compatibility: required Warcraft III v3.0\n" + generated + bootstrap
    (out / "war3map.lua").write_text(lua)
    with zipfile.ZipFile(out / "tool-output.w3x", "w") as archive:
        for path in sorted(source.rglob("*")):
            if path.is_file(): archive.write(path, path.relative_to(source).as_posix())
        archive.writestr("war3map.lua", lua)
'''
FAKE_GRILL = FAKE_GRILL.replace('if sys.argv[1] == "build":', FAKE_EXECUTION + '\nif sys.argv[1] == "build":')

class PackagingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        category = Path(self.temp.name) / "historical-world-rpg"; self.project = category / "age-of-sail-world"
        shutil.copytree(PROJECT_ROOT.parent / "_shared", category / "_shared")
        shutil.copytree(PROJECT_ROOT, self.project, ignore=shutil.ignore_patterns("_build", ".wurst"))
        self.fake = self.project / "fake-grill"; self.fake.write_text(FAKE_GRILL, encoding="utf-8"); self.fake.chmod(self.fake.stat().st_mode | stat.S_IXUSR)
        allow_synthetic_compiler(self, self.fake)

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
        self.assertEqual(["install", "typecheck", "test", "build map/AgeOfSailWorld.w3x"], (self.project / "_build/commands.txt").read_text().splitlines())
        with zipfile.ZipFile(output) as archive:
            names = set(archive.namelist()); lua = archive.read("war3map.lua").decode(); runtime = json.loads(archive.read("runtime/scenario-runtime.json")); terrain = json.loads(archive.read("runtime/terrain-europe.json")); africa = json.loads(archive.read("runtime/terrain-africa.json")); middle_east_india = json.loads(archive.read("runtime/terrain-middle_east_india.json"))
        self.assertIn("war3map.w3i", names); self.assertIn("runtime/provenance.json", names)
        self.assertIn("runtime/terrain-europe.json", names)
        self.assertIn("runtime/terrain-africa.json", names)
        self.assertIn("runtime/terrain-middle_east_india.json", names)
        self.assertEqual("europe", terrain["regionId"]); self.assertEqual("africa", africa["regionId"]); self.assertEqual("middle_east_india", middle_east_india["regionId"])
        self.assertNotIn("SCENARIO_RUNTIME_JSON", lua); self.assertIn("england", runtime["ids"]["polities"])
        self.assertEqual(__import__("hashlib").sha256((self.project / "scenario/world/world.json").read_bytes()).hexdigest(), runtime["sourceSha256"])
        world = json.loads((self.project / "scenario/world/world.json").read_text())
        self.assertEqual({row["id"]: row["availabilityWindow"] for row in world["characters"]}, runtime["characterRecruitmentWindows"])
        self.assertEqual(len(world["polities"]),len(runtime["polityDefinitions"])); self.assertTrue({"england","france","byzantine_empire","mali_empire","ethiopian_empire","kongo_kingdom"}.issubset(item["id"] for item in runtime["polityDefinitions"]))
        self.assertEqual(len(world["provinces"]),len(runtime["provinceDefinitions"])); self.assertTrue({"greater_london","kent","ile_de_france","normandy","manding","shewa","kongo_core"}.issubset(item["id"] for item in runtime["provinceDefinitions"]))
        self.assertEqual(len(world["territorialHoldings"]),len(runtime["provinceHoldings"]))
        self.assertEqual("london",next(x for x in runtime["polityDefinitions"] if x["id"]=="england")["capitalSettlementId"]); self.assertEqual("niani",next(x for x in runtime["polityDefinitions"] if x["id"]=="mali_empire")["capitalSettlementId"])
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
        self.assertNotIn("SCENARIO_RUNTIME_JSON", generated_wurst)
        self.assertIn("public function configureGeneratedOrigins", generated_wurst)
        self.assertIn("\tskip\n", generated_wurst)
        (generated / "scenario-runtime.json").write_text("stale")
        with self.assertRaisesRegex(PackagingError, "stale generated data"):
            verify_generated(config, generated)

    def test_generated_trade_uses_authoritative_settlement_profiles(self):
        config = load_config(self.project / "package.json"); generated = self.project / "_build/generated"
        generate(config, generated)
        source = (generated / "ScenarioData.wurst").read_text(encoding="utf-8")
        self.assertIn("public function configureGeneratedTrade", source)
        reachable = source.count("runtime.registerSettlement(")
        self.assertGreater(source.count("runtime.registerMarketProfile("), reachable)
        self.assertEqual(reachable, source.count('runtime.registerStore(new TradeStore("warehouse:'))
        self.assertGreater(source.count("function configureGeneratedTrade"), 2)
        goods = {row["id"]: row for row in json.loads((self.project / "scenario/economy/global-goods.json").read_text())["goods"]}
        defaults = json.loads((self.project / "scenario/economy/playable-trade.json").read_text())["marketDefaults"]
        records = re.findall(r'runtime.registerMarketProfile\("([^"]+)","([^"]+)",([^\n]+)\)', source)
        self.assertEqual(source.count("runtime.registerMarketProfile("), len(records))
        for market, good_id, arguments in records:
            with self.subTest(market=market, good=good_id):
                values = list(map(int, arguments.split(",")))
                good = goods[good_id]
                self.assertEqual(11, len(values))
                self.assertEqual(good["basePriceMinor"], values[2])
                self.assertEqual([good["quantityUnitsPerDisplayUnit"], good["priceElasticityPermille"],
                                  defaults["spreadPermille"], defaults["priceFloorPermille"],
                                  defaults["priceCeilingPermille"]], values[6:])
        self.assertNotIn('new RuntimeMarket("starting_settlement","Grain",100,10000,10,8)', source)
        self.assertIn('runtime.registerMarketProfile("london","grain"', source)

    def test_changed_authoritative_input_is_rejected(self):
        config = load_config(self.project / "package.json"); generated = self.project / "_build/generated"
        generate(config, generated)
        with (self.project / "wurst.build").open("a", encoding="utf-8") as build_file:
            build_file.write("\n# changed after generation\n")
        with self.assertRaisesRegex(PackagingError, "stale generated data.*wurst.build"):
            verify_generated(config, generated)

    def test_explicit_compiler_options_are_copied_and_provenance_checked(self):
        from package_wurst_map import _assemble
        config = load_config(self.project / "package.json")
        generated = self.project / "_build/generated"
        args = self.project / "wurst_run.args"
        generate(config, generated)
        compiled = _assemble(config, self.project / "_build/options", generated)
        self.assertEqual(args.read_bytes(), (compiled / args.name).read_bytes())
        flags = args.read_text().splitlines()
        self.assertNotIn("+opt", flags)
        self.assertNotIn("-opt", flags)
        self.assertIn("+inline", flags)
        self.assertIn("+localOptimizations", flags)
        args.write_text(args.read_text() + "\n+opt\n")
        with self.assertRaisesRegex(PackagingError, "stale generated data.*wurst_run.args"):
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
        self.assertIn("*.w3n", ignore)

if __name__ == "__main__": unittest.main()
