"""Read-only adapter for a separately obtained, pinned mpyq source file.

No dependency installation or archive rewriting. The caller must obtain/review
the source; verify its bytes BEFORE importing it. mpyq cannot decrypt encrypted
members (including Grill's listfile); callers must report that limitation.
"""
from __future__ import annotations

import hashlib
import importlib.util
import io
from pathlib import Path

READER_REVISION = "6bfba18ec403f702666b4109db3d95f3b97b1dc5"
READER_SHA256 = "e10fa2f422d837345f438934a99a3cdf67fa9148c7106d421408e1ecfa83e239"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_reader(path: Path):
    if sha256(path.read_bytes()) != READER_SHA256:
        raise ValueError("independent MPQ reader does not match the reviewed pin")
    spec = importlib.util.spec_from_file_location("diagnostic_mpyq", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def open_archive(reader, data: bytes):
    # mpyq understands raw MPQ, but not Warcraft's optional 512-byte wrapper.
    offset = 512 if data.startswith(b"HM3W") else 0
    if len(data) < offset + 32 or data[offset:offset + 4] != b"MPQ\x1a":
        raise ValueError("expected raw MPQ or a 512-byte HM3W wrapper")
    return reader.MPQArchive(io.BytesIO(data[offset:]), listfile=False)


def read_member(archive, name: str) -> bytes:
    name = name.replace("/", "\\")
    value = archive.read_file(name)
    if value is None:
        entry = archive.get_hash_table_entry(name)
        if entry is not None and archive.block_table[entry.block_table_index].size == 0:
            return b""
        raise ValueError(f"missing MPQ member: {name}")
    return value
