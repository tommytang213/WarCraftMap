"""Launch-sensitive static regressions; none execute retail Warcraft."""
import gzip
import hashlib
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT.parent / "_shared/tooling"))
from materialize_physical_map import _unit
from warcraft_lua_startup import startup_failures
from warcraft_map_info import parse_w3i
from warcraft_map_units import validate_units
from package_wurst_campaign import (_write_campaign, inspect_campaign,
                                    load_campaign_config, PackagingError)
from warcraft_campaign import MpqReader, write_mpq
from package_wurst_map import _inspect, load_config


class LaunchContractTests(unittest.TestCase):
    def test_exact_artifact_704_bootstrap_omits_blizzard_initialization(self):
        script = gzip.decompress((PROJECT / "tests/fixtures/artifact-704-bootstrap.lua.gz").read_bytes())
        self.assertEqual("c17afea376ab8b813cfb0386894a838bdf422c7014de5a38ecf63db4edc92dbe",
                         hashlib.sha256(script).hexdigest())
        self.assertEqual([
            "compiled Lua main must call InitBlizzard once before Wurst package initialization"
        ], startup_failures(script))

    def test_initialization_must_be_in_main_before_packages(self):
        good = "function config() end\nfunction main() InitBlizzard() init_Bootstrap() end"
        self.assertEqual([], startup_failures(good))
        for wrong in (
            good.replace("InitBlizzard()", "-- InitBlizzard()\n"),
            good.replace("InitBlizzard()", "local text = 'InitBlizzard()'"),
            good.replace("InitBlizzard()", "local text = [=[InitBlizzard()]=]"),
            good.replace("InitBlizzard()", "--[==[InitBlizzard()]==]"),
            good.replace("InitBlizzard()", "if false then InitBlizzard() end"),
            good.replace("InitBlizzard()", "local function unused() InitBlizzard() end"),
            good.replace("InitBlizzard() init_Bootstrap()", "init_Bootstrap() InitBlizzard()"),
            good.replace("config() end", "config() InitBlizzard() end"),
            good.replace("function config() end", ""),
            good.replace("function main()", "local function main()"),
            "function helper() " + good + " end",
            good.replace("InitBlizzard()", "return; InitBlizzard()"),
            good.replace("InitBlizzard()", "local ignored = false and InitBlizzard()"),
            good.replace("InitBlizzard()", "unused.InitBlizzard()"),
            good.replace("InitBlizzard()", "local InitBlizzard = function() end; InitBlizzard()"),
        ):
            with self.subTest(script=wrong):
                self.assertTrue(startup_failures(wrong))

    def test_exact_artifact_704_regional_records_reference_absent_item_table(self):
        data = gzip.decompress((PROJECT / "tests/fixtures/artifact-704-europe-units.doo.gz").read_bytes())
        self.assertEqual("baa0141352d4b3f23559761dfaf4dce21a18269ace494c0a68b9d493d31a8a02",
                         hashlib.sha256(data).hexdigest())
        with self.assertRaisesRegex(ValueError, "missing W3I item table"):
            validate_units(data)

    def test_mpq_inspection_checks_archived_lua_not_intermediate_output(self):
        config = load_config(PROJECT / "package.json")
        broken = gzip.decompress((PROJECT / "tests/fixtures/artifact-704-bootstrap.lua.gz").read_bytes())
        # Change only the missing source-main call in the historical script.
        repaired = broken.replace(b"\tif not xpcall(init_AbilityIds,",
                                  b"\tInitBlizzard()\n\tif not xpcall(init_AbilityIds,", 1)
        self.assertEqual([], startup_failures(repaired))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / "bootstrap.w3x"
            runtime = json.dumps({"sourceSha256": hashlib.sha256(config.scenario_file.read_bytes()).hexdigest()}).encode()
            for packaged, intermediate, succeeds in ((broken, repaired, False), (repaired, broken, True)):
                with self.subTest(archived_lua_is_valid=succeeds):
                    (root / "war3map.lua").write_bytes(intermediate)
                    write_mpq(archive, {"war3map.lua": packaged, "runtime/scenario-runtime.json": runtime})
                    if succeeds:
                        _inspect(config, archive, root)
                    else:
                        with self.assertRaisesRegex(PackagingError, "main must call InitBlizzard"):
                            _inspect(config, archive, root)

    def test_generated_records_are_complete_and_not_randomized(self):
        header = b"W3do" + struct.pack("<III", 8, 11, 2)
        data = header + _unit(b"sloc", 0., 0., 0, 0) + _unit(b"ntav", 128., 256., 15, 1)
        rows = validate_units(data)
        self.assertEqual(["sloc", "ntav"], [row["typeId"] for row in rows])
        self.assertEqual([-1, -1], [row["itemTable"] for row in rows])
        self.assertEqual([-1, -1], [row["randomMode"] for row in rows])
        self.assertEqual([1, 1], [row["heroLevel"] for row in rows])
        self.assertEqual((128., 256., 0.), rows[1]["position"])
        for malformed in (data[:-1], data + b"\0", header + data[16:123] * 2):
            with self.subTest(size=len(malformed)), self.assertRaises(ValueError):
                validate_units(malformed)

    def test_authoring_bootstrap_placement_is_independently_valid(self):
        rows = validate_units((PROJECT / "map/AgeOfSailWorld.w3x/war3mapUnits.doo").read_bytes())
        self.assertEqual(["sloc"], [row["typeId"] for row in rows])

    def test_real_3_0_map_fixture_uses_v39_not_authoring_v33(self):
        data = bytes.fromhex((PROJECT / "tests/fixtures/war3net-map-3.0.0-war3map.w3i.hex").read_text())
        info = parse_w3i(data)
        self.assertEqual(39, info["format"])
        self.assertEqual((3, 0, 0, 24268), info["gameVersion"])
        self.assertEqual(0, info["scriptLanguage"])  # the external fixture uses JASS
        self.assertEqual(1, info["players"])
        for malformed in (data[:-1], data + b"\0"):
            with self.assertRaises(ValueError):
                parse_w3i(malformed)

    def test_campaign_member_manifest_cannot_alias_or_hide_maps(self):
        # Synthetic nested bytes isolate MPQ/member semantics from compilation.
        config = load_campaign_config(PROJECT / "physical-maps.json")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            built = []
            for physical in config.maps:
                path = root / (physical.id + ".w3x")
                path.write_bytes(physical.id.encode())
                built.append((physical, path))
            campaign = root / "campaign.w3n"
            _write_campaign(campaign, config, built)
            inspect_campaign(config, campaign)
            original = MpqReader(campaign).members()
            for field, value in (("id", config.maps[1].id),
                                 ("packagePath", config.maps[1].package_path),
                                 ("bootstrap", False)):
                members = dict(original)
                manifest = json.loads(members["campaign-manifest.json"])
                manifest["maps"][0][field] = value
                members["campaign-manifest.json"] = json.dumps(manifest).encode()
                write_mpq(campaign, members)
                with self.subTest(field=field), self.assertRaises(PackagingError):
                    inspect_campaign(config, campaign)
            members = original | {"Maps/Unexpected.w3x": b"unlisted"}
            write_mpq(campaign, members)
            with self.assertRaisesRegex(PackagingError, "listfile"):
                inspect_campaign(config, campaign)


if __name__ == "__main__":
    unittest.main()
