"""Narrow, non-release MPQ0 patcher for issue #438 isolation experiments.

The caller must hash-bind its input. This is not a general MPQ writer: only raw
MPQ0, unencrypted zlib sectors or literal single-unit targets are accepted.
Offsets, archive length, other members and unused allocation bytes stay fixed.
No archive, script, or embedded code is executed.
"""
from __future__ import annotations

from pathlib import Path
import struct
import sys
import zlib

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "_shared/tooling"))
from warcraft_campaign import _decrypt, _encrypt, _hash

EXISTS = 0x80000000
SINGLE = 0x01000000
COMPRESSED = 0x00000200
EMPTY = 0xffffffff


def _decode_sectors(packed: bytes, size: int, sector_size: int) -> bytes:
    count = (size + sector_size - 1) // sector_size
    table_size = (count + 1) * 4
    if len(packed) < table_size:
        raise ValueError("truncated sector table")
    offsets = struct.unpack_from(f"<{count + 1}I", packed)
    if (offsets[0] != table_size or offsets[-1] != len(packed)
            or any(a >= b for a, b in zip(offsets, offsets[1:]))):
        raise ValueError("unsupported or malformed sector offsets")
    output = bytearray()
    for start, end in zip(offsets, offsets[1:]):
        expected = min(sector_size, size - len(output))
        sector = packed[start:end]
        if len(sector) == expected:
            output.extend(sector)
        elif sector[:1] == b"\x02" and len(sector) < expected:
            decoder = zlib.decompressobj()
            try:
                value = decoder.decompress(sector[1:], expected + 1)
            except zlib.error as error:
                raise ValueError("malformed zlib sector") from error
            if (len(value) != expected or not decoder.eof
                    or decoder.unused_data or decoder.unconsumed_tail):
                raise ValueError("malformed zlib sector size or trailing bytes")
            output.extend(value)
        else:
            raise ValueError("unsupported sector compression")
    return bytes(output)


def _encode_sectors(value: bytes, sector_size: int) -> bytes:
    count = (len(value) + sector_size - 1) // sector_size
    offsets, sectors = [(count + 1) * 4], []
    for start in range(0, len(value), sector_size):
        raw = value[start:start + sector_size]
        compressed = b"\x02" + zlib.compress(raw, 9)
        sector = compressed if len(compressed) < len(raw) else raw
        sectors.append(sector)
        offsets.append(offsets[-1] + len(sector))
    return struct.pack(f"<{len(offsets)}I", *offsets) + b"".join(sectors)


def replace_member(archive: bytes, name: str, replacement: bytes) -> bytes:
    """Replace one member without relocation; refuse allocation/logical growth."""
    if len(archive) < 32 or archive[:4] != b"MPQ\x1a":
        raise ValueError("only raw MPQ0 archives without wrappers are supported")
    _, header_size, archive_size, version, shift, hash_at, block_at, hashes, blocks = struct.unpack_from("<4sIIHHIIII", archive)
    if (header_size != 32 or version != 0 or archive_size != len(archive)
            or shift > 16 or not hashes or hashes & (hashes - 1) or not blocks):
        raise ValueError("unsupported or malformed MPQ0 header")
    regions = [(0, 32, "header"), (hash_at, hash_at + hashes * 16, "hash table"),
               (block_at, block_at + blocks * 16, "block table")]
    if any(start < 0 or end > len(archive) or start >= end for start, end, _ in regions):
        raise ValueError("MPQ table outside archive")
    hash_rows = list(struct.iter_unpack("<IIHHI", _decrypt(archive[hash_at:hash_at + hashes * 16], _hash("(hash table)", 3))))
    block_table = bytearray(_decrypt(archive[block_at:block_at + blocks * 16], _hash("(block table)", 3)))
    block_rows = list(struct.iter_unpack("<IIII", block_table))
    live = [row for row in hash_rows if row[4] not in (EMPTY, EMPTY - 1)]
    if (any(row[2] or row[3] or row[4] >= blocks for row in live)
            or len({row[4] for row in live}) != len(live)
            or len({row[:2] for row in live}) != len(live)):
        raise ValueError("unsupported MPQ aliases or member variants")
    for special in ("(attributes)", "(signature)"):
        if any(row[:2] == (_hash(special, 1), _hash(special, 2)) for row in live):
            raise ValueError("attributes and signatures require regeneration; patch refused")
    for index, (offset, packed, size, flags) in enumerate(block_rows):
        if flags & EXISTS:
            if offset < 32 or offset + packed > len(archive):
                raise ValueError("member allocation outside archive")
            if packed:
                regions.append((offset, offset + packed, f"block {index}"))
    ordered = sorted(regions)
    if any(a[1] > b[0] for a, b in zip(ordered, ordered[1:])):
        raise ValueError("overlapping MPQ allocations")
    if not name or "\0" in name:
        raise ValueError("invalid member name")
    selected = None
    for step in range(hashes):
        row = hash_rows[(_hash(name, 0) + step) & (hashes - 1)]
        if row[4] == EMPTY:
            break
        if row[4] != EMPTY - 1 and row[:2] == (_hash(name, 1), _hash(name, 2)):
            selected = row[4]
            break
    if selected is None:
        raise ValueError("member is absent from MPQ hash lookup")
    offset, packed, size, flags = block_rows[selected]
    original = archive[offset:offset + packed]
    if flags == EXISTS | SINGLE:
        if packed != size:
            raise ValueError("literal member has inconsistent sizes")
        decoded = original
    elif flags == EXISTS | COMPRESSED:
        decoded = _decode_sectors(original, size, 512 << shift)
    else:
        raise ValueError("unsupported target flags (encryption, CRC, or compression layout)")
    if replacement == decoded:
        return archive
    if len(replacement) > size:
        raise ValueError("logical member growth is forbidden")
    encoded = (_encode_sectors(replacement, 512 << shift)
               if flags & COMPRESSED else replacement)
    if len(encoded) > packed:
        raise ValueError("packed member growth is forbidden")
    result = bytearray(archive)
    result[offset:offset + len(encoded)] = encoded
    struct.pack_into("<II", block_table, selected * 16 + 4, len(encoded), len(replacement))
    result[block_at:block_at + len(block_table)] = _encrypt(block_table, _hash("(block table)", 3))
    return bytes(result)
