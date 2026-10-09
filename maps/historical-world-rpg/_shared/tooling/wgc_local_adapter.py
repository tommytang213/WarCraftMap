#!/usr/bin/env python3
"""Opt-in, local-only WGC 1.1 adapter. Default: no process, native not_run.

Third-party code is not bundled. A local owner approval must pin ALL files in a
reviewed WGC/Lua bundle, license/dependency review and the actual game executable.
Positive/negative controls qualify this client/context before the target map.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

SLOTS = ["slot0,team0,raceHuman,color0,health100,human",
         "slot1,team0,raceHuman,color1,health100,observer"]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def checked_file(path, expected):
    path = Path(path).resolve(strict=True)
    if not re.fullmatch(r"[0-9a-f]{64}", expected) or digest(path.read_bytes()) != expected:
        raise ValueError("local file SHA-256 mismatch")
    return path


def bundle_path(root, relative):
    if not isinstance(relative, str) or not re.fullmatch(r"[A-Za-z0-9_. /-]+", relative):
        raise ValueError("unsafe reviewed bundle path")
    path = (root / relative).resolve(strict=True)
    path.relative_to(root.resolve(strict=True))
    return path


def approve(config):
    if (config.get("format") != "wgc_local_approval_v1" or config.get("ownerApproved") is not True
            or config.get("upstreamVersion") != "1.1"
            or config.get("review") != {"source": True, "dependencies": True, "license": True}):
        raise ValueError("native_runner_unavailable: reviewed, owner-approved WGC 1.1 copy required")
    if not re.fullmatch(r"3\.0\.\d+\.\d+", config.get("clientBuild", "")):
        raise ValueError("exact retail 3.0.x client build required")
    root = Path(config["bundle"]).resolve(strict=True)
    pins = config["files"]
    actual = {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()}
    if not pins or actual != set(pins) or any(p.is_symlink() for p in root.rglob("*")):
        raise ValueError("review must pin the complete local WGC/Lua bundle")
    for name, sha in pins.items(): checked_file(bundle_path(root, name), sha)
    for name in (config["lua"], config["script"]):
        if name not in pins: raise ValueError("launcher not included in reviewed pins")
    if not config["script"].endswith(".lua") or not config["lua"].endswith(".exe"):
        raise ValueError("local adapter requires Lua source and a reviewed Windows Lua executable")
    exe = checked_file(config["gameExe"], config["gameExeSha256"])
    game_root = Path(config["gameRoot"]).resolve(strict=True)
    exe.relative_to(game_root)
    if config.get("allowGameRootScratch") is not True:
        raise ValueError("explicit local opt-in to WGC game-root scratch writes required")
    positive = config["positiveControl"]
    checked_file(positive["path"], positive["sha256"])
    if (positive.get("knownWorkingClientBuild") != config["clientBuild"]
            or positive.get("scriptLanguage") != "Lua" or not positive.get("provenance")):
        raise ValueError("known-working Lua control and same-client native provenance required")
    # The source review must confirm WGC's current write surface before enabling
    # the adapter. Never infer it from old 1.27/1.31 documentation.
    if config.get("reviewedWriteScope") != "session_and_game_root_map-wgc-test_only":
        raise ValueError("WGC write scope has not been reviewed")
    if config.get("reviewedLoadfileMode") != "reforged_absolute":
        raise ValueError("source review must establish the actual -loadfile command semantics")
    return {"clientBuild": config["clientBuild"], "gameExeSha256": config["gameExeSha256"],
            "bundleSha256": digest(json.dumps(pins, sort_keys=True).encode()),
            "positiveSha256": positive["sha256"], "slots": SLOTS, "gamespeed": 1,
            "requestedLoadfileMode": "reforged_absolute", "timeoutSeconds": 90}


def command(config, bundle, game_root, game_exe, map_file, wgc_file):
    # -E prevents unreviewed LUA_INIT/LUA_PATH environment injection.
    return [str(bundle / config["lua"]), "-E", str(bundle / config["script"]),
            "--reforged", "--gameroot", str(game_root), "--gameexe", str(game_exe),
            "--map", str(map_file), "--wgc", str(wgc_file), "--gamespeed", "1",
            "--slot", SLOTS[0], "--slot", SLOTS[1], "--gameargs", "-windowed -launch"]


def log_events(before: bytes, after: bytes, map_filename: str):
    # Read only new content from the explicitly selected War3Log. Export counts,
    # never raw lines, user paths, account details or Blizzard dump files.
    new = after[len(before):] if after.startswith(before) else after
    text = new.decode("utf-8", errors="replace")
    events = {"openingMap": 0, "playedLoaderEntry": 0}
    for line in text.splitlines():
        match = re.search(r"\b(Opening map - |Played )(.+)$", line)
        if match and match[2].replace("\\", "/").rsplit("/", 1)[-1].casefold() == map_filename.casefold():
            events["openingMap" if match[1].startswith("Opening") else "playedLoaderEntry"] += 1
    return events


def qualify(package, context):
    for case, required in (("positive", "gameplay_frames"), ("negative", "load_rejected")):
        receipt = json.loads((package / f"{case}-result.json").read_text())
        expected = (context["positiveSha256"] if case == "positive" else
                    json.loads((package / "diagnostic.json").read_text())["negativeControl"]["sha256"])
        if (receipt.get("context") != context or receipt.get("observedMilestone") != required
                or receipt.get("w3xSha256") != expected or receipt.get("nativeAttempt") is not True):
            raise ValueError("native_runner_unavailable: same-client control qualification missing")
        if case == "positive" and (receipt.get("logEvents", {}).get("openingMap", 0) < 1
                                   or receipt.get("loadfileSemantics") != "confirmed_in_this_control_context"):
            raise ValueError("native_runner_unavailable: positive map/path qualification missing")


def execute(package: Path, approval: Path, case: str):
    if os.name != "nt":
        raise ValueError("native_runner_unavailable: opt-in local Windows execution only")
    config = json.loads(approval.read_text())
    context = approve(config)
    # Record the executable's actual version, not only a typed client label.
    version = subprocess.check_output([
        "powershell.exe", "-NoProfile", "-NonInteractive", "-Command",
        "(Get-Item -LiteralPath $env:WGC_DIAGNOSTIC_EXE).VersionInfo.FileVersion"],
        env={**os.environ, "WGC_DIAGNOSTIC_EXE": config["gameExe"]}, text=True).strip()
    if version != config["clientBuild"]:
        raise ValueError("actual executable FileVersion differs from approved client build")
    tasks = subprocess.check_output(["tasklist.exe", "/FI", "IMAGENAME eq Warcraft III.exe", "/FO", "CSV"], text=True)
    if '"warcraft iii.exe"' in tasks.casefold():
        raise ValueError("close the existing game before an isolated local diagnostic")
    manifest = json.loads((package / "diagnostic.json").read_text())
    if case == "target":
        qualify(package, context)
        source = checked_file(package / manifest["mapFile"], manifest["w3xSha256"])
    elif case == "negative":
        source = checked_file(package / manifest["negativeControl"]["file"], manifest["negativeControl"]["sha256"])
    else:
        source = checked_file(config["positiveControl"]["path"], context["positiveSha256"])
    game_root = Path(config["gameRoot"]).resolve()
    scratch = game_root / "map-wgc-test"
    if scratch.exists():
        raise ValueError("WGC scratch already exists; refuse to modify or clean someone else's files")
    log = Path(config["war3Log"])
    before = log.read_bytes() if log.exists() else b""
    receipt = {"context": context, "w3nSha256": manifest["w3nSha256"], "w3xSha256": digest(source.read_bytes()),
               "source_revision": manifest["source_revision"], "windowsClientBuild": version,
               "map_standalone_native": "not_run", "campaign_native": "not_run",
               "nativeAttempt": False, "observedMilestone": "none", "case": case}
    result_path = package / f"{case}-result.json"
    if result_path.exists():
        raise ValueError("retain the earlier result; use a new package for a new session")
    try:
        with tempfile.TemporaryDirectory(prefix="wgc-local-", dir=package) as tmp:
            session = Path(tmp)
            bundle = session / "reviewed-wgc"
            shutil.copytree(config["bundle"], bundle)
            for name, sha in config["files"].items(): checked_file(bundle_path(bundle, name), sha)
            target = session / source.name
            shutil.copyfile(source, target)
            checked_file(target, receipt["w3xSha256"])
            # Claim the scratch directory ourselves; cleanup applies only to it.
            from windows_diagnostic_job import run
            scratch.mkdir()
            receipt["nativeAttempt"] = True
            try:
                receipt["launcher"] = run(command(config, bundle, game_root, Path(config["gameExe"]),
                                                   target, session / "launch.wgc"), str(bundle), 90)
            finally:
                shutil.rmtree(scratch)
            after = log.read_bytes() if log.exists() else b""
            receipt["logEvents"] = log_events(before, after, target.name)
            receipt["observedMilestone"] = input(
                "Observed milestone (origin_selection / gameplay_frames / load_rejected / native_error / none): ").strip()
            allowed = {"origin_selection", "gameplay_frames", "load_rejected", "native_error", "none"}
            if receipt["observedMilestone"] not in allowed:
                receipt["observedMilestone"] = "none"
            if case == "target":
                accepted = (receipt["observedMilestone"] == "origin_selection" and receipt["logEvents"]["openingMap"] > 0)
                receipt["map_standalone_native"] = "passed" if accepted else "failed"
                receipt["failureMeaning"] = "failed means required origin milestone not established; not automatically a native crash"
            receipt["loadfileSemantics"] = ("confirmed_in_this_control_context" if case == "positive" and
                                           receipt["observedMilestone"] == "gameplay_frames" and
                                           receipt["logEvents"]["openingMap"] > 0 else "not_independently_confirmed")
    finally:
        if case == "target" and receipt["nativeAttempt"] and receipt["map_standalone_native"] == "not_run":
            receipt["map_standalone_native"] = "failed"
            receipt["failureMeaning"] = "attempt incomplete; origin-selection acceptance not established"
        result_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    return receipt


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--package", type=Path, default=Path(__file__).resolve().parent)
    p.add_argument("--approval", type=Path)
    p.add_argument("--case", choices=("positive", "negative", "target"), default="target")
    p.add_argument("--run", action="store_true", help="owner-initiated local test; never use in CI")
    a = p.parse_args()
    status = {"runnerStatus": "native_runner_unavailable", "map_standalone_native": "not_run",
              "campaign_native": "not_run", "observedMilestone": "none"}
    if a.run:
        if not a.approval: p.error("--run requires a separately reviewed local --approval file")
        try:
            status = execute(a.package.resolve(), a.approval, a.case)
        except (ValueError, OSError, KeyError) as error:
            # Do not export local paths/error contents into a shareable receipt.
            print(json.dumps(status)); p.exit(2, "Local runner unavailable or validation failed; review local configuration.\n")
    print(json.dumps(status, indent=2))


if __name__ == "__main__":
    main()
