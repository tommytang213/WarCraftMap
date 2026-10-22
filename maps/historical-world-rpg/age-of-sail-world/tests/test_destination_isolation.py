"""Binary-delta and minimal Lua checks; no retail Warcraft execution is claimed."""
import ctypes
import ctypes.util
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
import zlib

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "tooling"))
sys.path.insert(0, str(PROJECT.parent / "_shared/tooling"))
import prepare_destination_isolation as isolation
from warcraft_campaign import (FILE_COMPRESS, FILE_EXISTS, MpqReader, _encrypt, _hash, write_mpq)


CONFIG = b'''function config() \n\t__wurst_init_bootstrap()\n\tSetMapName("fixture")\n\tSetPlayers(1)\n\tSetTeams(1)\n\tSetPlayerController(Player(0), MAP_CONTROL_USER)\nend\n'''
LIGHTING = b'''    SetDayNightModels("Environment\\\\DNC\\\\DNCLordaeron\\\\DNCLordaeronTerrain\\\\DNCLordaeronTerrain.mdl", "Environment\\\\DNC\\\\DNCLordaeron\\\\DNCLordaeronUnit\\\\DNCLordaeronUnit.mdl")\n'''
ORIGINAL_LUA = CONFIG + b"\nfunction main()\n" + LIGHTING + b"    InitBlizzard()\nend\n"
# Distinct comment lines make the original compressed slot large enough for the
# minimal control while retaining valid Lua and more than one compressed sector.
ORIGINAL_LUA += b"".join(("-- baseline runtime row %04d %s\n" % (i, isolation.sha(str(i).encode()))).encode() for i in range(400))


def compiler_style_map(path, files):
    """Fixture built from the generic MPQ writer, with data preceding tables.

    Only its script uses the real compiler's multi-sector zlib format. Other
    members include an unknown payload that must survive byte-for-byte.
    """
    write_mpq(path, files)
    original = MpqReader(path)
    entries = sorted(files.items())
    payload, blocks = bytearray(), []
    for index, (name, value) in enumerate(entries):
        flags = original.blocks[index][3]
        if name == "war3map.lua":
            count = (len(value) + 4095) // 4096
            sectors = [b"\x02" + zlib.compress(value[i * 4096:(i + 1) * 4096]) for i in range(count)]
            offsets = [(count + 1) * 4]
            for sector in sectors:
                offsets.append(offsets[-1] + len(sector))
            stored = struct.pack(f"<{len(offsets)}I", *offsets) + b"".join(sectors)
            flags = FILE_EXISTS | FILE_COMPRESS
        else:
            stored = value
        blocks.append((32 + len(payload), len(stored), len(value), flags))
        payload.extend(stored)
    hash_at = 32 + len(payload)
    block_at = hash_at + len(original.hashes) * 16
    header = struct.pack("<4sIIHHIIII", b"MPQ\x1a", 32, block_at + len(blocks) * 16,
                         0, 3, hash_at, block_at, len(original.hashes), len(blocks))
    hashes = _encrypt(b"".join(struct.pack("<IIHHI", *row) for row in original.hashes), _hash("(hash table)", 3))
    block_table = _encrypt(b"".join(struct.pack("<IIII", *row) for row in blocks), _hash("(block table)", 3))
    path.write_bytes(header + payload + hashes + block_table)


class DestinationIsolationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.nested = self.root / "baseline.w3x"
        self.files = {"(listfile)": b"war3map.lua\nwar3map.w3i\nopaque/unknown.bin\n",
                      "war3map.lua": ORIGINAL_LUA, "war3map.w3i": b"original identity and terrain metadata",
                      "opaque/unknown.bin": bytes(range(256)) * 9}
        compiler_style_map(self.nested, self.files)
        self.campaign = self.root / "unchanged-installed-name.w3n"
        self.outer_files = {"(listfile)": b"EuropeCentralEast.w3x\nSelector.w3x\nwar3campaign.w3f\ncampaign-manifest.json\n",
                            "EuropeCentralEast.w3x": self.nested.read_bytes(), "Selector.w3x": b"unchanged selector bytes",
                            "war3campaign.w3f": b"original paths and visibility",
                            "campaign-manifest.json": json.dumps({"baselineMapHash": isolation.sha(self.nested.read_bytes())}).encode()}
        write_mpq(self.campaign, self.outer_files)
        self.script = isolation.make_script(ORIGINAL_LUA, [-1000., -1000., 1000., 1000., -1000., 1000., 1000., -1000.])

    def test_exactly_one_script_changes_with_all_other_packed_bytes_and_tables_preserved(self):
        before = self.campaign.read_bytes()
        target = self.root / "result.w3n"
        receipt = isolation.replace_script(self.campaign, self.script, target)
        self.assertEqual(self.campaign.read_bytes(), before)
        self.assertEqual(len(before), target.stat().st_size)
        a, b = MpqReader(self.campaign), MpqReader(target)
        self.assertEqual(a.hashes, b.hashes)
        self.assertEqual(a.blocks, b.blocks)
        for name, original in a.members().items():
            if name != "europecentraleast.w3x":
                self.assertEqual(original, b.read(name), name)
        extracted = self.root / "result.w3x"
        extracted.write_bytes(b.read("EuropeCentralEast.w3x"))
        original, changed = MpqReader(self.nested), MpqReader(extracted)
        self.assertEqual(original.hashes, changed.hashes)
        self.assertEqual(original.data[:32], changed.data[:32])
        self.assertEqual(len(original.data), len(changed.data))
        index, old_row = isolation._block(original, "war3map.lua")
        for i, row in enumerate(original.blocks):
            if i != index:
                self.assertEqual(row, changed.blocks[i])
                at, length, _, _ = row
                self.assertEqual(original.data[at:at + length], changed.data[at:at + length])
        self.assertEqual(changed.read("war3map.lua"), self.script)
        for name, content in original.members().items():
            if name != "war3map.lua":
                self.assertEqual(content, changed.read(name), name)
        _, new_packed, _, new_flags = changed.blocks[index]
        self.assertEqual(new_flags, old_row[3])
        self.assertEqual(original.data[old_row[0] + new_packed:old_row[0] + old_row[1]],
                         changed.data[old_row[0] + new_packed:old_row[0] + old_row[1]])
        layout = receipt["containerPreservation"]
        self.assertTrue(isolation._same_outside(before, target.read_bytes(),
            [(row["offset"], row["bytes"]) for row in layout["allowedCampaignByteRegions"]]))
        self.assertEqual(["europecentraleast.w3x"], [row["member"] for row in receipt["outerMemberDiff"]])
        self.assertEqual(["war3map.lua"], [row["member"] for row in receipt["destinationMemberDiff"]])
        self.assertEqual(isolation.extract_config(ORIGINAL_LUA), isolation.extract_config(self.script))
        repeated = self.root / "repeated.w3n"
        isolation.replace_script(self.campaign, self.script, repeated)
        self.assertEqual(target.read_bytes(), repeated.read_bytes())

    def test_unknown_unlisted_member_refuses_patch_instead_of_dropping_it(self):
        self.files["unlisted-secret.bin"] = b"must not disappear"
        compiler_style_map(self.nested, self.files)
        write_mpq(self.campaign, self.outer_files | {"EuropeCentralEast.w3x": self.nested.read_bytes()})
        with self.assertRaisesRegex(ValueError, "does not cover every archived member"):
            isolation.replace_script(self.campaign, self.script, self.root / "refused.w3n")
        self.assertFalse((self.root / "refused.w3n").exists())

    def test_unchanged_runtime_and_wrong_baseline_cannot_be_relabelled(self):
        with self.assertRaisesRegex(ValueError, "unchanged script"):
            isolation.replace_script(self.campaign, ORIGINAL_LUA, self.root / "refused.w3n")
        with self.assertRaisesRegex(ValueError, "bound to failed baseline"):
            isolation.prepare(self.campaign, self.root / "refused-directory")
        self.assertFalse((self.root / "refused-directory").exists())

    def test_original_baseline_cannot_be_overwritten(self):
        before = self.campaign.read_bytes()
        with self.assertRaisesRegex(ValueError, "new file"):
            isolation.replace_script(self.campaign, self.script, self.campaign)
        self.assertEqual(before, self.campaign.read_bytes())

    def test_missing_configuration_dependency_is_rejected(self):
        wrong = ORIGINAL_LUA.replace(b'SetMapName("fixture")', b'SetMapName(ExcludedCampaignGlobal)')
        with self.assertRaisesRegex(ValueError, "ExcludedCampaignGlobal"):
            isolation.make_script(wrong, [0.] * 8)


