#!/usr/bin/env python3
"""Deterministic, scenario-configured Warcraft folder-map build pipeline."""
from __future__ import annotations
import calendar, hashlib, json, re, shutil, subprocess, sys, zipfile
from datetime import date
from dataclasses import dataclass
from pathlib import Path

class PackagingError(RuntimeError): pass
GENERATOR_VERSION = 4
GENERATED_WURST, GENERATED_DATA, PROVENANCE = "ScenarioData.wurst", "scenario-runtime.json", "provenance.json"

@dataclass(frozen=True)
class BuildConfig:
    project: Path; config_path: Path; source_map: Path; manifest: Path; wurst_source: Path
    scenario_file: Path; scenario_validator: Path; output: Path; output_stem: str
    package_name: str; metadata: dict[str, str]; bootstrap_markers: tuple[str, ...]
    regional_terrain: tuple[tuple[str, Path], ...]
    custom_2d_source: Path | None; custom_2d_builder: Path | None

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
    terrain = scenario.get("regionalTerrain", [])
    if not isinstance(terrain, list) or any(not isinstance(item, dict) for item in terrain): raise PackagingError("configuration: scenario.regionalTerrain must be an array")
    terrain_entries = []
    for item in terrain:
        terrain_id = item.get("id")
        if not isinstance(terrain_id, str) or not re.fullmatch(r"[a-z][a-z0-9_]*", terrain_id): raise PackagingError("configuration: regional terrain id is invalid")
        terrain_entries.append((terrain_id, _inside(project, item.get("source"), f"regionalTerrain {terrain_id}.source")))
    if len({item[0] for item in terrain_entries}) != len(terrain_entries): raise PackagingError("configuration: regional terrain ids must be unique")
    custom = scenario.get("custom2d")
    if custom is not None and (not isinstance(custom, dict) or set(custom) != {"source", "builder"}):
        raise PackagingError("configuration: scenario.custom2d must contain source and builder")
    custom_source = _inside(project, custom["source"], "scenario.custom2d.source") if custom else None
    custom_builder = _inside(project, custom["builder"], "scenario.custom2d.builder") if custom else None
    return BuildConfig(project, config_path, _inside(project, raw.get("sourceMap"), "sourceMap"), _inside(project, raw.get("sourceManifest"), "sourceManifest"), _inside(project, raw.get("wurstSource"), "wurstSource"), _inside(project, scenario.get("data"), "scenario.data"), _inside(project, scenario.get("validator"), "scenario.validator", project.parent), _inside(project, raw.get("outputDirectory", "_build/release"), "outputDirectory") / f"{stem}.w3x", stem, package_name, metadata, tuple(markers), tuple(terrain_entries), custom_source, custom_builder)

def _fail(stage: str, message: object) -> PackagingError: return PackagingError(f"{stage} stage failed: {message}")
def _sha(path: Path) -> str: return hashlib.sha256(path.read_bytes()).hexdigest()

