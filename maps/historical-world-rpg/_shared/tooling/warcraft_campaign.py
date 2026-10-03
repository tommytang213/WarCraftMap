"""Minimal deterministic MPQ and Warcraft III campaign-metadata support.

Campaigns and maps are MPQ archives.  The writer deliberately uses uncompressed
single-unit files: this is a little larger, but is part of the original MPQ
format understood by every supported Warcraft III version and is reproducible.
"""
from __future__ import annotations

import struct
from pathlib import Path

MPQ_MAGIC = b"MPQ\x1a"
HASH_EMPTY = 0xFFFFFFFF
FILE_EXISTS = 0x80000000
FILE_SINGLE_UNIT = 0x01000000


def _crypt_table() -> tuple[int, ...]:
    seed, table = 0x00100001, [0] * 0x500
    for index1 in range(0x100):
        for index2 in range(index1, 0x500, 0x100):
            seed = (seed * 125 + 3) % 0x2AAAAB
            high = (seed & 0xFFFF) << 16
            seed = (seed * 125 + 3) % 0x2AAAAB
            table[index2] = high | (seed & 0xFFFF)
    return tuple(table)


CRYPT = _crypt_table()


def _hash(name: str, kind: int) -> int:
    seed1, seed2 = 0x7FED7FED, 0xEEEEEEEE
    for byte in name.replace("/", "\\").upper().encode("utf-8"):
        seed1 = (CRYPT[(kind << 8) + byte] ^ (seed1 + seed2)) & 0xFFFFFFFF
        seed2 = (byte + seed1 + seed2 + ((seed2 << 5) & 0xFFFFFFFF) + 3) & 0xFFFFFFFF
    return seed1


def _crypt_words(data: bytes, key: int, decrypt: bool = False) -> bytes:
    seed, words = 0xEEEEEEEE, []
    for (value,) in struct.iter_unpack("<I", data):
        seed = (seed + CRYPT[0x400 + (key & 0xFF)]) & 0xFFFFFFFF
        plain = (value ^ (key + seed)) & 0xFFFFFFFF
        words.append(plain if decrypt else plain)  # encryption and decryption share the xor result
        source = plain if decrypt else value
        key = (((~key << 21) + 0x11111111) | (key >> 11)) & 0xFFFFFFFF
        seed = (source + seed + ((seed << 5) & 0xFFFFFFFF) + 3) & 0xFFFFFFFF
    return struct.pack(f"<{len(words)}I", *words)


def _encrypt(data: bytes, key: int) -> bytes:
    # MPQ's seed update uses the plaintext word while encrypting.
    seed, result = 0xEEEEEEEE, []
    for (plain,) in struct.iter_unpack("<I", data):
        seed = (seed + CRYPT[0x400 + (key & 0xFF)]) & 0xFFFFFFFF
        result.append((plain ^ (key + seed)) & 0xFFFFFFFF)
        key = (((~key << 21) + 0x11111111) | (key >> 11)) & 0xFFFFFFFF
        seed = (plain + seed + ((seed << 5) & 0xFFFFFFFF) + 3) & 0xFFFFFFFF
    return struct.pack(f"<{len(result)}I", *result)


def write_mpq(path: Path, files: dict[str, bytes]) -> None:
    entries = sorted(files.items())
    table_size = 4
    while table_size < len(entries) * 2:
        table_size *= 2
    header_size, hash_offset = 32, 32
    block_offset = hash_offset + table_size * 16
    data_offset = block_offset + len(entries) * 16
    hashes = [[HASH_EMPTY, HASH_EMPTY, 0xFFFF, 0xFFFF, HASH_EMPTY] for _ in range(table_size)]
    blocks, payload = [], bytearray()
    for block_index, (name, value) in enumerate(entries):
        slot = _hash(name, 0) & (table_size - 1)
        while hashes[slot][4] != HASH_EMPTY:
            slot = (slot + 1) & (table_size - 1)
        hashes[slot] = [_hash(name, 1), _hash(name, 2), 0, 0, block_index]
        blocks.append((data_offset + len(payload), len(value), len(value), FILE_EXISTS | FILE_SINGLE_UNIT))
        payload.extend(value)
    hash_bytes = b"".join(struct.pack("<IIHHI", *row) for row in hashes)
    block_bytes = b"".join(struct.pack("<IIII", *row) for row in blocks)
    header = struct.pack("<4sIIHHIIII", MPQ_MAGIC, 32, data_offset + len(payload), 0, 3,
                         hash_offset, block_offset, table_size, len(entries))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(header + _encrypt(hash_bytes, _hash("(hash table)", 3)) +
                     _encrypt(block_bytes, _hash("(block table)", 3)) + payload)


