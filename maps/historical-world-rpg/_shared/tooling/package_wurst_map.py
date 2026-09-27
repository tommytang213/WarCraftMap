#!/usr/bin/env python3
"""Deterministic, scenario-configured Warcraft folder-map build pipeline."""
from __future__ import annotations
import hashlib, json, re, shutil, subprocess, sys, zipfile
from dataclasses import dataclass
from pathlib import Path

class PackagingError(RuntimeError): pass
GENERATOR_VERSION = 1
GENERATED_WURST, GENERATED_DATA, PROVENANCE = "ScenarioData.wurst", "scenario-runtime.json", "provenance.json"

@dataclass(frozen=True)
class BuildConfig:
    project: Path; config_path: Path; source_map: Path; manifest: Path; wurst_source: Path
    scenario_file: Path; scenario_validator: Path; output: Path; output_stem: str
    package_name: str; metadata: dict[str, str]; bootstrap_markers: tuple[str, ...]

def _inside(root: Path, value: object, label: str, boundary: Path | None = None) -> Path:
    if not isinstance(value, str) or not value or Path(value).is_absolute():
        raise PackagingError(f"configuration: {label} must be a non-empty relative path")
    path = (root / value).resolve()
    try: path.relative_to((boundary or root).resolve())
    except ValueError as error: raise PackagingError(f"configuration: {label} escapes the project directory") from error
    return path