def validate_inputs(config: BuildConfig, grill: str | None = None) -> str:
    required = {"source map folder": config.source_map, "source manifest": config.manifest, "Wurst source folder": config.wurst_source, "scenario data": config.scenario_file, "scenario validator": config.scenario_validator, "wurst.build": config.project / "wurst.build"}
    missing = [f"{label} ({path})" for label, path in required.items() if not path.exists()]
    missing.extend(f"regional terrain {terrain_id} ({path})" for terrain_id, path in config.regional_terrain if not path.is_file())
    if config.custom_2d_source and not config.custom_2d_source.is_file(): missing.append(f"custom 2D source ({config.custom_2d_source})")
    if config.custom_2d_builder and not config.custom_2d_builder.is_file(): missing.append(f"custom 2D builder ({config.custom_2d_builder})")
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
    if config.custom_2d_builder:
        result=subprocess.run([sys.executable,str(config.custom_2d_builder),"--output",str(generated/"custom-2d"),"--check"],cwd=config.project,text=True,capture_output=True)
        if result.returncode: raise _fail("custom 2D generation", (result.stderr or result.stdout).strip())
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from generate_regional_terrain import canonical_bytes, generate as generate_terrain
    terrain_outputs = {}
    terrain_authorities = []
    for terrain_id, terrain_path in config.regional_terrain:
        try:
            terrain_source = json.loads(terrain_path.read_text(encoding="utf-8"))
            authority = None
            if terrain_source.get("authority"):
                authority_path = _inside(config.project, terrain_source["authority"], f"regionalTerrain {terrain_id}.authority")
                authority = json.loads(authority_path.read_text(encoding="utf-8")); terrain_authorities.append(authority_path)
            terrain = generate_terrain(terrain_source, world["regionalGeography"], authority)
        except (OSError, json.JSONDecodeError, KeyError, ValueError) as error:
            raise _fail("terrain generation", f"{terrain_id}: {error}") from error
        output_name = f"terrain-{terrain_id}.json"
        (generated / output_name).write_bytes(canonical_bytes(terrain))
        terrain_outputs[terrain_id] = output_name
    domains = ("polities", "provinces", "settlements", "strategicUnits", "characters", "technologies", "institutions")
    runtime = {"schemaVersion": world["schemaVersion"], "sourceSha256": _sha(config.scenario_file), "timeline": world["timeline"], "events": world.get("events", []), "regionalGeography": world["regionalGeography"], "ids": {domain: [entry["id"] for entry in world.get(domain, [])] for domain in domains}, "polityDefinitions": world.get("polities", []), "provinceDefinitions": world.get("provinces", []), "provinceHoldings": [holding for holding in world.get("territorialHoldings", []) if holding.get("territory", {}).get("kind") == "province"]}
    if config.custom_2d_source:
        custom=json.loads((generated/"custom-2d/custom-2d-imports.json").read_text(encoding="utf-8"))
        runtime["custom2dAssets"]={use:row["importPath"] for row in custom["assets"] for use in row["uses"]}
    (generated / GENERATED_DATA).write_text(json.dumps(runtime, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    encoded = json.dumps(runtime, ensure_ascii=False, sort_keys=True, separators=(",", ":")).replace("\\", "\\\\").replace('"', '\\"')
    movement = {"land": "MOVE_LAND", "naval": "MOVE_NAVAL", "amphibious": "MOVE_AMPHIBIOUS", "flying": "MOVE_FLYING"}
    recovery = ["\npublic function configureRecoveryScenario(UnstuckRecoveryService service)"]
    for index, zone in enumerate(world.get("navigationZones", ())):
        name = f"zone{index}"
        recovery.append(f'\tlet {name} = new RecoveryZone("{zone["id"]}")')
        for kind in zone["movementClasses"]: recovery.append(f"\t{name}.addMovement({movement[kind]})")
        for kind, destinations in zone.get("connections", {}).items():
            for destination in destinations: recovery.append(f'\t{name}.connect({movement[kind]}, "{destination}")')
        recovery.append(f"\tservice.addZone({name})")
    for index, point in enumerate(world.get("navigationSafePoints", ())):
        name, position = f"point{index}", point["position"]
        anchor = str(point["kind"] == "recovery_anchor").lower()
        recovery.append(f'\tlet {name} = new RecoveryPoint("{point["id"]}", "{point["zoneId"]}", {float(position["x"])}, {float(position["y"])}, true, {anchor})')
        for kind in point["movementClasses"]: recovery.append(f"\t{name}.addMovement({movement[kind]})")
        recovery.append(f"\tservice.addPoint({name})")
    for index, state in enumerate(world.get("activeUnitNavigationStates", ())):
        name, safe = f"entity{index}", state["lastSafePosition"]
        recovery.append(f'\tlet {name} = new RecoveryEntity("{state["unitId"]}", {movement[state["movementClass"]]}, "{state["currentZoneId"]}", true, true, false, false, true)')
        recovery.append(f"\tservice.addEntity({name})")
        recovery.append(f'\tservice.importLastSafe("{state["unitId"]}", "{safe["zoneId"]}", {float(safe["x"])}, {float(safe["y"])})')
    timeline = world["timeline"]
    timeline_lines = ["\npublic function configureCampaignTimeline() returns CampaignClock",
        f'\tlet clock = new CampaignClock({date.fromisoformat(timeline["startDate"]).toordinal()}, {date.fromisoformat(timeline["endDate"]).toordinal()}, {date.fromisoformat(timeline["initialDate"]).toordinal()}, 1.)']
    for era in timeline.get("eras", []):
        timeline_lines.append(f'\tclock.addEra("{era["id"]}", {date.fromisoformat(era["startDate"]).toordinal()}, {date.fromisoformat(era["endDate"]).toordinal()})')
    occurrences=[]
    for schedule in timeline.get("schedules", []):
        current=date.fromisoformat(schedule["firstDate"]); number=1; rule=schedule.get("recurrence")
        while True:
            occurrences.append((current, schedule["priority"], schedule["id"], number, schedule["eventId"]))
            if not rule or number >= rule.get("maxOccurrences", 2**31-1): break
            if rule["unit"] == "days":
                from datetime import timedelta
                following=current+timedelta(days=rule["interval"])
            else:
                months=rule["interval"]*(1 if rule["unit"] == "months" else 12)
                year,month0=divmod(current.year*12+current.month-1+months,12); month=month0+1
                following=date(year,month,min(current.day,calendar.monthrange(year,month)[1]))
            if following > date.fromisoformat(rule["untilDate"]): break
            current=following; number+=1
    for day,_,schedule,number,event in sorted(occurrences):
        timeline_lines.append(f'\tclock.addOccurrence("{schedule}", "{event}", {day.toordinal()}, {number})')
    timeline_lines.append("\treturn clock")
    wurst = f"// Generated by package_wurst_map.py v{GENERATOR_VERSION}; do not edit.\npackage {config.package_name}\n\nimport UnstuckRecovery\nimport CampaignTimeline\n\npublic constant int SCENARIO_SCHEMA_VERSION = {world['schemaVersion']}\npublic constant string SCENARIO_SOURCE_SHA256 = \"{runtime['sourceSha256']}\"\npublic constant string SCENARIO_RUNTIME_JSON = \"{encoded}\"\n\npublic function getScenarioRuntimeData() returns string\n\treturn SCENARIO_RUNTIME_JSON\n" + "\n".join(recovery + timeline_lines) + "\n"
    (generated / GENERATED_WURST).write_text(wurst, encoding="utf-8")
    input_paths = (
        config.config_path,
        config.manifest,
        config.scenario_file,
        config.scenario_validator,
        config.project / "wurst.build",
        Path(__file__).resolve(),
        Path(__file__).resolve().with_name("generate_regional_terrain.py"),
        *(path for _, path in config.regional_terrain),
        *terrain_authorities,
        *((config.custom_2d_source, config.custom_2d_builder) if config.custom_2d_source else ()),
    )
    inputs = {}
    for path in input_paths:
        try:
            key = str(path.relative_to(config.project.parent))
        except ValueError:
            # Unit tests load this shared module before copying a fixture project.
            # The reserved key also avoids encoding machine-specific absolute paths.
            key = f"@generator/{path.name}"
        inputs[key] = _sha(path)
    outputs = {name: _sha(generated / name) for name in (GENERATED_WURST, GENERATED_DATA, *terrain_outputs.values())}
    if config.custom_2d_source:
        for path in sorted((generated/"custom-2d").rglob("*")):
            if path.is_file(): outputs[path.relative_to(generated).as_posix()]=_sha(path)
    provenance = {"formatVersion": 1, "generatorVersion": GENERATOR_VERSION, "inputs": inputs, "outputs": outputs}
    (generated / PROVENANCE).write_text(json.dumps(provenance, sort_keys=True, indent=2) + "\n", encoding="utf-8")

def verify_generated(config: BuildConfig, generated: Path) -> None:
    try: provenance = json.loads((generated / PROVENANCE).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error: raise _fail("provenance", f"missing or invalid {PROVENANCE}: {error}") from error
    if provenance.get("generatorVersion") != GENERATOR_VERSION: raise _fail("provenance", "generated data uses a different generator version")
    for relative, expected in provenance.get("inputs", {}).items():
        if relative.startswith("@generator/"):
            path = Path(__file__).resolve().with_name(relative.removeprefix("@generator/"))
        else:
            path = config.project.parent / relative
        if not path.is_file() or _sha(path) != expected: raise _fail("provenance", f"stale generated data: input changed: {relative}")
    for name, expected in provenance.get("outputs", {}).items():
        path = generated / name
        if not path.is_file() or _sha(path) != expected: raise _fail("provenance", f"stale generated data: output changed: {name}")

def _run(stage: str, command: list[str], cwd: Path) -> None:
    result = subprocess.run(command, cwd=cwd, text=True, capture_output=True)
    if result.returncode: raise _fail(stage, f"command exited {result.returncode}: {' '.join(command)}\n{(result.stderr or result.stdout).strip()}")

def _assemble(config: BuildConfig, root: Path, generated: Path, terrain_ids: tuple[str, ...] | None = None) -> Path:
    compile_root = root / "compile"
    shutil.copytree(config.source_map, compile_root / "map" / config.source_map.name)
    shutil.copytree(config.wurst_source, compile_root / "wurst")
    shutil.copy2(config.project / "wurst.build", compile_root / "wurst.build")
    shutil.copy2(generated / GENERATED_WURST, compile_root / "wurst" / GENERATED_WURST)
    runtime_dir = compile_root / "map" / config.source_map.name / "runtime"; runtime_dir.mkdir()
    shutil.copy2(generated / GENERATED_DATA, runtime_dir / GENERATED_DATA); shutil.copy2(generated / PROVENANCE, runtime_dir / PROVENANCE)
    selected = set(terrain_ids) if terrain_ids is not None else {terrain_id for terrain_id, _ in config.regional_terrain}
    for terrain_id, _source in config.regional_terrain:
        if terrain_id not in selected:
            continue
        shutil.copy2(generated / f"terrain-{terrain_id}.json", runtime_dir / f"terrain-{terrain_id}.json")
    if config.custom_2d_source:
        custom=generated/"custom-2d"
        shutil.copy2(custom/"custom-2d-imports.json",runtime_dir/"custom-2d-imports.json")
        for path in sorted((custom/"imports").rglob("*")):
            if path.is_file():
                target=compile_root/"map"/config.source_map.name/path.relative_to(custom/"imports")
                target.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(path,target)
    return compile_root

def _find_archive(root: Path) -> Path:
    files = [p for p in root.rglob("*.w3x") if p.is_file()]
    if not files: raise _fail("map assembly", "Wurst produced no .w3x archive")
    return max(files, key=lambda p: p.stat().st_mtime_ns)

def _inspect(config: BuildConfig, archive: Path, compile_root: Path, terrain_ids: tuple[str, ...] | None = None) -> None:
    data = archive.read_bytes()
    if len(data) < 4 or data[:4] not in (b"MPQ\x1a", b"HM3W", b"PK\x03\x04"): raise _fail("archive inspection", f"unrecognized Warcraft archive: {archive}")
    lua = ""
    if zipfile.is_zipfile(archive):
        with zipfile.ZipFile(archive) as zipped:
            selected = set(terrain_ids) if terrain_ids is not None else {terrain_id for terrain_id, _ in config.regional_terrain}
            names = set(zipped.namelist()); expected = {"war3map.w3i", "war3map.w3e", "war3map.wpm", "war3map.lua", f"runtime/{GENERATED_DATA}", f"runtime/{PROVENANCE}", *(f"runtime/terrain-{terrain_id}.json" for terrain_id in selected)}
            if config.custom_2d_source:
                expected.add("runtime/custom-2d-imports.json")
                custom=json.loads(zipped.read("runtime/custom-2d-imports.json"))
                expected.update(row["importPath"].replace("\\","/") for row in custom["assets"])
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