class MpqReader:
    def __init__(self, path: Path):
        self.data = path.read_bytes()
        if self.data[:4] != MPQ_MAGIC or len(self.data) < 32:
            raise ValueError("not an MPQ archive")
        _, header_size, archive_size, version, _, hash_at, block_at, hash_count, block_count = struct.unpack_from("<4sIIHHIIII", self.data)
        if header_size != 32 or version != 0 or archive_size > len(self.data) or not hash_count or not block_count:
            raise ValueError("malformed MPQ header")
        raw_hash = self.data[hash_at:hash_at + hash_count * 16]
        raw_block = self.data[block_at:block_at + block_count * 16]
        if len(raw_hash) != hash_count * 16 or len(raw_block) != block_count * 16:
            raise ValueError("truncated MPQ tables")
        self.hashes = list(struct.iter_unpack("<IIHHI", _crypt_words(raw_hash, _hash("(hash table)", 3), True)))
        self.blocks = list(struct.iter_unpack("<IIII", _crypt_words(raw_block, _hash("(block table)", 3), True)))

    def read(self, name: str) -> bytes:
        start = _hash(name, 0) & (len(self.hashes) - 1)
        for step in range(len(self.hashes)):
            one, two, _, _, block = self.hashes[(start + step) & (len(self.hashes) - 1)]
            if block == HASH_EMPTY:
                break
            if one == _hash(name, 1) and two == _hash(name, 2):
                offset, packed, size, flags = self.blocks[block]
                if flags != FILE_EXISTS | FILE_SINGLE_UNIT or packed != size or offset + size > len(self.data):
                    raise ValueError(f"unsupported or malformed MPQ member: {name}")
                return self.data[offset:offset + size]
        raise KeyError(name)


def _cstring(value: str) -> bytes:
    return value.encode("utf-8") + b"\0"


def campaign_metadata(name: str, description: str, maps: list[tuple[str, str]], chapters: list[tuple[str, str]] | None = None) -> bytes:
    """Create Warcraft III 3.0 war3campaign.w3f v3 metadata."""
    chapters = maps if chapters is None else chapters
    out = bytearray(struct.pack("<III", 3, 1, 7000))
    out += _cstring(name) + _cstring("Normal") + _cstring("WarcraftMap contributors") + _cstring(description)
    # Fixed difficulty + expansion maps.  All packaged chapters are W3X.
    out += struct.pack("<ii", 2, -1) + _cstring("") + _cstring("")
    out += struct.pack("<i", -1) + _cstring("")
    out += struct.pack("<ifffBBBBi", 0, 0.0, 10000.0, 0.0, 0, 0, 0, 0, 0)
    # v3 fog-height extension, then the v2+ background model version.
    out += struct.pack("<fffffi", 0.0, 0.0, 0.0, 0.0, 0.0, 0)
    out += struct.pack("<ii", 0, len(chapters))
    for title, path in chapters:
        out += struct.pack("<i", 1) + _cstring(title) + _cstring(title) + _cstring(path)
    out += struct.pack("<i", len(maps))
    for _, path in maps:
        out += _cstring("") + _cstring(path)
    return bytes(out)


def parse_campaign_metadata(data: bytes) -> dict:
    position = 0
    def integer() -> int:
        nonlocal position
        value = struct.unpack_from("<i", data, position)[0]; position += 4; return value
    def string() -> str:
        nonlocal position
        end = data.index(0, position); value = data[position:end].decode("utf-8"); position = end + 1; return value
    try:
        version = integer()
        if version not in (1, 2, 3):
            raise ValueError(f"unsupported war3campaign.w3f version: {version}")
        campaign_version, editor = integer(), integer()
        name, difficulty, author, description = string(), string(), string(), string()
        flags, background = integer(), integer(); background_path, minimap = string(), string()
        ambient = integer(); ambient_path = string()
        position += 4 + 12 + 4 + 4  # fog style, three floats, BGRA, cursor race
        if version >= 3:
            position += 20 + 4  # five extended fog floats and draw-over-sky
        background_version = integer() if version >= 2 else None
        button_count = integer()
        buttons = [(integer(), string(), string(), string()) for _ in range(button_count)]
        map_count = integer()
        maps = [(string(), string()) for _ in range(map_count)]
    except (IndexError, UnicodeDecodeError, struct.error, ValueError) as error:
        raise ValueError("malformed war3campaign.w3f") from error
    if position != len(data):
        raise ValueError("trailing campaign metadata")
    return {"version": version, "campaignVersion": campaign_version, "editorVersion": editor,
            "name": name, "difficulty": difficulty, "author": author, "description": description,
            "flags": flags, "backgroundVersion": background_version, "maps": maps, "buttons": buttons}
