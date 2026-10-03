import hashlib
import json
import shutil
import stat
import struct
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT.parent / "_shared" / "tooling"))
from package_wurst_campaign import (  # noqa: E402
    PackagingError,
    _localize_runtime,
    build_campaign,
    inspect_campaign,
    load_campaign_config,
    validate_campaign,
)
from package_wurst_map import generate, load_config, verify_generated  # noqa: E402
from warcraft_campaign import MpqReader, campaign_metadata, parse_campaign_metadata  # noqa: E402

FAKE_GRILL = r'''#!/usr/bin/env python3
import pathlib, sys, zipfile
root = pathlib.Path.cwd()
with (root.parent / "commands.txt").open("a") as log: log.write(" ".join(sys.argv[1:]) + "\n")
if sys.argv[1] == "build":
    source = root / sys.argv[2]
    out = root / "_build"; out.mkdir(parents=True, exist_ok=True)
    generated = (root / "wurst/ScenarioData.wurst").read_text()
    bootstrap = (root / "wurst/Bootstrap.wurst").read_text()
    lua = "Age of Sail: The World - development bootstrap loaded.\nWC3Compatibility: required Warcraft III v3.0\n" + generated + bootstrap
    with zipfile.ZipFile(out / "tool-output.w3x", "w") as archive:
        for path in sorted(source.rglob("*")):
            if path.is_file(): archive.write(path, path.relative_to(source).as_posix())
        archive.writestr("war3map.lua", lua)
'''


class CampaignPackagingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        category = Path(self.temp.name) / "historical-world-rpg"
        self.project = category / "age-of-sail-world"
        shutil.copytree(PROJECT_ROOT.parent / "_shared", category / "_shared")
        shutil.copytree(PROJECT_ROOT, self.project, ignore=shutil.ignore_patterns("_build", ".wurst", "__pycache__"))
        self.manifest = self.project / "physical-maps.json"
        self.fake = self.project / "fake-grill"
        self.fake.write_text(FAKE_GRILL, encoding="utf-8")
        self.fake.chmod(self.fake.stat().st_mode | stat.S_IXUSR)

    def rewrite(self, mutate):
        data = json.loads(self.manifest.read_text(encoding="utf-8")); mutate(data)
        self.manifest.write_text(json.dumps(data), encoding="utf-8")

    def assert_invalid(self, mutate, message):
        self.rewrite(mutate)
        with self.assertRaisesRegex(PackagingError, message):
            validate_campaign(load_campaign_config(self.manifest))

    def test_manifest_supports_split_logical_region_and_valid_single_map_compatibility(self):
        config = load_campaign_config(self.manifest); validate_campaign(config)
        self.assertEqual(2, sum("europe" in item.logical_region_ids for item in config.maps))
        raw = json.loads(self.manifest.read_text(encoding="utf-8"))
        content = raw["physicalMaps"][1:]
        content[0]["id"] = "whole_world"; content[0]["packagePath"] = "Maps/WholeWorld.w3x"
        for key in ("logicalRegionIds", "regionalInstanceIds", "generatedTerrainIds"):
            content[0]["assignments"][key] = sorted({v for item in content for v in item["assignments"][key]})
        content[0]["terrainBudget"] = {"maximumCells": 110000, "maximumOutputBytes": 5242880}
        raw["physicalMaps"] = [raw["physicalMaps"][0], content[0]]
        self.manifest.write_text(json.dumps(raw), encoding="utf-8")
        validate_campaign(load_campaign_config(self.manifest))

    def test_duplicate_ids_and_package_collisions_are_rejected(self):
        self.rewrite(lambda d: d["physicalMaps"][1].update(id=d["physicalMaps"][0]["id"]))
        with self.assertRaisesRegex(PackagingError, "duplicate physical map IDs"): load_campaign_config(self.manifest)
        shutil.copy2(PROJECT_ROOT / "physical-maps.json", self.manifest)
        self.rewrite(lambda d: d["physicalMaps"][1].update(packagePath=d["physicalMaps"][0]["packagePath"].lower()))
        with self.assertRaisesRegex(PackagingError, "conflicting package paths"): load_campaign_config(self.manifest)

    def test_generic_zip_renamed_to_w3n_is_rejected(self):
        fake_campaign = self.project / "generic.w3n"
        with zipfile.ZipFile(fake_campaign, "w") as archive:
            archive.writestr("war3campaign.w3f", b"not campaign metadata")
        with self.assertRaisesRegex(PackagingError, "invalid Warcraft MPQ campaign"):
            inspect_campaign(load_campaign_config(self.manifest), fake_campaign)

    def test_warcraft_3_campaign_metadata_matches_independent_war3net_layout(self):
        """Independent cursor mirrors War3Net, not the production parser."""
        chapters = [("Begin the Campaign", "Maps/AgeOfSailWorld.w3x"), ("Africa", "Maps/Africa.w3x")]
        data = campaign_metadata("Age of Sail: The World", "description", chapters)
        at = 0
        def i32():
            nonlocal at
            value = struct.unpack_from("<i", data, at)[0]; at += 4; return value
        def f32():
            nonlocal at
            value = struct.unpack_from("<f", data, at)[0]; at += 4; return value
        def text():
            nonlocal at
            end = data.index(0, at); value = data[at:end].decode(); at = end + 1; return value
        self.assertEqual((3, 1, 7000), (i32(), i32(), i32()))
        self.assertEqual(("Age of Sail: The World", "Normal", "WarcraftMap contributors", "description"), tuple(text() for _ in range(4)))
        self.assertEqual((2, -1, "", "", -1, ""), (i32(), i32(), text(), text(), i32(), text()))
        self.assertEqual(0, i32()); self.assertEqual((0.0, 10000.0, 0.0), tuple(f32() for _ in range(3)))
        self.assertEqual(b"\0\0\0\0", data[at:at + 4]); at += 4
        self.assertEqual(0, i32())
        self.assertEqual((0.0,) * 5, tuple(f32() for _ in range(5)))
        self.assertEqual((0, 0), (i32(), i32()))  # draw-over-sky, background version
        self.assertEqual(2, i32())
        buttons = [(i32(), text(), text(), text()) for _ in range(2)]
        self.assertEqual([(1, t, t, p) for t, p in chapters], buttons)
        self.assertEqual(2, i32())
        self.assertEqual([("", p) for _, p in chapters], [(text(), text()) for _ in range(2)])
        self.assertEqual(len(data), at)

    def test_old_rc2_malformed_metadata_fixture_is_rejected(self):
        fixture = Path(__file__).parent / "fixtures/malformed-rc2-war3campaign.w3f.hex"
        with self.assertRaises(ValueError):
            parse_campaign_metadata(bytes.fromhex(fixture.read_text().strip()))

    def test_known_war3net_3_0_fixture_is_accepted(self):
        fixture = Path(__file__).parent / "fixtures/war3net-campaign-3.0.0-war3campaign.w3f.hex"
        metadata = parse_campaign_metadata(bytes.fromhex(fixture.read_text().strip()))
        self.assertEqual((3, 7000, 1),
                         (metadata["version"], metadata["editorVersion"], metadata["backgroundVersion"]))
        self.assertEqual([("", "patch_3.0.0_1.w3x")], metadata["maps"])
        self.assertEqual("patch_3.0.0_1.w3x", metadata["buttons"][0][3])

    def test_missing_source_invalid_assignment_and_unassigned_content_are_rejected(self):
        self.assert_invalid(lambda d: d["physicalMaps"][1].update(sourceMap="map/missing.w3x"), "missing source input")
        shutil.copy2(PROJECT_ROOT / "physical-maps.json", self.manifest)
        self.assert_invalid(lambda d: d["physicalMaps"][1]["assignments"]["regionalInstanceIds"].append("not_a_region"), "invalid region assignment")
        shutil.copy2(PROJECT_ROOT / "physical-maps.json", self.manifest)
        self.assert_invalid(lambda d: d["physicalMaps"][1]["assignments"]["regionalInstanceIds"].pop(), "unassigned required content")

    def test_terrain_budget_failure_is_map_scoped(self):
        self.rewrite(lambda d: d["physicalMaps"][1]["terrainBudget"].update(maximumCells=1))
        with self.assertRaisesRegex(PackagingError, r"terrain budget stage failed \[europe_west\]"):
            build_campaign(self.manifest, grill=str(self.fake))

    def test_each_physical_map_uses_its_configured_source_map(self):
        alternate = self.project / "map/AlternateAfrica.w3x"
        shutil.copytree(self.project / "map/AgeOfSailWorld.w3x", alternate)
        (alternate / "physical-source-marker.txt").write_text("africa source\n", encoding="utf-8")
        self.rewrite(lambda d: d["physicalMaps"][3].update(sourceMap="map/AlternateAfrica.w3x"))
        output = build_campaign(self.manifest, grill=str(self.fake))
        campaign = MpqReader(output)
        africa_path = self.project / "africa.w3x"
        europe_path = self.project / "europe.w3x"
        africa_path.write_bytes(campaign.read("Maps/Africa.w3x"))
        europe_path.write_bytes(campaign.read("Maps/EuropeWest.w3x"))
        with zipfile.ZipFile(africa_path) as africa, zipfile.ZipFile(europe_path) as europe:
            self.assertIn("physical-source-marker.txt", africa.namelist())
            self.assertNotIn("physical-source-marker.txt", europe.namelist())

    def test_map_local_generated_output_detects_stale_manifest(self):
        campaign = load_campaign_config(self.manifest)
        base = load_config(campaign.map_config_path)
        generated = self.project / "_build/maps/europe_west/generated"
        generate(base, generated)
        world = validate_campaign(campaign)
        _localize_runtime(campaign, world, campaign.maps[1], generated)
        generated_wurst = (generated / "ScenarioData.wurst").read_text()
        self.assertNotIn("\tskip\n", generated_wurst)
        self.assertEqual(len(world["polities"]), generated_wurst.count("\tcontroller.add("))
        verify_generated(base, generated)
        self.manifest.write_text(self.manifest.read_text(encoding="utf-8") + "\n", encoding="utf-8")
        with self.assertRaisesRegex(PackagingError, "stale generated data.*physical-maps.json"):
            verify_generated(base, generated)

    def test_every_packaged_map_has_one_authoritative_runtime_identity(self):
        campaign = load_campaign_config(self.manifest)
        world = validate_campaign(campaign)
        base = load_config(campaign.map_config_path)
        bootstrap = (self.project / "wurst/Bootstrap.wurst").read_text(encoding="utf-8")
        self.assertNotIn("MAP_INTERNAL_ID", bootstrap)
        self.assertIn("initializePlayableCampaignRuntime(commands, PHYSICAL_MAP_ID", bootstrap)
        for physical in campaign.maps:
            generated = self.project / "_build/identity" / physical.id
            generate(base, generated)
            _localize_runtime(campaign, world, physical, generated)
            scenario = (generated / "ScenarioData.wurst").read_text(encoding="utf-8")
            declaration = f'public constant string PHYSICAL_MAP_ID = "{physical.id}"'
            self.assertEqual(1, scenario.count("public constant string PHYSICAL_MAP_ID"))
            self.assertIn(declaration, scenario)
            runtime = json.loads((generated / "scenario-runtime.json").read_text(encoding="utf-8"))
            self.assertEqual(physical.id, runtime["physicalMap"]["id"])

    def test_bootstrap_alone_registers_and_defers_origin_selection(self):
        bootstrap = (self.project / "wurst/Bootstrap.wurst").read_text(encoding="utf-8")
        gate = 'if PHYSICAL_MAP_ID == "bootstrap_runtime_validation"'
        self.assertEqual(2, bootstrap.count(gate))
        registration = bootstrap.index("registerOriginSelection(commands, bootstrapOriginSelection)")
        self.assertLess(bootstrap.rfind(gate, 0, registration), registration)
        self.assertIn("TimerStart(CreateTimer(), 0., false, function openBootstrapOriginSelection)", bootstrap)
        callback = bootstrap[bootstrap.index("function openBootstrapOriginSelection"):bootstrap.index("/** Applies")]
        self.assertIn("PauseGame(true)", callback)
        self.assertIn("bootstrapOriginSelection.showPage(1)", callback)
        self.assertNotIn("PauseGame(true)", bootstrap[bootstrap.index("init\n"):bootstrap.index("if SCENARIO_SCHEMA_VERSION")])

    def test_generated_output_detects_stale_southeast_asia_authority(self):
        base = load_config(load_campaign_config(self.manifest).map_config_path)
        generated = self.project / "_build/generated"
        generate(base, generated); verify_generated(base, generated)
        authority = self.project / "scenario/geography/southeast_asia.json"
        authority.write_text(authority.read_text(encoding="utf-8") + "\n", encoding="utf-8")
        with self.assertRaisesRegex(PackagingError, "stale generated data.*southeast_asia.json"):
            verify_generated(base, generated)

    def test_generated_output_detects_stale_americas_authority(self):
        base = load_config(load_campaign_config(self.manifest).map_config_path)
        generated = self.project / "_build/generated-americas"
        generate(base, generated); verify_generated(base, generated)
        authority = self.project / "scenario/geography/americas_caribbean.json"
        authority.write_text(authority.read_text(encoding="utf-8") + "\n", encoding="utf-8")
        with self.assertRaisesRegex(PackagingError, "stale generated data.*americas_caribbean.json"):
            verify_generated(base, generated)

    def test_generated_output_detects_stale_pacific_authority(self):
        base = load_config(load_campaign_config(self.manifest).map_config_path)
        generated = self.project / "_build/generated-pacific"
        generate(base, generated); verify_generated(base, generated)
        authority = self.project / "scenario/geography/pacific.json"
        authority.write_text(authority.read_text(encoding="utf-8") + "\n", encoding="utf-8")
        with self.assertRaisesRegex(PackagingError, "stale generated data.*pacific.json"):
            verify_generated(base, generated)

    @staticmethod
    def structure(path):
        archive = MpqReader(path)
        config = load_campaign_config(path.parents[2] / "physical-maps.json")
        result = {}
        for name in ["war3campaign.w3f", "campaign-manifest.json", *(x.package_path for x in config.maps)]:
                value = archive.read(name)
                if name == "campaign-manifest.json":
                    manifest = json.loads(value)
                    for item in manifest["maps"]: item.pop("sha256", None)
                    value = json.dumps(manifest, sort_keys=True).encode()
                elif name.endswith(".w3x"):
                    nested = Path(tempfile.gettempdir()) / (hashlib.sha256(value).hexdigest() + ".w3x")
                    nested.write_bytes(value)
                    try:
                        with zipfile.ZipFile(nested) as map_archive:
                            value = json.dumps({entry: hashlib.sha256(map_archive.read(entry)).hexdigest() for entry in sorted(map_archive.namelist())}, sort_keys=True).encode()
                    finally:
                        nested.unlink()
                result[name] = hashlib.sha256(value).hexdigest()
        return result

    def test_clean_builds_are_deterministic_local_and_structurally_complete(self):
        authoritative = [p for root in (self.project / "map", self.project / "scenario") for p in root.rglob("*") if p.is_file()]
        source_hashes = {p.relative_to(self.project): hashlib.sha256(p.read_bytes()).hexdigest() for p in authoritative}
        first = build_campaign(self.manifest, grill=str(self.fake)); first_structure = self.structure(first)
        # Embedded headless-test maps are ZIPs, so zipfile may find their EOCD;
        # the outer campaign itself must nevertheless begin with an MPQ header.
        # War3Net's known campaign_3.0.0.w3n fixture is likewise raw MPQ at
        # byte zero (no HM3W map wrapper or appended signature footer).
        self.assertEqual(b"MPQ\x1a", first.read_bytes()[:4])
        campaign = MpqReader(first)
        campaign_manifest = json.loads(campaign.read("campaign-manifest.json"))
        metadata = parse_campaign_metadata(campaign.read("war3campaign.w3f"))
        configured_maps = json.loads(self.manifest.read_text(encoding="utf-8"))["physicalMaps"]
        self.assertEqual("Age of Sail: The World", metadata["name"])
        self.assertTrue(metadata["description"])
        self.assertEqual(3, metadata["version"])
        self.assertEqual(2, metadata["flags"])
        self.assertEqual(configured_maps[0]["packagePath"], metadata["buttons"][0][3])
        self.assertEqual(len(configured_maps), len(campaign_manifest["maps"]))
        for configured in configured_maps:
            packaged = self.project / (configured["id"] + "-identity.w3x")
            packaged.write_bytes(campaign.read(configured["packagePath"]))
            with zipfile.ZipFile(packaged) as map_archive:
                lua = map_archive.read("war3map.lua").decode("utf-8")
            identity = f'public constant string PHYSICAL_MAP_ID = "{configured["id"]}"'
            self.assertEqual(1, lua.count("public constant string PHYSICAL_MAP_ID"))
            self.assertIn(identity, lua)
            self.assertIn("initializePlayableCampaignRuntime(commands, PHYSICAL_MAP_ID", lua)
        west_bytes = campaign.read("Maps/EuropeWest.w3x")
        southeast_asia_bytes = campaign.read("Maps/SoutheastAsia.w3x")
        east_asia_bytes = campaign.read("Maps/EastAsia.w3x")
        local = self.project / "west.w3x"; local.write_bytes(west_bytes)
        with zipfile.ZipFile(local) as west:
            runtime = json.loads(west.read("runtime/scenario-runtime.json"))
            provenance = json.loads(west.read("runtime/provenance.json"))
            self.assertEqual("europe_west", runtime["physicalMap"]["id"])
            self.assertEqual("europe_west", provenance["physicalMap"])
            self.assertIn("runtime/terrain-europe.json", west.namelist())
            self.assertNotIn("runtime/terrain-africa.json", west.namelist())
            self.assertTrue(runtime["settlementDefinitions"])
            self.assertTrue(all(x["regionalInstanceId"] in runtime["physicalMap"]["regionalInstanceIds"] for x in runtime["settlementDefinitions"]))
            self.assertIn("mali_empire", runtime["ids"]["polities"])
        southeast_asia_local = self.project / "southeast-asia.w3x"
        southeast_asia_local.write_bytes(southeast_asia_bytes)
        with zipfile.ZipFile(southeast_asia_local) as southeast_asia:
            runtime = json.loads(southeast_asia.read("runtime/scenario-runtime.json"))
            self.assertEqual("southeast_asia", runtime["physicalMap"]["id"])
            self.assertEqual(7, len(runtime["physicalMap"]["regionalInstanceIds"]))
            self.assertIn("majapahit_empire", {row["id"] for row in runtime["polityDefinitions"]})
            self.assertIn("ava_upper_burma", {row["id"] for row in runtime["provinceDefinitions"]})
            self.assertTrue(all(row["regionalInstanceId"].startswith("sea_") for row in runtime["settlementDefinitions"]))
        east_asia_local = self.project / "east-asia.w3x"
        east_asia_local.write_bytes(east_asia_bytes)
        with zipfile.ZipFile(east_asia_local) as east_asia:
            runtime = json.loads(east_asia.read("runtime/scenario-runtime.json"))
            self.assertEqual("east_asia", runtime["physicalMap"]["id"])
            self.assertEqual(6, len(runtime["physicalMap"]["regionalInstanceIds"]))
            self.assertIn("ming_empire", {row["id"] for row in runtime["polityDefinitions"]})
            self.assertIn("joseon_central_provinces", {row["id"] for row in runtime["provinceDefinitions"]})
            self.assertTrue(all(row["regionalInstanceId"].startswith("east_asia_") for row in runtime["settlementDefinitions"]))
        second = build_campaign(self.manifest, grill=str(self.fake))
        self.assertEqual(first_structure, self.structure(second))
        self.assertEqual(source_hashes, {p.relative_to(self.project): hashlib.sha256(p.read_bytes()).hexdigest() for p in authoritative})


if __name__ == "__main__": unittest.main()
