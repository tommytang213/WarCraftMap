"""Bounded, verified transport of full execution evidence, never build outputs.

The private compiler tree can be discarded after staging. Publication is a
single directory rename; readers see either no evidence or the complete bundle.
"""
from __future__ import annotations

import argparse
from itertools import chain
import json
from pathlib import Path, PurePosixPath
import shutil
import tarfile

MAX_BYTES = 128 * 1024 * 1024
MAX_FILE_BYTES = 32 * 1024 * 1024
MAX_FILES = 12000
MAX_ARCHIVE_BYTES = MAX_BYTES + MAX_FILES * 2048
FILES = {"results.json", "execution.log"}


class LimitedStream:
    def __init__(self, stream):
        self.stream = stream
        self.remaining = MAX_ARCHIVE_BYTES

    def read(self, size):
        value = self.stream.read(min(size, self.remaining + 1))
        self.remaining -= len(value)
        if self.remaining < 0:
            raise ValueError("execution archive stream exceeds transport limit")
        return value


def relative_path(name: str) -> Path:
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts or not path.parts or "\\" in name:
        raise ValueError(f"unsafe evidence path: {name}")
    return Path(*path.parts)


def snapshot_inputs(compile_root: Path, destination: Path, inputs: dict) -> None:
    from wurst_execution import sha
    if destination.exists():
        shutil.rmtree(destination)
    total = 0
    if len(inputs) > MAX_FILES - 2:
        raise ValueError("too many execution verification inputs")
    for name, digest in inputs.items():
        relative = relative_path(name)
        source = compile_root / relative
        source.resolve().relative_to(compile_root.resolve())
        size = source.stat().st_size
        total += size
        if size > MAX_FILE_BYTES or total > MAX_BYTES:
            raise ValueError("execution verification inputs exceed transport limit")
        data = source.read_bytes()
        if sha(data) != digest:
            raise ValueError(f"execution input changed before snapshot: {name}")
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)


def read_bundle(directory: Path, project: Path, revision: str) -> tuple[dict, bytes]:
    """Recheck all exported bytes and the existing full-source coverage gate."""
    from integration_evidence import verify_execution_coverage
    from wurst_execution import sha
    if directory.is_symlink():
        raise ValueError("non-regular execution bundle directory")
    sizes = {}
    paths = [directory / name for name in FILES]
    inputs_root = directory / "verification-inputs"
    if inputs_root.is_symlink():
        raise ValueError("non-regular execution verification inputs")
    for index, path in enumerate(chain(paths, inputs_root.rglob("*"))):
        if index >= MAX_FILES * 2:
            raise ValueError("too many execution evidence entries")
        if path.is_symlink():
            raise ValueError("non-regular execution evidence")
        if not path.exists():
            raise FileNotFoundError(f"missing execution evidence: {path}")
        if not (path.is_file() or path.is_dir()):
            raise ValueError("non-regular execution evidence")
        if path.is_file():
            sizes[path.relative_to(directory).as_posix()] = path.stat().st_size
    if (len(sizes) > MAX_FILES or sum(sizes.values()) > MAX_BYTES or
            any(size > MAX_FILE_BYTES for size in sizes.values())):
        raise ValueError("execution evidence exceeds transport limit")
    report = json.loads((directory / "results.json").read_text())
    log = (directory / "execution.log").read_bytes()
    verify_execution_coverage(report, log, project, revision)
    expected = FILES | {"verification-inputs/" + relative_path(name).as_posix()
                        for name in report["inputs"]}
    # Local execution also has a compile tree; the published bundle does not.
    actual = set(sizes)
    if actual != expected:
        raise ValueError("incomplete execution verification inputs")
    for name, digest in report["inputs"].items():
        if sha((directory / "verification-inputs" / relative_path(name)).read_bytes()) != digest:
            raise ValueError(f"exported execution input mismatch: {name}")
    return report, log


def invalidate(project: Path) -> None:
    root = project / "_build/wurst-tests"
    # Keep the expensive local build tree, but remove every consumable result.
    for name in FILES:
        (root / name).unlink(missing_ok=True)
    inputs = root / "verification-inputs"
    if inputs.exists():
        shutil.rmtree(inputs)


def stage(project: Path, destination: Path, revision: str) -> None:
    source = project / "_build/wurst-tests"
    report, _ = read_bundle(source, project, revision)
    destination.mkdir()
    for name in FILES | {"verification-inputs/" + name for name in report["inputs"]}:
        target = destination / relative_path(name)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source / name, target)
    read_bundle(destination, project, revision)


def unpack(stream, destination: Path) -> None:
    """Read Docker's tar stream without extracting links, devices or build trees."""
    seen, total = set(), 0
    with tarfile.open(fileobj=LimitedStream(stream), mode="r|") as archive:
        for index, member in enumerate(archive):
            if index >= MAX_FILES * 2:
                raise ValueError("too many execution archive entries")
            if member.name in (".", "./") and member.isdir():
                continue
            relative = relative_path(member.name)
            name = relative.as_posix()
            allowed = name in FILES or name == "verification-inputs" or name.startswith("verification-inputs/")
            if not allowed or name in seen or not (member.isdir() or member.isfile()):
                raise ValueError(f"unexpected execution archive entry: {name}")
            seen.add(name)
            total += member.size
            if not 0 <= member.size <= MAX_FILE_BYTES or total > MAX_BYTES:
                raise ValueError("execution archive exceeds transport limit")
            target = destination / relative
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.extractfile(member) as source, target.open("xb") as output:
                    shutil.copyfileobj(source, output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("invalidate", "stage"))
    parser.add_argument("project", type=Path)
    parser.add_argument("destination", type=Path, nargs="?")
    parser.add_argument("--source-revision")
    args = parser.parse_args()
    if args.action == "invalidate":
        invalidate(args.project)
    else:
        stage(args.project, args.destination, args.source_revision)


if __name__ == "__main__":
    main()
