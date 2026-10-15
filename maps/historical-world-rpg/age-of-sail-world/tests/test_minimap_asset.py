"""Checks for the evidence-backed WC3 minimap browser experiment.

F/G only establishes reported menu browsing, not campaign-launch acceptance.
The authored placeholder is original artwork, not a copied diagnostic donor.
"""
import base64
import hashlib
import shutil
import struct
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT.parent / "_shared" / "tooling"))
from package_wurst_map import PackagingError, _materialize_authored_minimap  # noqa: E402

SOURCE = PROJECT / "map/AgeOfSailWorld.w3x/war3mapMap.blp.base64"
EXPECTED_SHA256 = "a0a6dd942dacb5a458ff0247475751caba851cd245ad07854dc1e4421cf749c7"


class MinimapSourceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        shutil.copy2(SOURCE, self.root / SOURCE.name)

    def test_original_image_materializes_without_exposing_base64_to_warcraft(self):
        expected = base64.b64decode(SOURCE.read_text(encoding="ascii").strip(), validate=True)
        self.assertEqual(EXPECTED_SHA256, hashlib.sha256(expected).hexdigest())
        actual = _materialize_authored_minimap(self.root)
        self.assertEqual(expected, actual)
        self.assertEqual(expected, (self.root / "war3mapMap.blp").read_bytes())
        self.assertFalse((self.root / SOURCE.name).exists())
        self.assertEqual((b"BLP1", 0, 0, 256, 256, 5, 0),
                         struct.unpack_from("<4s6I", actual))

    def test_missing_source_does_not_change_other_maps(self):
        (self.root / SOURCE.name).unlink()
        self.assertIsNone(_materialize_authored_minimap(self.root))
        self.assertEqual([], list(self.root.iterdir()))

    def test_corrupt_base64_fails_without_writing_a_preview(self):
        (self.root / SOURCE.name).write_text("broken preview?", encoding="ascii")
        with self.assertRaisesRegex(PackagingError, "invalid authored minimap"):
            _materialize_authored_minimap(self.root)
        self.assertFalse((self.root / "war3mapMap.blp").exists())

    def test_invalid_blp_header_fails_closed(self):
        bad = bytearray(base64.b64decode(SOURCE.read_text(encoding="ascii")))
        bad[0:4] = b"NOPE"
        (self.root / SOURCE.name).write_text(base64.b64encode(bad).decode("ascii"), encoding="ascii")
        with self.assertRaisesRegex(PackagingError, "expected BLP1"):
            _materialize_authored_minimap(self.root)

    def test_author_supplied_binary_cannot_be_silently_overwritten(self):
        (self.root / "war3mapMap.blp").write_bytes(b"custom")
        with self.assertRaisesRegex(PackagingError, "both authored BLP"):
            _materialize_authored_minimap(self.root)
        self.assertEqual(b"custom", (self.root / "war3mapMap.blp").read_bytes())


if __name__ == "__main__":
    unittest.main()
