#!/usr/bin/env python3
"""Prepare once, then compile one integrated-source Europe variant at a time."""
from dataclasses import replace
import argparse
import difflib
import os
from pathlib import Path
import re
import shutil
import subprocess
import time

from continuation_common import *
from integration_evidence import execution_sources
from wurst_execution import input_hashes, compiler_identity, toolchain_environment, PINNED_COMPILER_SHA256, PINNED_IMAGE
from package_wurst_map import load_config, verify_generated, _assemble, _inspect, _find_archive
from package_wurst_campaign import load_campaign_config, validate_campaign, _localize_runtime, _inspect_audio_runtime, _validate_budget, _inspect_physical_map
from materialize_physical_map import materialize
from warcraft_campaign import MpqReader
from independent_mpq import load_reader, open_archive, read_member


def config_pair():
    config = load_campaign_config(PROJECT / "physical-maps.json")
    physical = next(p for p in config.maps if p.id == "europe_central_east")
    base = load_config(config.map_config_path)
    return config, physical, replace(base, source_map=physical.source_map, manifest=physical.source_manifest)


def pinned_tools():
    assert sha(LAUNCHER) == LAUNCHER_SHA
    assert sha(COMPILER) == PINNED_COMPILER_SHA256
    assert git("rev-parse", "HEAD", cwd=DEPENDENCY) == DEPENDENCY_REVISION
    assert not git("status", "--porcelain", cwd=DEPENDENCY)


def prepare():
    """Reuse the current full-suite generation, localizing a copy for Europe."""
    no_compiler()
    out = ROOT / "europe-seed"
    assert not out.exists(), "Preserve previous assembly; do not overwrite evidence"
    source = check_repository()
    pinned_tools()
    check_frozen()
    upstream = CONTINUATION / "seed"
    upstream_receipt = read(upstream / "receipt.json")
    authored = {name: sha(path) for name, path in sorted(execution_sources(PROJECT).items())}
    assert upstream_receipt["authoredInputs"] == authored
    assert upstream_receipt["sourceIdentity"]["sourceTreeSha256"] == source["sourceTreeSha256"]
    assert upstream_receipt["generatedInputs"] == {p.name: sha(p) for p in (upstream / "compile/wurst").glob("Scenario*.wurst")}
    assert (upstream / "generated/ScenarioData.wurst").read_bytes() == (upstream / "compile/wurst/ScenarioData.wurst").read_bytes()
    generation_before = tree(upstream / "generated")
    out.mkdir()
    receipt = {"format": "pr536_continuation_europe_seed_v1", "status": "running",
        "sourceRevision": REVISION, "sourceIdentityAtAssembly": source,
        "sourceState": "clean_committed_tree", "schema": 17, "nativeStatus": "not_run",
        "playerArtifactProduced": False, "upstreamGenerationReceipt": identity(upstream / "receipt.json"),
        "upstreamGenerationInputs": generation_before, "authoredInputs": authored,
        "generationPolicy": "Copy verified current full-suite generation, then localize only the copy to Europe using current pinned source helpers"}
    began = time.monotonic()
    try:
        config, physical, map_config = config_pair()
        world = validate_campaign(config)
        generated = out / "generated"
        shutil.copytree(upstream / "generated", generated)
        verify_generated(map_config, generated)
        _localize_runtime(config, world, physical, generated)
        _inspect_audio_runtime(physical, generated)
        verify_generated(map_config, generated)
        _validate_budget(map_config, physical, generated)
        compile_root = _assemble(map_config, out, generated, physical.terrain_ids, include_tests=False)
        assert compile_root == out / "compile"
        assert not list((compile_root / "wurst").rglob("*Tests.wurst"))
        map_dir = compile_root / "map" / map_config.source_map.name
        (map_dir / "runtime/build-identity.json").write_text(json.dumps(source, sort_keys=True) + "\n")
        materialize(config.project, map_dir, generated, physical, read(generated / "scenario-runtime.json"))
        shutil.copytree(DEPENDENCY, compile_root / "_build/dependencies/WurstStdlib2")
        for name in ("common.j", "blizzard.j"):
            shutil.copy2(upstream / "compile/_build" / name, compile_root / "_build" / name)
        for path in (compile_root / "wurst").glob("*.wurst"):
            if path.name not in {"ScenarioData.wurst", "ScenarioSettings.wurst"}:
                assert sha(path) == authored["wurst/" + path.name], path.name
        assert source == check_repository()
        assert generation_before == tree(upstream / "generated")
        receipt.update(status="pass", compilerInputs=input_hashes(compile_root),
            dependencyInputs=tree(compile_root / "_build/dependencies/WurstStdlib2"),
            generatedInputs=tree(generated), mapInputs=tree(compile_root / "map"),
            sourceInputsUnchanged=True, upstreamGenerationUnchanged=True,
            compilerSha256=sha(COMPILER), launcher=identity(LAUNCHER), dependencyRevision=DEPENDENCY_REVISION)
    except BaseException as exc:
        receipt.update(status="fail", error=f"{type(exc).__name__}: {exc}")
        raise
    finally:
        receipt["wallSeconds"] = round(time.monotonic() - began, 6)
        write(out / "seed-receipt.json", receipt)
    print(json.dumps({"status": receipt["status"], "seed": str(out), "compilerExecuted": False}), flush=True)