def run_lua(text):
    """Optional stock Lua syntax/control-flow check with explicit native doubles."""
    library = ctypes.util.find_library("lua5.3") or ctypes.util.find_library("lua5.4")
    if library is None:
        raise unittest.SkipTest("stock Lua 5.3/5.4 library unavailable; no native runtime claimed")
    lua = ctypes.CDLL(library)
    lua.luaL_newstate.restype = ctypes.c_void_p
    lua.luaL_openlibs.argtypes = [ctypes.c_void_p]
    lua.luaL_loadstring.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
    lua.luaL_loadstring.restype = ctypes.c_int
    lua.lua_pcallk.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_ssize_t, ctypes.c_void_p]
    lua.lua_pcallk.restype = ctypes.c_int
    lua.lua_tolstring.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.POINTER(ctypes.c_size_t)]
    lua.lua_tolstring.restype = ctypes.c_char_p
    lua.lua_close.argtypes = [ctypes.c_void_p]
    state = lua.luaL_newstate()
    try:
        lua.luaL_openlibs(state)
        status = lua.luaL_loadstring(state, text.encode())
        if status == 0:
            status = lua.lua_pcallk(state, 0, 0, 0, 0, None)
        if status:
            raise AssertionError(lua.lua_tolstring(state, -1, None).decode())
    finally:
        lua.lua_close(state)


LUA_DOUBLES = '''
messages, timers, playerZero = {}, {}, {}
MAP_CONTROL_USER, CAMERA_FIELD_TARGET_DISTANCE = 1, 0
function Player(id) assert(id == 0); return playerZero end
function SetMapName(value) assert(value == "fixture") end
function SetPlayers(value) assert(value == 1) end
function SetTeams(value) assert(value == 1) end
function SetPlayerController(owner, value) assert(owner == playerZero and value == 1) end
function SetDayNightModels(terrain, unit) assert(terrain:find("Terrain") and unit:find("Unit")); lighting = true end
function InitBlizzard() assert(lighting); initialized = true end
function DisplayTimedTextToPlayer(owner, x, y, duration, message)
    assert(owner == playerZero); table.insert(messages, message)
end
function CreateTimer() local t = {}; table.insert(timers, t); return t end
function TimerStart(timer, delay, periodic, callback) timer.periodic = periodic; timer.callback = callback end
function GetExpiredTimer() return currentTimer end
function DestroyTimer(timer) timer.destroyed = true end
function PauseGame(value) assert(not value) end
function EnableUserControl(value) assert(value) end
function EnableUserUI(value) assert(value) end
function SetCameraBounds(...) assert(select('#', ...) == 8) end
function FogMaskEnable(value) assert(not value) end
function FogEnable(value) assert(not value) end
function PanCameraToTimed(x, y, seconds) assert(x == 576 and y == 64 and seconds == 0) end
function SetCameraField(field, distance, duration) assert(distance == 1650) end
function FourCC(value) assert(value == "hfoo"); return 1751543663 end
function CreateUnit(owner, unitType, x, y, facing)
    assert(initialized and owner == playerZero and x == 576 and y == 64)
    if createNil then return nil end
    createdUnit = {x = x, y = y}; return createdUnit
end
function SetUnitInvulnerable(unit, value) assert(unit ~= nil and value) end
function PauseUnit(unit, value) assert(unit ~= nil and not value) end
function ClearSelection() end
function SelectUnit(unit, value) assert(unit ~= nil and value); selectedUnit = unit end
function GetUnitX(unit) assert(unit ~= nil); return unit.x end
function GetUnitY(unit) assert(unit ~= nil); return unit.y end
'''


class DestinationLuaTests(unittest.TestCase):
    def script(self):
        return isolation.make_script(ORIGINAL_LUA, [-1000., -1000., 1000., 1000., -1000., 1000., 1000., -1000.]).decode()

    def test_native_doubles_reach_visible_unit_and_heartbeat_without_campaign_storage(self):
        run_lua(LUA_DOUBLES + self.script() + '''
config(); main()
currentTimer = timers[1]; timers[1].callback()
assert(timers[1].destroyed and selectedUnit == createdUnit and selectedUnit ~= nil)
timers[2].callback()
assert(messages[#messages]:find("heartbeat 1") and messages[#messages]:find("movement not yet verified"))
assert(messages[#messages]:find("AOS%-DESTINATION%-ISOLATION%-54911ca%-v1"))
''')

    def test_null_native_unit_is_reported_and_heartbeat_survives_without_dereferencing_it(self):
        run_lua(LUA_DOUBLES + "createNil = true\n" + self.script() + '''
config(); main()
currentTimer = timers[1]; timers[1].callback()
assert(timers[1].destroyed and selectedUnit == nil)
assert(messages[#messages]:find("FAILED: CreateUnit returned nil"))
timers[2].callback()
assert(messages[#messages]:find("heartbeat 1") and messages[#messages]:find("FAILED: CreateUnit returned nil"))
''')


if __name__ == "__main__":
    unittest.main()
