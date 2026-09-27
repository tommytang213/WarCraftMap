#!/usr/bin/env python3
"""Build a configured Wurst folder-map into a release archive."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


class PackagingError(RuntimeError):
    pass


@dataclass(frozen=True)
class BuildConfig:
    project: Path
    source_map: Path
    manifest: Path
    wurst_source: Path
    scenario_data: Path
    output: Path
    output_stem: str
    bootstrap_markers: tuple[str, ...]


def _inside(root: Path, value: object, label: str) -> Path:
    if not isinstance(value, str) or not value or Path(value).is_absolute():
        raise PackagingError(f"{label} must be a non-empty relative path")
    path = (root / value).resolve()
    try:
        path.relative_to(root)
    except ValueError as error:
        raise PackagingError(f"{label} escapes the project directory") from error
    return path


def load_config(config_path: Path) -> BuildConfig:
    config_path = config_path.resolve()
    try:
        raw = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise PackagingError(f"cannot read packaging config {config_path}: {error}") from error
    if raw.get("formatVersion") != 1:
        raise PackagingError("packaging config formatVersion must be 1")
    project = _inside(config_path.parent, raw.get("projectRoot", "."), "projectRoot")
    release = raw.get("release")
    if not isinstance(release, dict):
        raise PackagingError("release metadata is missing")
    stem = release.get("fileName")
    if not isinstance(stem, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", stem):
        raise PackagingError("release.fileName is not a safe deterministic file name")
    markers = release.get("bootstrapMarkers")
    if not isinstance(markers, list) or not markers or not all(isinstance(x, str) and x for x in markers):
        raise PackagingError("release.bootstrapMarkers must be a non-empty string list")
    return BuildConfig(
        project=project,
        source_map=_inside(project, raw.get("sourceMap"), "sourceMap"),
        manifest=_inside(project, raw.get("sourceManifest"), "sourceManifest"),
        wurst_source=_inside(project, raw.get("wurstSource"), "wurstSource"),
        scenario_data=_inside(project, raw.get("scenarioData"), "scenarioData"),
        output=_inside(project, raw.get("outputDirectory", "_build/release"), "outputDirectory") / f"{stem}.w3x",
        output_stem=stem,
        bootstrap_markers=tuple(markers),
    )


def validate_inputs(config: BuildConfig, grill: str | None = None) -> str:
    required = {
        "project directory": config.project,
        "source map folder": config.source_map,
        "source manifest": config.manifest,
        "Wurst source folder": config.wurst_source,
        "scenario data folder": config.scenario_data,
        "wurst.build": config.project / "wurst.build",
    }
    missing = [label for label, path in required.items() if not path.exists()]
    if missing:
        raise PackagingError("required build inputs are missing: " + ", ".join(missing))
    build_text = (config.project / "wurst.build").read_text(encoding="utf-8")
    for setting in ("scriptMode: LUA", "wc3Patch: v3.0", f"fileName: {config.output_stem}"):
        if setting not in build_text:
            raise PackagingError(f"wurst.build must contain pinned setting: {setting}")
    executable = grill or shutil.which("grill")
    if not executable:
        raise PackagingError("required tool 'grill' was not found on PATH")
    return executable


def _find_generated(project: Path, before: set[Path]) -> Path:
    candidates = [p for p in (project / "_build").rglob("*.w3x") if p.resolve() not in before]
    if not candidates:
        candidates = list((project / "_build").rglob("*.w3x"))
    if not candidates:
        raise PackagingError("grill completed but generated no .w3x archive under _build")
    return max(candidates, key=lambda path: path.stat().st_mtime_ns)


def _verify_outputs(config: BuildConfig, generated: Path) -> None:
    data = generated.read_bytes()
    if len(data) < 4 or data[:4] not in (b"MPQ\x1a", b"HM3W", b"PK\x03\x04"):
        raise PackagingError(f"generated output is not a recognizable Warcraft archive: {generated}")
    build_root = config.project / "_build"
    lua_files = list(build_root.rglob("war3map.lua"))
    lua_files.extend(build_root.glob("*_compiled.lua"))
    lua_files.extend(build_root.glob("grill/output.lua"))
    if not lua_files:
        raise PackagingError(
            "generated Lua payload is missing from _build "
            "(expected war3map.lua, *_compiled.lua, or grill/output.lua)"
        )
    lua = max(lua_files, key=lambda path: path.stat().st_mtime_ns).read_text(encoding="utf-8", errors="replace")
    absent = [marker for marker in config.bootstrap_markers if marker not in lua]
    if absent:
        raise PackagingError("generated Lua script is missing bootstrap marker(s): " + ", ".join(absent))


def build(config_path: Path, grill: str | None = None) -> Path:
    config = load_config(config_path)
    executable = validate_inputs(config, grill)
    before = {p.resolve() for p in (config.project / "_build").rglob("*.w3x")} if (config.project / "_build").exists() else set()
    relative_map = config.source_map.relative_to(config.project)
    for command in ([executable, "install"], [executable, "typecheck"], [executable, "build", str(relative_map)]):
        result = subprocess.run(command, cwd=config.project, text=True)
        if result.returncode:
            raise PackagingError(f"command failed ({result.returncode}): {' '.join(command)}")
    generated = _find_generated(config.project, before)
    _verify_outputs(config, generated)
    config.output.parent.mkdir(parents=True, exist_ok=True)
    if generated.resolve() != config.output.resolve():
        shutil.copyfile(generated, config.output)
    print(f"release archive: {config.output}")
    return config.output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path)
    args = parser.parse_args(argv)
    try:
        build(args.config)
    except (PackagingError, OSError) as error:
        print(f"packaging failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
