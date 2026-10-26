#!/usr/bin/env python3
"""Run the retained full-scale case with reviewed current-catalogue counts only."""
import argparse
from pathlib import Path
import subprocess
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from continuation_common import *
from compare_completed_startup import ADAPTATION, PREPARATION, CARDINALITY, check_adaptation


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "full-scale-revised-current-catalogue")
    args = parser.parse_args()
    no_compiler()
    assert not args.output.exists(), "Preserve prior evidence; use a fresh full-scale run directory"
    prepared, proof, frozen = check_adaptation()
    comparison_path = ROOT / "startup-comparison/comparison-current-catalogue.json"
    comparison = read(comparison_path)
    assert comparison["status"] == "pass_under_explicit_models"
    assert comparison["catalogueCardinality"] == identity(CARDINALITY)
    assert comparison["adaptationPreparation"] == identity(PREPARATION)
    assert comparison["adaptationReview"] == identity(ADAPTATION / "static-review.json")
    build_path = ROOT / "revised/build-result.json"
    build = load_build(build_path, "revised")
    assert build["wurstInputs"]["wurst/PlayableTrade.wurst"] == REVISED_TRADE_SHA
    args.output.mkdir(parents=True)
    original = FROZEN / "verify-trade-full-scale-original.py"
    runner_path = ADAPTATION / "verify-trade-full-scale-current-catalogue.py"
    case_path = ADAPTATION / "full-scale-roundtrip-current-catalogue.lua"
    changes = read(ADAPTATION / "preparation-transformations.json")
    result_path = args.output / "result.json"
    command = [sys.executable, "-B", str(runner_path), "--lua-path", build["compiledScript"],
               "--build-receipt", str(build_path), "--library", str(LIBRARY), "--report", str(result_path)]
    receipt = {"format": "pr536_continuation_current_catalogue_full_scale_binding_v1", "status": "running",
        "sourceRevision": REVISION, "schema": 17, "nativeStatus": "not_run", "playerArtifactProduced": False,
        "compiledScript": identity(Path(build["compiledScript"])), "buildReceipt": identity(build_path),
        "sourceSha256": REVISED_TRADE_SHA, "frozenInputs": frozen,
        "runner": identity(Path(__file__)), "retainedRunner": identity(original), "boundRunner": identity(runner_path),
        "retainedCase": identity(FROZEN / "full-scale-roundtrip.lua"), "adaptedCase": identity(case_path),
        "catalogueCardinality": identity(CARDINALITY), "adaptationPreparation": identity(PREPARATION),
        "adaptationReview": identity(ADAPTATION / "static-review.json"), "startupComparison": identity(comparison_path),
        "bindingChanges": changes["runner"]["bindings"],
        "caseWholeTokenReplacements": changes["case"]["wholeTokenReplacements"],
        "runnerWholeTokenReplacements": changes["runner"]["wholeTokenReplacements"],
        "fullScaleLuaCaseChanged": True, "fullScaleCaseChangeScope": "Only whole-token 8422 to 8426 and 8421 to 8425",
        "nativeStubsChanged": False, "budgetsChanged": False, "allOtherFullScaleAssertionsUnchanged": True,
        "instructionBudgetPerPhase": 2_000_000_000, "productionFunctionOverrides": False,
        "command": command}
    began = time.monotonic()
    try:
        print("Running reviewed current-catalogue full-scale Lua case on revised archived Lua", flush=True)
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
        assert full["inputs"]["roundtripHarness"] == identity(runner_path)
        assert full["inputs"]["roundtripCase"] == identity(case_path)
        assert full["runtimeLibrary"]["sha256"] == LIBRARY_SHA and full["runtimeVersion"] == "Lua 5.3"
        assert full["instructionBudgetPerPhase"] == 2_000_000_000
        assert full["productionFunctionOverrides"] is False and full["compiledFunctionsCheckedUnchanged"] > 0
        assert full["execution"]["roundtrip"]["marketCount"] == proof["marketCount"]
        check_adaptation()
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
