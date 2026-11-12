"""Independent malformed-W3F table-count regression for campaign packaging.

The test locates counts by the published W3F v3 layout, rather than calling the
production parser to discover offsets. This is a binary-only check, not a
Warcraft III startup or handoff acceptance test.
"""
import struct
import sys
import unittest
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT.parent / "_shared" / "tooling"))
from warcraft_campaign import campaign_metadata, parse_campaign_metadata


def table_count_offsets(payload: bytes) -> tuple[int, int]:
    """Independent v3 header cursor (War3Net-compatible field order)."""
    at = 12  # format version, campaign version, editor version
    for _ in range(4):  # name, difficulty, author, description
        at = payload.index(0, at) + 1
    at += 8  # flags and background
    for _ in range(2):  # background model path and minimap
        at = payload.index(0, at) + 1
    at += 4  # ambient
    at = payload.index(0, at) + 1  # ambient path
    at += 4 + 12 + 4 + 4 + 20 + 4 + 4  # fog, extended fog, background version
    chapter_at = at
    chapters = struct.unpack_from("<i", payload, at)[0]
    at += 4
    for _ in range(chapters):
        at += 4  # chapter visibility
        for _ in range(3):  # title, header, chapter map path
            at = payload.index(0, at) + 1
    return chapter_at, at


class CampaignMetadataCountTests(unittest.TestCase):
    def test_negative_and_impossible_table_counts_fail_closed(self):
        baseline = campaign_metadata("Age of Sail: The World", "fixture", [])
        self.assertEqual([], parse_campaign_metadata(baseline)["buttons"])
        self.assertEqual([], parse_campaign_metadata(baseline)["maps"])
        chapter_offset, map_offset = table_count_offsets(baseline)
        self.assertEqual((0, 0),
                         (struct.unpack_from("<i", baseline, chapter_offset)[0],
                          struct.unpack_from("<i", baseline, map_offset)[0]))
        # An intact record with -1 previously passed as if the table were empty.
        for label, offset in (("chapters", chapter_offset), ("maps", map_offset)):
            for invalid in (-1, -(2**31), 2**31 - 1):
                with self.subTest(table=label, count=invalid):
                    corrupt = bytearray(baseline)
                    struct.pack_into("<i", corrupt, offset, invalid)
                    with self.assertRaisesRegex(ValueError, "malformed war3campaign.w3f"):
                        parse_campaign_metadata(bytes(corrupt))

    def test_hidden_regional_chapters_still_parse_with_correct_identity(self):
        chapters = [("Begin the Campaign", "AgeOfSailWorld.w3x"),
                    ("Central and Eastern Europe", "EuropeCentralEast.w3x")]
        value = campaign_metadata(
            "Age of Sail: The World", "fixture", chapters,
            visible_chapters={"AgeOfSailWorld.w3x"})
        parsed = parse_campaign_metadata(value)
        self.assertEqual([1, 0], [button[0] for button in parsed["buttons"]])
        self.assertEqual([path for _, path in chapters],
                         [row[1] for row in parsed["maps"]])
        self.assertEqual([path for _, path in chapters],
                         [button[3] for button in parsed["buttons"]])


if __name__ == "__main__":
    unittest.main()
