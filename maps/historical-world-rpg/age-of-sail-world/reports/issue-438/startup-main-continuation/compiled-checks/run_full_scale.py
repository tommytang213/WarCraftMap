#!/usr/bin/env python3
"""Rebind the retained full-scale trade runner to the current revised archive."""
import argparse
from pathlib import Path
import subprocess
import sys
import time

from continuation_common import *


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "full-scale-revised")
    args = parser.parse_args()
    no_compiler()
    assert not args.output.exists(), "Preserve prior evidence; use a fresh full-scale run directory"
    frozen = check_frozen()
    build_path = ROOT / "revised/build-result.json"
    build = load_build(build_path, "revised")
    assert build["wurstInputs"]["wurst/PlayableTrade.wurst"] == REVISED_TRADE_SHA
    args.output.mkdir(parents=True)
    original = FROZEN / "verify-trade-full-scale-original.py"
    runner = original.read_text()
    substitutions = {
        "ROOT = Path(__file__).resolve().parent": "ROOT = Path(" + repr(str(FROZEN)) + ")",
        "SOURCE_SHA = '0730e299ae8fa093e317bb586f7b0992dd30e8ca86082be84637653c3865ecda'": "SOURCE_SHA = " + repr(REVISED_TRADE_SHA),
    }
    for before, after in substitutions.items():
        assert runner.count(before) == 1, before
        runner = runner.replace(before, after)
    runner_path = args.output / "verify-trade-full-scale.py"
    runner_path.write_text(runner)
    result_path = args.output / "result.json"
    command = [sys.executable, "-B", str(runner_path), "--lua-path", build["compiledScript"],
               "--build-receipt", str(build_path), "--library", str(LIBRARY), "--report", str(result_path)]
    receipt = {"format": "pr536_continuation_full_scale_binding_v1", "status": "running",
        "sourceRevision": REVISION, "nativeStatus": "not_run", "playerArtifactProduced": False,
        "compiledScript": identity(Path(build["compiledScript"])), "buildReceipt": identity(build_path),
        "sourceSha256": REVISED_TRADE_SHA, "frozenInputs": frozen,
        "runner": identity(Path(__file__)), "retainedRunner": identity(original), "boundRunner": identity(runner_path),
        "bindingChanges": [{"before": before, "after": after} for before, after in substitutions.items()],
        "fullScaleLuaCaseChanged": False, "nativeStubsChanged": False, "budgetsChanged": False,
        "instructionBudgetPerPhase": 2_000_000_000, "productionFunctionOverrides": False,
        "command": command}
    began = time.monotonic()
    try:
        print("Running unchanged full-scale Lua case on revised archived Lua", flush=True)
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        log = args.output / "execution.log"
        log.write_text(result.stdout)
        receipt.update(exitCode=result.returncode, log=identity(log))
        assert result.returncode == 0, f"Full-scale regression failed; inspect {log}"
        full = read(result_path)
        assert full["status"] == "pass_full_scale_roundtrip_under_explicit_stubs"
        assert full["inputs"]["compiledLua"] == identity(Path(build["compiledScript"]))
        assert full["inputs"]["buildReceipt"] == identity(build_path)
        assert full["inputs"]["productionSourceSha256"] == REVISED_TRADE_SHA
        assert full["runtimeLibrary"]["sha256"] == LIBRARY_SHA and full["runtimeVersion"] == "Lua 5.3"
        assert full["instructionBudgetPerPhase"] == 2_000_000_000
        assert full["productionFunctionOverrides"] is False and full["compiledFunctionsCheckedUnchanged"] > 0
        check_frozen()
        load_build(build_path, "revised")
        receipt.update(status="pass_full_scale_roundtrip_under_explicit_stubs", result=identity(result_path))
    except BaseException as exc:
        receipt.update(status="fail", error=f"{type(exc).__name__}: {exc}")
        if result_path.is_file():
            receipt["result"] = identity(result_path)
        raise
    finally:
        receipt["wallSeconds"] = round(time.monotonic() - began, 6)
        write(args.output / "receipt.json", receipt)
    print(json.dumps({key: receipt[key] for key in ("status", "wallSeconds")}), flush=True)


if __name__ == "__main__":
    main()
