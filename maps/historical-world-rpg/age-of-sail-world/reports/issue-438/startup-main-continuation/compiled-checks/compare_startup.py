#!/usr/bin/env python3
"""Run the unchanged retained startup/first-callback models on both archives."""
import argparse
import gzip
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

from continuation_common import *


def observe(label, build_path, out):
    build = load_build(build_path, label)
    script = Path(build["compiledScript"])
    run = out / label
    frozen = run / "frozen"
    observer = run / "observer"
    frozen.mkdir(parents=True)
    observer.mkdir()
    for name in ("probe-lua54-initialization.py", "late-startup-stubs.lua"):
        shutil.copy2(FROZEN / name, frozen / name)
    os.environ["WC3_LUA_PROBE_LIBRARY"] = str(LIBRARY)
    harness = frozen / "probe-lua54-initialization.py"
    spec = importlib.util.spec_from_file_location("frozen_startup_" + label, harness)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    print("Running unchanged frozen probe: " + label, flush=True)
    result = module.probe("europe_central_east", "startup-complete", 2_000_000_000,
                          lua_path=script, report_label=label)
    result["boundBuildReceipt"] = identity(build_path)
    result["nativeStatus"] = "not_run"
    result["runner"] = identity(Path(__file__))
    write(frozen / "result.json", result)
    assert result["status"] == "completed_under_stubs", result.get("error")
    assert result["campaignStarted"] and result["campaignRegistered"]
    assert result["compiledLuaSha256"] == build["compiledScriptSha256"]
    shutil.copy2(FROZEN / "observe-startup.lua", observer / "observe-startup.lua")
    runner = (FROZEN / "observe-startup-template.py").read_text()
    substitutions = {
        "OUT=ROOT/'validation-536/native-boundary-audit/europe-repair/observer'": "OUT=Path(" + repr(str(observer)) + ")",
        "EVIDENCE=ROOT/'WarCraftMap/maps/historical-world-rpg/age-of-sail-world/reports/issue-438/trade-startup'": "EVIDENCE=Path(" + repr(str(frozen)) + ")",
        "SCRIPT=ROOT/'validation-536/native-boundary-audit/europe-repair/war3map.lua'": "SCRIPT=Path(" + repr(str(script)) + ")",
        "RECEIPT=ROOT/'validation-536/native-boundary-audit/europe-repair/build-result.json'": "RECEIPT=Path(" + repr(str(build_path)) + ")",
    }
    for before, after in substitutions.items():
        assert runner.count(before) == 1, before
        runner = runner.replace(before, after)
    runner_path = observer / "observe-startup.py"
    runner_path.write_text(runner)
    print("Running unchanged parse-once observer Lua: " + label, flush=True)
    subprocess.run([sys.executable, "-B", str(runner_path)], check=True)
    observed = read(observer / "startup-and-first-callbacks.json")
    assert observed["status"] == "completed_under_explicit_stubs"
    assert observed["execution"]["startup"]["nativeCalls"] == result["nativeCalls"]
    assert observed["execution"]["startup"]["started"] and observed["execution"]["startup"]["registered"]
    callbacks = observed["execution"]["callbackPhase"]
    assert callbacks["completed"] and callbacks["callbackCount"] == 37 and callbacks["throughSeconds"] == 1.001
    assert callbacks["budget"] == 200_000_000
    assert not observed["execution"]["callbackErrors"]
    assert observed["inputs"]["observer"]["sha256"] == sha(FROZEN / "observe-startup.lua")
    assert len(observed["cachePayloads"]) == 4
    assert identity(script)["sha256"] == build["compiledScriptSha256"]
    return {"frozen": result, "observer": observed, "directory": run, "build": identity(build_path)}