def compile_variant(mode):
    no_compiler()
    source = check_repository()
    pinned_tools()
    seed = ROOT / "europe-seed"
    original = read(seed / "seed-receipt.json")
    assert original["status"] == "pass" and original["sourceIdentityAtAssembly"] == source
    assert input_hashes(seed / "compile") == original["compilerInputs"]
    assert tree(seed / "compile/map") == original["mapInputs"]
    assert tree(seed / "compile/_build/dependencies/WurstStdlib2") == original["dependencyInputs"]
    out = ROOT / mode
    assert not out.exists(), "Preserve previous compile attempt; do not overwrite evidence"
    out.mkdir()
    compile_root = out / "compile"
    shutil.copytree(seed / "compile", compile_root)
    changes = []
    patch = []
    if mode == "baseline":
        for relative in sorted(CHANGED_INPUTS):
            path = compile_root / relative
            before = path.read_bytes()
            after = revert_continuation(relative, before)
            assert before != after
            path.write_bytes(after)
            changes.append({"file": relative, "before": hashlib.sha256(before).hexdigest(), "after": sha(path)})
            patch.extend(difflib.unified_diff(before.decode().splitlines(True), after.decode().splitlines(True),
                                              fromfile="integrated/" + relative, tofile="baseline/" + relative))
        (out / "baseline-reversion.patch").write_text("".join(patch))
    inputs = input_hashes(compile_root)
    assert {name for name in inputs if inputs[name] != original["compilerInputs"][name]} == (CHANGED_INPUTS if mode == "baseline" else set())
    assert inputs.keys() == original["compilerInputs"].keys()
    dependency = tree(compile_root / "_build/dependencies/WurstStdlib2")
    assert dependency == original["dependencyInputs"]
    config, physical, map_config = config_pair()
    receipt = {"format": "pr536_continuation_europe_compile_v1", "status": "running", "mode": mode,
        "sourceRevision": REVISION, "sourceIdentityAtAssembly": source, "schema": 17,
        "sourcePolicy": ("Integrated d669 counterfactual baseline: only empty-public-encode guards and trade digit helper/call reverted in disposable compiler input"
                         if mode == "baseline" else "Exact clean integrated d669 authored production source"),
        "seedReceipt": identity(seed / "seed-receipt.json"), "changedProductionInputs": changes,
        "mapMetadataIdentity": "Shared current d669 metadata; baseline counterfactual is developer-only and not distributable",
        "compilerInputs": inputs, "wurstInputs": {k: v for k, v in inputs.items() if k.startswith("wurst/")},
        "mapInputs": tree(compile_root / "map"), "generatedInputs": original["generatedInputs"],
        "compilerSha256": sha(COMPILER), "launcher": identity(LAUNCHER), "dependencyRevision": DEPENDENCY_REVISION,
        "dependencyInstallInvoked": False, "javaToolOptions": "-Xmx8g -Xmx6g (explicit final 6 GiB override, unchanged from retained compile)",
        "executionEnvironment": "Verified extracted pinned compiler/runtime on workspace host; full OCI image not run",
        "expectedImage": PINNED_IMAGE, "nativeStatus": "not_run", "playerArtifactProduced": False,
        "stages": [], "runner": identity(Path(__file__))}
    assert receipt["mapInputs"] == original["mapInputs"]
    write(out / "inputs-before.json", inputs)
    write(out / "dependency-before.json", dependency)
    write(out / "build-result.json", receipt)
    began = time.monotonic()
    try:
        env = toolchain_environment()
        # Preserve the retained 6 GiB final heap setting, without mutating the caller environment.
        env["JAVA_TOOL_OPTIONS"] = "-Xmx8g -Xmx6g"
        for stage, arguments, marker in (("typecheck", ["typecheck"], "Typecheck succeeded."),
                                        ("build", ["build", "map/" + map_config.source_map.name], "Map built.")):
            no_compiler()
            command = [str(LAUNCHER), *arguments]
            print(f"{mode}: {stage}", flush=True)
            started = time.monotonic()
            result = subprocess.run(command, cwd=compile_root, env=env,
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            log = out / (stage + ".log")
            log.write_text(result.stdout)
            row = {"stage": stage, "command": command, "exitCode": result.returncode,
                   "wallSeconds": round(time.monotonic() - started, 6), "log": identity(log)}
            receipt["stages"].append(row)
            receipt[stage + "ExitCode"] = result.returncode
            write(out / "build-result.json", receipt)
            assert result.returncode == 0 and marker in result.stdout, f"Incomplete {stage}; inspect {log}"
            bad = re.search(r"(?m)(?:Exception in thread|\b[\w.$]*(?:Exception|Error):|^Error in File|No builtin function|Typecheck failed|Build failed)", result.stdout)
            assert not bad, f"Compiler diagnostic {bad.group(0) if bad else ''}; inspect {log}"
            row["compiler"] = compiler_identity(result.stdout)
            assert input_hashes(compile_root) == inputs
            assert tree(compile_root / "_build/dependencies/WurstStdlib2") == dependency
        archive = _find_archive(compile_root / "_build")
        _inspect(map_config, archive, compile_root, physical.terrain_ids)
        _inspect_physical_map(physical, archive)
        own = MpqReader(archive)
        independent = open_archive(load_reader(INDEPENDENT_READER), archive.read_bytes())
        names = ["war3map.lua", "war3map.wpm", "war3map.w3i", "war3map.w3e", "war3mapUnits.doo", "war3map.shd",
                 "runtime/build-identity.json", "runtime/scenario-runtime.json", "runtime/provenance.json", "runtime/physical-map.json"]
        if (compile_root / "map" / map_config.source_map.name / "war3mapMap.blp").is_file():
            names.append("war3mapMap.blp")
        extracted = {}
        for name in names:
            payload = own.read(name)
            assert payload == read_member(independent, name), name
            destination = out / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(payload)
            extracted[name] = identity(destination)
        assert (compile_root / "_build/02_compiled.lua").read_bytes() == (out / "war3map.lua").read_bytes()
        assert source == check_repository()
        assert input_hashes(compile_root) == inputs
        assert tree(compile_root / "_build/dependencies/WurstStdlib2") == dependency
        receipt.update(status="pass", archive=identity(archive), extracted=extracted,
            independentKnownMembersEqual=True, independentReader=identity(INDEPENDENT_READER),
            independentReaderLimitation="Known members checked; mpyq does not decrypt Grill's encrypted listfile, so this is not an exhaustive archive inventory",
            compilerOutputEqualsArchiveLua=True, authoredSourcesUnchanged=True,
            compilerInputsUnchangedDuringBuild=True, dependencyInputsUnchanged=True,
            compiledScript=str(out / "war3map.lua"), compiledScriptSha256=sha(out / "war3map.lua"),
            compiledScriptBytes=(out / "war3map.lua").stat().st_size)
    except BaseException as exc:
        receipt.update(status="fail", error=f"{type(exc).__name__}: {exc}")
        raise
    finally:
        receipt["wallSeconds"] = round(time.monotonic() - began, 6)
        write(out / "inputs-after.json", input_hashes(compile_root))
        write(out / "build-result.json", receipt)
    print(json.dumps({key: receipt[key] for key in ("mode", "status", "compiledScriptSha256", "compiledScriptBytes", "wallSeconds")}), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "baseline", "revised"))
    args = parser.parse_args()
    prepare() if args.mode == "prepare" else compile_variant(args.mode)
