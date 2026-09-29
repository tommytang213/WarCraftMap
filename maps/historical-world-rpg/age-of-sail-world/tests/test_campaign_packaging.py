import hashlib
import json
import shutil
import stat
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
    load_campaign_config,
    validate_campaign,
)
from package_wurst_map import generate, load_config, verify_generated  # noqa: E402

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
        with zipfile.ZipFile(output) as campaign:
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
        verify_generated(base, generated)
        self.manifest.write_text(self.manifest.read_text(encoding="utf-8") + "\n", encoding="utf-8")
        with self.assertRaisesRegex(PackagingError, "stale generated data.*physical-maps.json"):
            verify_generated(base, generated)

    def test_generated_output_detects_stale_southeast_asia_authority(self):
        base = load_config(load_campaign_config(self.manifest).map_config_path)
        generated = self.project / "_build/generated"
        generate(base, generated); verify_generated(base, generated)
        authority = self.project / "scenario/geography/southeast_asia.json"
        authority.write_text(authority.read_text(encoding="utf-8") + "\n", encoding="utf-8")
        with self.assertRaisesRegex(PackagingError, "stale generated data.*southeast_asia.json"):
            verify_generated(base, generated)

    @staticmethod
    def structure(path):
        with zipfile.ZipFile(path) as archive:
            result = {}
            for name in sorted(archive.namelist()):
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
        with zipfile.ZipFile(first) as campaign:
            campaign_manifest = json.loads(campaign.read("campaign-manifest.json"))
            configured_maps = json.loads(self.manifest.read_text(encoding="utf-8"))["physicalMaps"]
            self.assertEqual(len(configured_maps), len(campaign_manifest["maps"]))
            west_bytes = campaign.read("Maps/EuropeWest.w3x")
            southeast_asia_bytes = campaign.read("Maps/SoutheastAsia.w3x")
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
        second = build_campaign(self.manifest, grill=str(self.fake))
        self.assertEqual(first_structure, self.structure(second))
        self.assertEqual(source_hashes, {p.relative_to(self.project): hashlib.sha256(p.read_bytes()).hexdigest() for p in authoritative})


if __name__ == "__main__": unittest.main()
