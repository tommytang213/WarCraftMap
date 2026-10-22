#!/usr/bin/env python3
"""Derive the current-catalogue comparison from retained completed outputs only."""
import gzip
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from continuation_common import *

ADAPTATION = Path(__file__).resolve().parent
PREPARATION = ADAPTATION / "preparation-receipt.json"
CARDINALITY = ROOT / "catalogue-cardinality.json"
COMPLETED = ROOT / "startup-comparison"


def check_adaptation():
    """Read-only bindings; never load a Lua runtime or launch a model/compiler."""
    no_compiler()
    source = check_repository()
    frozen = check_frozen()
    prepared = read(PREPARATION)
    assert prepared["status"] == "prepared_for_review_not_executed"
    assert prepared["sourceIdentity"] == source
    for group in ("retainedInputs", "adaptedFiles", "patches"):
        for expected in prepared[group].values():
            assert identity(Path(expected["path"])) == expected, expected["path"]
    assert identity(CARDINALITY) == prepared["catalogueCardinality"]
    proof = read(CARDINALITY)
    assert proof["status"] == "pass_static_source_derivation"
    assert proof["sourceIdentity"] == source and proof["schema"] == 17
    assert proof["marketCount"] == 8426 and proof["lastMarketIndex"] == 8425
    assert proof["storeCount"] == 829 and proof["lastStoreIndex"] == 828
    assert proof["baseMarketCount"] == 8422 and proof["industryAddedMarketCount"] == 4
    assert proof["marketCount"] == proof["baseMarketCount"] + proof["industryAddedMarketCount"]
    assert proof["nativeStatus"] == "not_run"
    assert proof["validationPerformed"]["modelExecution"] is False
    for group in ("inputs", "sourceInputs"):
        for expected in proof[group].values():
            assert identity(Path(expected["path"])) == expected, expected["path"]
    review = read(ADAPTATION / "static-review.json")
    assert review["status"] == "pass_static_review" and not review["blockingFindings"]
    assert review["preparationReceipt"] == identity(PREPARATION)
    return prepared, proof, frozen


def read_completed(label, build_path):
    build = load_build(build_path, label)
    script = Path(build["compiledScript"])
    run = COMPLETED / label
    frozen = run / "frozen"
    observer = run / "observer"
    result = read(frozen / "result.json")
    assert result["status"] == "completed_under_stubs", result.get("error")
    assert result["campaignStarted"] and result["campaignRegistered"]
    assert result["compiledLuaSha256"] == build["compiledScriptSha256"]
    assert result["boundBuildReceipt"] == identity(build_path)
    assert Path(result["compiledLuaPath"]) == script
    assert result["instructionBudget"] == 2_000_000_000
    assert result["nativeStatus"] == "not_run"
    assert result["runner"] == identity(ROOT / "compare_startup.py")
    assert result["harnessSha256"] == sha(FROZEN / "probe-lua54-initialization.py")
    assert result["lateNativeStubsSha256"] == sha(FROZEN / "late-startup-stubs.lua")
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
    assert observed["inputs"]["buildReceipt"] == identity(build_path)
    assert observed["inputs"]["compiledLua"] == identity(script)
    assert observed["inputs"]["library"] == identity(LIBRARY)
    assert observed["nativeStatus"] == "not_run"
    for expected in observed["inputs"].values():
        assert identity(Path(expected["path"])) == expected
    snapshot = identity(Path(result["tradeSnapshotPath"]))
    assert {key: snapshot[key] for key in ("bytes", "sha256")} == result["tradeSnapshotIdentity"]
    return {"frozen": result, "observer": observed, "directory": run, "build": identity(build_path),
            "retainedResults": {"frozen": identity(frozen / "result.json"),
                                "observer": identity(observer / "startup-and-first-callbacks.json")}}


def phases(report):
    names = {"PlayableCampaignState_PlayableCampaignState_captureAuthoritativeState",
             "PlayableCampaignState_PlayableCampaignState_validateAuthoritativeState",
             "MilitarySettlementRuntime_MilitarySettlementRuntime_parseSnapshot", "runtimeChecksum"}
    return [{key: row[key] for key in ("name", "nativeCalls", "instructions", "completed")}
            for row in report["execution"]["phases"] if row["name"] in names]