def phases(report):
    names = {"PlayableCampaignState_PlayableCampaignState_captureAuthoritativeState",
             "PlayableCampaignState_PlayableCampaignState_validateAuthoritativeState",
             "MilitarySettlementRuntime_MilitarySettlementRuntime_parseSnapshot", "runtimeChecksum"}
    return [{key: row[key] for key in ("name", "nativeCalls", "instructions", "completed")}
            for row in report["execution"]["phases"] if row["name"] in names]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "startup-comparison")
    args = parser.parse_args()
    no_compiler()
    assert not args.output.exists(), "Preserve prior evidence; choose a fresh output directory"
    frozen_inputs = check_frozen()
    builds = {mode: load_build(ROOT / mode / "build-result.json", mode) for mode in ("baseline", "revised")}
    declaration = b"function MilitarySettlementRuntime_MilitarySettlementRuntime_validateSnapshot("
    for build in builds.values():
        assert declaration not in Path(build["compiledScript"]).read_bytes(), "Both arms use the existing parse-once production path"
    assert builds["baseline"]["generatedInputs"] == builds["revised"]["generatedInputs"]
    args.output.mkdir(parents=True)
    report = {"format": "pr536_continuation_compiled_startup_comparison_v1", "status": "running",
        "sourceRevision": REVISION, "schema": 17, "nativeStatus": "not_run", "nativeHangResolution": "not_established",
        "runner": identity(Path(__file__)), "frozenInputs": frozen_inputs,
        "baselineMeaning": "Integrated d669 counterfactual; only two empty-encode guards and the ASCII digit fast path are reverted",
        "observerVariant": {"sameForBothArms": True, "validateSnapshotWrapperAbsentInBoth": True,
                            "observerLuaChanged": False, "productionFunctionOverridesAdded": False},
        "historicalCounts": "The previous 15,095,868 SubString and 37,931 StringHash baseline constants described a different pre-main comparison and are not gates for these schema17 inputs",
        "limitations": [
            "Stock Lua5.3.6 with frozen explicit native stubs is not Warcraft execution.",
            "The observer delegates production functions but is not a function-identity gate.",
            "Argument byte volumes measure modeled traffic, not proof that Warcraft copies these bytes.",
            "Unchanged budgets: 2B sampled startup instructions and 200M sampled callback instructions.",
            "Callbacks end after 1.001 synthetic seconds; no rendering, assets, disk cache or real native scheduling is exercised.",
            "Synthetic orders report success but do not move units. This cannot establish terrain or controllable-unit acceptance.",
            "No native timing claim or wall-time speedup ratio. These are developer artifacts, not a player release candidate."]}
    began = time.monotonic()
    try:
        before = observe("baseline", ROOT / "baseline/build-result.json", args.output)
        after = observe("revised", ROOT / "revised/build-result.json", args.output)
        old, new = before["frozen"], after["frozen"]
        for key in ("runtimeCounts", "tradeSnapshotIdentity", "finalCacheRequest"):
            assert old[key] == new[key], key
        assert new["runtimeCounts"]["markets"] == 8422 and new["runtimeCounts"]["stores"] == 829
        assert new["nativeCalls"]["SubString"] < old["nativeCalls"]["SubString"], "Digit fast path did not reduce modeled startup SubString calls"
        payloads = []
        old_rows, new_rows = before["observer"]["cachePayloads"], after["observer"]["cachePayloads"]
        assert len(old_rows) == len(new_rows) == 4
        for index, (old_row, new_row) in enumerate(zip(old_rows, new_rows), 1):
            assert (old_row["mission"], old_row["key"]) == (new_row["mission"], new_row["key"])
            old_path = before["directory"] / "observer" / f"cache-write-{index}.txt.gz"
            new_path = after["directory"] / "observer" / f"cache-write-{index}.txt.gz"
            old_data, new_data = gzip.decompress(old_path.read_bytes()), gzip.decompress(new_path.read_bytes())
            assert old_data == new_data
            digest = hashlib.sha256(new_data).hexdigest()
            assert len(old_data) == old_row["bytes"] == new_row["bytes"]
            assert digest == old_row["sha256"] == new_row["sha256"]
            non_ascii = sum(byte >= 128 for byte in new_data)
            payloads.append({"index": index, "mission": new_row["mission"], "key": new_row["key"],
                "bytes": len(new_data), "sha256": digest, "exactBaselineBytesEqual": True,
                "baselineCompressed": identity(old_path), "revisedCompressed": identity(new_path),
                "asciiOnly": non_ascii == 0, "nonAsciiByteCount": non_ascii})
        names = sorted(set(old["nativeCalls"]) | set(new["nativeCalls"]))
        report.update(status="pass_under_explicit_models", baselineBuild=before["build"], revisedBuild=after["build"],
            nativeCalls={name: {"before": old["nativeCalls"].get(name, 0), "after": new["nativeCalls"].get(name, 0),
                "difference": new["nativeCalls"].get(name, 0) - old["nativeCalls"].get(name, 0)} for name in names},
            instructionSamples={"before": old["instructions"], "after": new["instructions"]},
            runtimeCounts=new["runtimeCounts"], tradeSnapshotIdentity=new["tradeSnapshotIdentity"],
            finalCacheRequest=new["finalCacheRequest"], cachePayloads=payloads,
            cachePayloadBytesTotal=sum(row["bytes"] for row in payloads),
            nativeArgumentVolumeScope="Startup and modeled callbacks through 1.001 simulated seconds",
            nativeArgumentVolumes={"before": before["observer"]["execution"]["nativeArgumentVolumes"],
                                   "after": after["observer"]["execution"]["nativeArgumentVolumes"]},
            phases={"before": phases(before["observer"]), "after": phases(after["observer"])},
            callbackPhases={"before": before["observer"]["execution"]["callbackPhase"],
                            "after": after["observer"]["execution"]["callbackPhase"]})
        check_frozen()
        for mode in ("baseline", "revised"):
            load_build(ROOT / mode / "build-result.json", mode)
    except BaseException as exc:
        report.update(status="fail", error=f"{type(exc).__name__}: {exc}")
        raise
    finally:
        report["wallSeconds"] = round(time.monotonic() - began, 6)
        write(args.output / "comparison.json", report)
    print(json.dumps({key: report[key] for key in ("status", "instructionSamples", "cachePayloadBytesTotal")}), flush=True)


if __name__ == "__main__":
    main()