def load_config(config_path: Path) -> BuildConfig:
    config_path = config_path.resolve()
    try: raw = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error: raise PackagingError(f"configuration: cannot read {config_path}: {error}") from error
    if raw.get("formatVersion") != 2: raise PackagingError("configuration: formatVersion must be 2")
    project = _inside(config_path.parent, raw.get("projectRoot", "."), "projectRoot")
    release, scenario = raw.get("release"), raw.get("scenario")
    if not isinstance(release, dict) or not isinstance(scenario, dict): raise PackagingError("configuration: release and scenario metadata are required")
    stem, package_name = release.get("fileName"), scenario.get("wurstPackage")
    if not isinstance(stem, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", stem): raise PackagingError("configuration: release.fileName is unsafe")
    if not isinstance(package_name, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9]*", package_name): raise PackagingError("configuration: scenario.wurstPackage is invalid")
    markers, metadata = release.get("bootstrapMarkers"), release.get("metadata")
    if not isinstance(markers, list) or not markers or not all(isinstance(x, str) and x for x in markers): raise PackagingError("configuration: release.bootstrapMarkers must be a non-empty string list")
    if not isinstance(metadata, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in metadata.items()): raise PackagingError("configuration: release.metadata must contain strings")
    return BuildConfig(project, config_path, _inside(project, raw.get("sourceMap"), "sourceMap"), _inside(project, raw.get("sourceManifest"), "sourceManifest"), _inside(project, raw.get("wurstSource"), "wurstSource"), _inside(project, scenario.get("data"), "scenario.data"), _inside(project, scenario.get("validator"), "scenario.validator", project.parent), _inside(project, raw.get("outputDirectory", "_build/release"), "outputDirectory") / f"{stem}.w3x", stem, package_name, metadata, tuple(markers))

def _fail(stage: str, message: object) -> PackagingError: return PackagingError(f"{stage} stage failed: {message}")
def _sha(path: Path) -> str: return hashlib.sha256(path.read_bytes()).hexdigest()

def validate_inputs(config: BuildConfig, grill: str | None = None) -> str:
    required = {"source map folder": config.source_map, "source manifest": config.manifest, "Wurst source folder": config.wurst_source, "scenario data": config.scenario_file, "scenario validator": config.scenario_validator, "wurst.build": config.project / "wurst.build"}
    missing = [f"{label} ({path})" for label, path in required.items() if not path.exists()]
    if missing: raise _fail("inputs", "missing " + ", ".join(missing))
    build_text = (config.project / "wurst.build").read_text(encoding="utf-8")
    for setting in ("scriptMode: LUA", "wc3Patch: v3.0", f"fileName: {config.output_stem}"):
        if setting not in build_text: raise _fail("inputs", f"wurst.build must contain {setting!r}")
    try: manifest_metadata = json.loads(config.manifest.read_text(encoding="utf-8")).get("metadata")
    except (OSError, json.JSONDecodeError) as error: raise _fail("inputs", f"invalid source manifest: {error}") from error
    if manifest_metadata != config.metadata: raise _fail("inputs", "release metadata differs from the authoritative source manifest")
    executable = grill or shutil.which("grill")
    if not executable: raise _fail("inputs", "required tool 'grill' was not found on PATH")
    return str(Path(executable).resolve())

def validate_scenario(config: BuildConfig) -> None:
    result = subprocess.run([sys.executable, str(config.scenario_validator), str(config.scenario_file)], cwd=config.project, text=True, capture_output=True)
    if result.returncode: raise _fail("scenario validation", (result.stderr or result.stdout).strip() or f"validator exited {result.returncode}")

def generate(config: BuildConfig, generated: Path) -> None:
    try: world = json.loads(config.scenario_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error: raise _fail("generation", error) from error
    generated.mkdir(parents=True, exist_ok=True)
    domains = ("polities", "provinces", "settlements", "strategicUnits", "characters", "technologies", "institutions")
    runtime = {"schemaVersion": world["schemaVersion"], "sourceSha256": _sha(config.scenario_file), "ids": {domain: [entry["id"] for entry in world.get(domain, [])] for domain in domains}}
    (generated / GENERATED_DATA).write_text(json.dumps(runtime, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    encoded = json.dumps(runtime, ensure_ascii=False, sort_keys=True, separators=(",", ":")).replace("\\", "\\\\").replace('"', '\\"')
    wurst = f"// Generated by package_wurst_map.py v{GENERATOR_VERSION}; do not edit.\npackage {config.package_name}\n\npublic constant int SCENARIO_SCHEMA_VERSION = {world['schemaVersion']}\npublic constant string SCENARIO_SOURCE_SHA256 = \"{runtime['sourceSha256']}\"\npublic constant string SCENARIO_RUNTIME_JSON = \"{encoded}\"\n\npublic function getScenarioRuntimeData() returns string\n\treturn SCENARIO_RUNTIME_JSON\n"
    (generated / GENERATED_WURST).write_text(wurst, encoding="utf-8")
    input_paths = (
        config.config_path,
        config.manifest,
        config.scenario_file,
        config.scenario_validator,
        config.project / "wurst.build",
        Path(__file__).resolve(),
    )
    inputs = {}
    for path in input_paths:
        try:
            key = str(path.relative_to(config.project.parent))
        except ValueError:
            # Unit tests load this shared module before copying a fixture project.
            # The reserved key also avoids encoding machine-specific absolute paths.
            key = "@generator"
        inputs[key] = _sha(path)
    outputs = {name: _sha(generated / name) for name in (GENERATED_WURST, GENERATED_DATA)}
    provenance = {"formatVersion": 1, "generatorVersion": GENERATOR_VERSION, "inputs": inputs, "outputs": outputs}
    (generated / PROVENANCE).write_text(json.dumps(provenance, sort_keys=True, indent=2) + "\n", encoding="utf-8")

def verify_generated(config: BuildConfig, generated: Path) -> None:
    try: provenance = json.loads((generated / PROVENANCE).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error: raise _fail("provenance", f"missing or invalid {PROVENANCE}: {error}") from error
    if provenance.get("generatorVersion") != GENERATOR_VERSION: raise _fail("provenance", "generated data uses a different generator version")
    for relative, expected in provenance.get("inputs", {}).items():
        path = Path(__file__).resolve() if relative == "@generator" else config.project.parent / relative
        if not path.is_file() or _sha(path) != expected: raise _fail("provenance", f"stale generated data: input changed: {relative}")
    for name, expected in provenance.get("outputs", {}).items():
        path = generated / name
        if not path.is_file() or _sha(path) != expected: raise _fail("provenance", f"stale generated data: output changed: {name}")

def _run(stage: str, command: list[str], cwd: Path) -> None:
    result = subprocess.run(command, cwd=cwd, text=True, capture_output=True)
    if result.returncode: raise _fail(stage, f"command exited {result.returncode}: {' '.join(command)}\n{(result.stderr or result.stdout).strip()}")

def _assemble(config: BuildConfig, root: Path, generated: Path) -> Path:
    compile_root = root / "compile"
    shutil.copytree(config.source_map, compile_root / "map" / config.source_map.name)
    shutil.copytree(config.wurst_source, compile_root / "wurst")
    shutil.copy2(config.project / "wurst.build", compile_root / "wurst.build")
    shutil.copy2(generated / GENERATED_WURST, compile_root / "wurst" / GENERATED_WURST)
    runtime_dir = compile_root / "map" / config.source_map.name / "runtime"; runtime_dir.mkdir()
    shutil.copy2(generated / GENERATED_DATA, runtime_dir / GENERATED_DATA); shutil.copy2(generated / PROVENANCE, runtime_dir / PROVENANCE)
    return compile_root

def _find_archive(root: Path) -> Path:
    files = [p for p in root.rglob("*.w3x") if p.is_file()]
    if not files: raise _fail("map assembly", "Wurst produced no .w3x archive")
    return max(files, key=lambda p: p.stat().st_mtime_ns)

def _inspect(config: BuildConfig, archive: Path, compile_root: Path) -> None:
    data = archive.read_bytes()
    if len(data) < 4 or data[:4] not in (b"MPQ\x1a", b"HM3W", b"PK\x03\x04"): raise _fail("archive inspection", f"unrecognized Warcraft archive: {archive}")
    lua = ""
    if zipfile.is_zipfile(archive):
        with zipfile.ZipFile(archive) as zipped:
            names = set(zipped.namelist()); expected = {"war3map.w3i", "war3map.w3e", "war3map.wpm", "war3map.lua", f"runtime/{GENERATED_DATA}", f"runtime/{PROVENANCE}"}
            if expected - names: raise _fail("archive inspection", "missing entries: " + ", ".join(sorted(expected - names)))
            if any(name.startswith(("tests/", "fixtures/", "scenario/", "wurst/")) for name in names): raise _fail("archive inspection", "development-only source or fixtures were packaged")
            lua = zipped.read("war3map.lua").decode("utf-8", errors="replace")
    else:
        candidates = list(compile_root.rglob("war3map.lua")) + list(compile_root.rglob("*_compiled.lua")) + list(compile_root.rglob("output.lua"))
        if candidates: lua = max(candidates, key=lambda p: p.stat().st_mtime_ns).read_text(encoding="utf-8", errors="replace")
    if not lua: raise _fail("archive inspection", "generated Lua runtime code is missing")
    absent = [marker for marker in (*config.bootstrap_markers, _sha(config.scenario_file)) if marker not in lua]
    if absent: raise _fail("archive inspection", "Lua is missing marker(s): " + ", ".join(absent))

def clean(config: BuildConfig) -> None:
    root = config.project / "_build"
    if root.exists(): shutil.rmtree(root)

def build(config_path: Path, grill: str | None = None, clean_first: bool = True) -> Path:
    config = load_config(config_path); executable = validate_inputs(config, grill)
    if clean_first: clean(config)
    validate_scenario(config); root = config.project / "_build"; generated = root / "generated"
    generate(config, generated); verify_generated(config, generated); compile_root = _assemble(config, root, generated)
    _run("Wurst dependency installation", [executable, "install"], compile_root)
    _run("Wurst compilation", [executable, "typecheck"], compile_root)
    _run("map assembly", [executable, "build", str(Path("map") / config.source_map.name)], compile_root)
    archive = _find_archive(compile_root / "_build"); _inspect(config, archive, compile_root)
    config.output.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(archive, config.output)
    print(f"release archive: {config.output}"); return config.output

def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) not in (1, 2) or (len(argv) == 2 and argv[0] != "clean"): print("usage: package_wurst_map.py [clean] CONFIG", file=sys.stderr); return 2
    try:
        config_path = Path(argv[-1]); clean(load_config(config_path)) if len(argv) == 2 else build(config_path)
    except (PackagingError, OSError) as error: print(f"packaging failed: {error}", file=sys.stderr); return 1
    return 0
if __name__ == "__main__": raise SystemExit(main())