def main():
    output = COMPLETED / "comparison-current-catalogue.json"
    assert not output.exists(), "Preserve all earlier evidence; this derivation writes one fresh result"
    prepared, proof, frozen_inputs = check_adaptation()
    failed = read(COMPLETED / "comparison.json")
    assert failed["status"] == "fail" and failed["error"] == "AssertionError: "
    assert failed["sourceRevision"] == REVISION and failed["schema"] == 17
    assert failed["runner"] == identity(ROOT / "compare_startup.py")
    builds = {mode: load_build(ROOT / mode / "build-result.json", mode) for mode in ("baseline", "revised")}
    declaration = b"function MilitarySettlementRuntime_MilitarySettlementRuntime_validateSnapshot("
    for build in builds.values():
        assert declaration not in Path(build["compiledScript"]).read_bytes(), "Both arms use the existing parse-once production path"
    assert builds["baseline"]["generatedInputs"] == builds["revised"]["generatedInputs"]
    report = {key: value for key, value in failed.items() if key not in ("error", "wallSeconds")}
    report.update(format="pr536_current_catalogue_retained_startup_comparison_v1", status="running",
        runner=identity(Path(__file__)), frozenInputs=frozen_inputs,
        originalFailedComparison=identity(COMPLETED / "comparison.json"),
        adaptationPreparation=identity(PREPARATION), adaptationReview=identity(ADAPTATION / "static-review.json"),
        catalogueCardinality=identity(CARDINALITY), modelExecutedByThisDerivation=False,
        inputEvidence="Already completed original frozen and parse-once observer outputs; no model is rerun",
        assertionChanges=[{"field": "runtimeCounts.markets", "historical": 8422,
                           "currentSourceExpectation": proof["marketCount"]}],
        allOtherOriginalComparisonConditionsRetained=True)
    began = time.monotonic()
    try:
        before = read_completed("baseline", ROOT / "baseline/build-result.json")
        after = read_completed("revised", ROOT / "revised/build-result.json")
        old, new = before["frozen"], after["frozen"]
        for key in ("runtimeCounts", "tradeSnapshotIdentity", "finalCacheRequest"):
            assert old[key] == new[key], key
        assert new["runtimeCounts"]["markets"] == proof["marketCount"] and new["runtimeCounts"]["stores"] == 829
        assert new["nativeCalls"]["SubString"] < old["nativeCalls"]["SubString"], "Digit fast path did not reduce modeled startup SubString calls"
        payloads = []
        old_rows, new_rows = before["observer"]["cachePayloads"], after["observer"]["cachePayloads"]
        assert len(old_rows) == len(new_rows) == 4
        for index, (old_row, new_row) in enumerate(zip(old_rows, new_rows), 1):
            assert (old_row["mission"], old_row["key"]) == (new_row["mission"], new_row["key"])
            old_path = before["directory"] / "observer" / f"cache-write-{index}.txt.gz"
            new_path = after["directory"] / "observer" / f"cache-write-{index}.txt.gz"
            assert identity(old_path) == old_row["compressed"]
            assert identity(new_path) == new_row["compressed"]
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
            retainedResults={"baseline": before["retainedResults"], "revised": after["retainedResults"]},
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
        check_adaptation()
        for mode in ("baseline", "revised"):
            load_build(ROOT / mode / "build-result.json", mode)
    except BaseException as exc:
        report.update(status="fail", error=f"{type(exc).__name__}: {exc}")
        raise
    finally:
        report["derivationWallSeconds"] = round(time.monotonic() - began, 6)
        with output.open("x") as stream:
            stream.write(json.dumps(report, sort_keys=True, indent=2) + "\n")
    print(json.dumps({key: report[key] for key in ("status", "instructionSamples", "cachePayloadBytesTotal")}), flush=True)


if __name__ == "__main__":
    main()
