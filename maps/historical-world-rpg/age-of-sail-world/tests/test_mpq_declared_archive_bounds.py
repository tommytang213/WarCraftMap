"""Reject malformed MPQ length claims before inspecting packaged map members.

Binary archive checks only, not Warcraft III native startup evidence.
"""
import struct
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT.parent / "_shared" / "tooling"))
from warcraft_campaign import MpqReader, write_mpq


class DeclaredMpqArchiveBoundsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "candidate.w3x"
        self.member = "war3map.w3e"
        self.payload = b"regional-terrain"
        write_mpq(self.path, {self.member: self.payload})
        self.original = self.path.read_bytes()

    def test_normal_archive_and_hm3w_wrapper_remain_readable(self):
        self.assertEqual(self.payload, MpqReader(self.path).read(self.member))
        self.path.write_bytes(b"HM3W" + bytes(24) + self.original)
        self.assertEqual(self.payload, MpqReader(self.path).read(self.member))

    def test_tables_must_fit_declared_archive_not_only_physical_file(self):
        invalid = bytearray(self.original)
        block_at = struct.unpack_from("<I", invalid, 20)[0]
        block_count = struct.unpack_from("<I", invalid, 28)[0]
        # Deliberately keep the entire physical file while excluding the
        # last byte of the block table from the MPQ's declared size.
        struct.pack_into("<I", invalid, 8, block_at + block_count * 16 - 1)
        self.path.write_bytes(invalid)
        with self.assertRaisesRegex(ValueError, "tables outside declared archive"):
            MpqReader(self.path)

    def test_hash_table_size_must_be_a_power_of_two(self):
        invalid = bytearray(self.original)
        # The advertised index table still fits, but three slots cannot
        # be searched by the mask-based MPQ lookup.
        self.assertEqual(4, struct.unpack_from("<I", invalid, 24)[0])
        struct.pack_into("<I", invalid, 24, 3)
        for prefix in (b"", b"HM3W" + bytes(24)):
            with self.subTest(wrapped=bool(prefix)):
                self.path.write_bytes(prefix + invalid)
                with self.assertRaisesRegex(ValueError, "power of two"):
                    MpqReader(self.path)

    def test_encrypted_hash_and_block_tables_cannot_overlap(self):
        invalid = bytearray(self.original)
        hash_at = struct.unpack_from("<I", invalid, 16)[0]
        # Both corrupted ranges remain within the advertised archive.
        struct.pack_into("<I", invalid, 20, hash_at + 8)
        self.path.write_bytes(invalid)
        with self.assertRaisesRegex(ValueError, "overlapping MPQ tables"):
            MpqReader(self.path)

    def test_member_must_fit_declared_archive_not_only_physical_file(self):
        invalid = bytearray(self.original)
        declared = struct.unpack_from("<I", invalid, 8)[0]
        self.assertEqual(len(invalid), declared)
        # Tables remain inside the archive but the last data byte does not.
        struct.pack_into("<I", invalid, 8, declared - 1)
        for prefix in (b"", b"HM3W" + bytes(24)):
            with self.subTest(wrapped=bool(prefix)):
                self.path.write_bytes(prefix + invalid)
                reader = MpqReader(self.path)
                with self.assertRaisesRegex(ValueError, "member outside declared archive"):
                    reader.read(self.member)


if __name__ == "__main__":
    unittest.main()
