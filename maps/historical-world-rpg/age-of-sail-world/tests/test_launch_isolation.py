"""Byte-preserving diagnostic MPQ surgery, never Warcraft acceptance tests."""
import importlib.util
from pathlib import Path
import random
import struct
import sys
import tempfile
import unittest
import zlib

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT.parent / "_shared/tooling"))
from warcraft_campaign import MpqReader, write_mpq, _decrypt, _encrypt, _hash

SPEC = importlib.util.spec_from_file_location("issue438_mpq_patch", PROJECT / "reports/issue-438/pass2/mpq_patch.py")
patcher = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(patcher)


class LaunchIsolationPatchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def read(self, data, name="war3map.lua"):
        path = self.root / "read.mpq"
        path.write_bytes(data)
        return MpqReader(path).read(name)

    def tables(self, data):
        header = struct.unpack_from("<4sIIHHIIII", data)
        hash_at, block_at, hashes, blocks = header[5:]
        h = bytearray(_decrypt(data[hash_at:hash_at + hashes * 16], _hash("(hash table)", 3)))
        b = bytearray(_decrypt(data[block_at:block_at + blocks * 16], _hash("(block table)", 3)))
        return header, h, b

    def block_index(self, data, name="war3map.lua"):
        _, hashes, _ = self.tables(data)
        return next(row[4] for row in struct.iter_unpack("<IIHHI", hashes)
                    if row[:2] == (_hash(name, 1), _hash(name, 2)))

    def edit_tables(self, data, mutate_blocks=None, mutate_hashes=None):
        header, h, b = self.tables(data)
        if mutate_blocks:
            mutate_blocks(b)
        if mutate_hashes:
            mutate_hashes(h)
        result = bytearray(data)
        result[header[5]:header[5] + len(h)] = _encrypt(h, _hash("(hash table)", 3))
        result[header[6]:header[6] + len(b)] = _encrypt(b, _hash("(block table)", 3))
        return bytes(result)

    def archive(self, original, compressed=False, extra=None):
        # Independent fixture encoder: raw sectors are used when zlib cannot
        # shrink a sector, exercising both legal representations in one member.
        stored = original
        if compressed:
            parts = []
            offsets = [4 * ((len(original) + 511) // 512 + 1)]
            for start in range(0, len(original), 512):
                sector = original[start:start + 512]
                zipped = b"\x02" + zlib.compress(sector, 1)
                part = zipped if len(zipped) < len(sector) else sector
                parts.append(part)
                offsets.append(offsets[-1] + len(part))
            stored = struct.pack(f"<{len(offsets)}I", *offsets) + b"".join(parts)
        path = self.root / "fixture.mpq"
        files = {"war3map.lua": stored, "untouched.bin": b"original-other-member" * 20,
                 "(listfile)": b"war3map.lua\nuntouched.bin\n"}
        files.update(extra or {})
        write_mpq(path, files)
        data = path.read_bytes()
        if compressed:
            data = bytearray(data)
            struct.pack_into("<H", data, 14, 0)  # 512-byte test sectors
            index = self.block_index(data)
            data = self.edit_tables(data, lambda b: struct.pack_into("<II", b, index * 16 + 8, len(original), 0x80000200))
        return bytes(data)

    def assert_preserved(self, original, changed, replacement):
        old_h, _, old_b = self.tables(original)
        new_h, _, new_b = self.tables(changed)
        self.assertEqual(old_h, new_h)
        index = self.block_index(original)
        offset, packed, size, flags = struct.unpack_from("<IIII", old_b, index * 16)
        new_offset, new_packed, new_size, new_flags = struct.unpack_from("<IIII", new_b, index * 16)
        self.assertEqual((offset, flags), (new_offset, new_flags))
        self.assertEqual(len(replacement), new_size)
        self.assertEqual(self.read(changed), replacement)
        self.assertEqual(self.read(original, "untouched.bin"), self.read(changed, "untouched.bin"))
        # Only the replacement's used bytes and encrypted block table can vary.
        expected = bytearray(original)
        expected[offset:offset + new_packed] = changed[offset:offset + new_packed]
        table_at, table_size = old_h[6], old_h[8] * 16
        expected[table_at:table_at + table_size] = changed[table_at:table_at + table_size]
        self.assertEqual(bytes(expected), changed)
        self.assertEqual(original[offset + new_packed:offset + packed], changed[offset + new_packed:offset + packed])
        # In plaintext, only the target's two size fields can vary.
        expected_b = bytearray(old_b)
        expected_b[index * 16 + 4:index * 16 + 12] = new_b[index * 16 + 4:index * 16 + 12]
        self.assertEqual(expected_b, new_b)
        self.assertEqual(len(original), len(changed))

    def test_neutral_literal_and_zlib_inputs_are_byte_identical(self):
        value = b"unchanged\n" * 800
        for compressed in (False, True):
            with self.subTest(compressed=compressed):
                original = self.archive(value, compressed)
                self.assertEqual(value, self.read(original))
                self.assertIs(patcher.replace_member(original, "war3map.lua", value), original)

    def test_literal_shrink_preserves_allocation_slack_and_other_members(self):
        original = self.archive(b"old script;" * 100)
        replacement = b"minimal script"
        self.assert_preserved(original, patcher.replace_member(original, "war3map.lua", replacement), replacement)

    def test_same_length_literal_patch_does_not_change_block_table(self):
        original = self.archive(b"a" * 100)
        changed = patcher.replace_member(original, "war3map.lua", b"b" * 100)
        self.assert_preserved(original, changed, b"b" * 100)
        self.assertEqual(self.tables(original)[2], self.tables(changed)[2])

    def test_zlib_and_raw_sectors_can_be_replaced_without_relocation(self):
        value = b"a" * 512 + random.Random(438).randbytes(512) + b"z" * 300
        original = self.archive(value, True)
        replacement = b"new Lua;\n" * 50
        self.assertEqual(self.read(original), value)
        self.assert_preserved(original, patcher.replace_member(original, "war3map.lua", replacement), replacement)

    def test_empty_replacements_are_decodable(self):
        for compressed in (False, True):
            with self.subTest(compressed=compressed):
                original = self.archive(b"content" * 200, compressed)
                self.assert_preserved(original, patcher.replace_member(original, "war3map.lua", b""), b"")

    def test_logical_and_packed_growth_are_rejected(self):
        for compressed in (False, True):
            with self.subTest(compressed=compressed), self.assertRaisesRegex(ValueError, "logical member growth"):
                patcher.replace_member(self.archive(b"a" * 512, compressed), "war3map.lua", b"b" * 513)
        with self.assertRaisesRegex(ValueError, "packed member growth"):
            patcher.replace_member(self.archive(b"a" * 512, True), "war3map.lua", random.Random(438).randbytes(512))

    def test_wrapper_trailing_data_and_unsupported_header_are_rejected(self):
        original = self.archive(b"value")
        wrong_version = bytearray(original)
        struct.pack_into("<H", wrong_version, 12, 1)
        for malformed in (b"HM3W" + original, original + b"trailer", bytes(wrong_version)):
            with self.subTest(case=malformed[:16]), self.assertRaises(ValueError):
                patcher.replace_member(malformed, "war3map.lua", b"x")

    def test_attributes_and_signature_are_rejected(self):
        for name in ("(attributes)", "(signature)"):
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, "attributes and signatures"):
                patcher.replace_member(self.archive(b"value", extra={name: b"opaque"}), "war3map.lua", b"x")

    def test_encrypted_or_other_target_flag_layouts_are_rejected(self):
        original = self.archive(b"value")
        index = self.block_index(original)
        for flags in (0x81010000, 0x81020000, 0x80000300, 0x85000200, 0x81000200):
            changed = self.edit_tables(original, lambda b: struct.pack_into("<I", b, index * 16 + 12, flags))
            with self.subTest(flags=hex(flags)), self.assertRaisesRegex(ValueError, "unsupported target flags"):
                patcher.replace_member(changed, "war3map.lua", b"x")

    def test_alias_and_overlapping_allocations_are_rejected(self):
        original = self.archive(b"value" * 20)
        index = self.block_index(original)
        def alias(h):
            free = next(i for i, row in enumerate(struct.iter_unpack("<IIHHI", h)) if row[4] == 0xffffffff)
            struct.pack_into("<IIHHI", h, free * 16, _hash("alias", 1), _hash("alias", 2), 0, 0, index)
        with self.assertRaisesRegex(ValueError, "aliases"):
            patcher.replace_member(self.edit_tables(original, mutate_hashes=alias), "war3map.lua", b"x")
        other = self.block_index(original, "untouched.bin")
        offset = struct.unpack_from("<I", self.tables(original)[2], other * 16)[0]
        changed = self.edit_tables(original, lambda b: struct.pack_into("<I", b, index * 16, offset + 1))
        with self.assertRaisesRegex(ValueError, "overlapping"):
            patcher.replace_member(changed, "war3map.lua", b"x")

    def test_bad_sector_offsets_and_unsupported_compression_are_rejected(self):
        original = self.archive(b"a" * 512, True)
        index = self.block_index(original)
        offset = struct.unpack_from("<I", self.tables(original)[2], index * 16)[0]
        for at, value in ((offset, 9), (offset + 8, 0x10)):
            changed = bytearray(original)
            changed[at] = value
            with self.subTest(at=at), self.assertRaises(ValueError):
                patcher.replace_member(bytes(changed), "war3map.lua", b"x")

    def test_missing_member_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "absent"):
            patcher.replace_member(self.archive(b"value"), "not-here", b"x")


if __name__ == "__main__":
    unittest.main()
