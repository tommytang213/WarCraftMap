#!/usr/bin/env python3
"""Read-only audit of one preserved negative-control attempt; never executes tests."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import re
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent / "WarCraftMap"
PROJECT = REPO / "maps/historical-world-rpg/age-of-sail-world"
TOOLING = PROJECT.parent / "_shared/tooling"
sys.path.insert(0, str(TOOLING))
from integration_evidence import execution_sources, source_identity
from wurst_execution import canonical, discover, input_hashes, parse_results, select_tests

REVISION = "d6697380d979f96b2f3543593c6383402ba26e5b"
SOURCE_SHA = "d08445f912a604b5fdb43beed2ec9573904075beb2e1ed6c40771df75852be37"
OUT = ROOT / "evidence-review/negative-control-review.json"
ATTEMPT = ROOT / "negative-guard-attempt1"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def require(value, message):
    if not value:
        raise ValueError(message)


def main():
    require(not OUT.exists(), "Preserve the prior review; use a new review path")
    protected = sorted(p for p in ATTEMPT.iterdir() if p.is_file())
    protected += [ROOT / "negative-guard-attempt1.log", ROOT / "run-wurst.py"]
    original_hashes = {p.relative_to(ROOT).as_posix(): sha(p) for p in protected}
    receipt = read(ATTEMPT / "receipt.json")
    result = read(ATTEMPT / "results.json")
    discovery = read(ATTEMPT / "discovery.json")
    before = read(ATTEMPT / "compiler-inputs-before.json")
    after = read(ATTEMPT / "compiler-inputs-after.json")
    seed = ROOT / "seed/compile"
    seed_receipt = read(ROOT / "seed/receipt.json")
    assembly = ATTEMPT / "compile"
    expected = [
        {"id": "wurst/CampaignStartupTests.wurst:emptySessionEncodingPreservesPendingStartupAndCanRetry", "line": 468},
        {"id": "wurst/CampaignStartupTests.wurst:emptyMilestoneEncodingPreservesPendingStartupAndCanRetry", "line": 471},
    ]
    require(discovery == expected == result["expected"] == discover(assembly), "Wrong selected tests")
    require(before == after == input_hashes(assembly) == result["inputs"], "Compiler inputs changed")
    require(result["inputSetSha256"] == hashlib.sha256(canonical(before)).hexdigest(), "Bad input-set hash")
    authored = {n: sha(p) for n, p in sorted(execution_sources(PROJECT).items())}
    require(authored == seed_receipt["authoredInputs"], "Current authored source differs from the seed")
    identity = {"sourceRevision": REVISION, "sourceTreeSha256": SOURCE_SHA}
    require(source_identity(PROJECT, REVISION) == identity == receipt["sourceIdentity"], "Bad source identity")
    # Reconstruct every legal difference from the original assembly in memory.
    # select_tests removes only nonselected @test annotations without moving lines.
    expected_inputs = {}
    for name, source_sha in input_hashes(seed).items():
        data = (seed / name).read_bytes()
        if name.endswith(".wurst"):
            text = data.decode()
            if name == "wurst/PlayableCampaignRuntime.wurst":
                for slot, variable in [("session_start", "session"), ("major_milestone", "milestone")]:
                    old = f'if {variable} == "" or not saves.storage.writeTransactional("{slot}", {variable})'
                    require(text.count(old) == 1, "Guard absent or ambiguous")
                    text = text.replace(old, f'if not saves.storage.writeTransactional("{slot}", {variable})')
            names = {t["id"].rsplit(":", 1)[1] for t in expected if t["id"].rsplit(":", 1)[0] == name}
            data = select_tests(text, names).encode()
        expected_inputs[name] = hashlib.sha256(data).hexdigest()
    require(expected_inputs == before, "Assembly has a change beyond the two guards and test selection")
    dependency = read(ATTEMPT / "dependency-before.json")
    dep_root = assembly / "_build/dependencies/WurstStdlib2"
    dep_files = {p.relative_to(dep_root).as_posix(): sha(p) for p in sorted(dep_root.rglob("*"))
                 if p.is_file() and ".git" not in p.relative_to(dep_root).parts}
    require(dependency == seed_receipt["dependency"], "Dependency differs from original seed")
    require(dependency["files"] == dep_files and dependency["dirty"] is False, "Dependency files changed")
    require(dependency["revision"] == "cce79096e71dcb066cf94785bc5cb48ef66c26db", "Unexpected dependency pin")
    log = (ATTEMPT / "execution.log").read_text()
    compiler = ROOT / "toolchain/home/.wurst/wurst-compiler/wurstscript.jar"
    prefix = (
        "Picked up JAVA_TOOL_OPTIONS: -Xmx8g -Xmx6g\n"
        "🔥 Grill 1.4.0.0-2c676dd\n"
        f"verifyInstallation: detectedCompilerJar={compiler} exists=true\n"
        f"Found installation at {compiler}\n"
        "⚗️ Running tests...\n"
        "Existing _build core JASS files have no Grill provenance; leaving them project-owned. Delete _build/common.j and _build/blizzard.j to let Grill regenerate them for v3.0.\n"
        "Picked up JAVA_TOOL_OPTIONS: -Xmx8g -Xmx6g\n"
        "Running tests\n"
    )
    bodies = "".join(
        f'Running {assembly / row["id"].rsplit(":", 1)[0]}:{row["line"]} - {row["id"].rsplit(":", 1)[1]}..\n'
        "\tFAILED assertion:\n\tTest failed: Expected <false>, Actual <true>\n\n"
        for row in expected
    )
    suffix = (
        "Tests succeeded: 0/2\n"
        ">> 2 Tests have failed!\n"
        "Finished running tests\n"
        "de.peeeq.wurstio.languageserver.requests.RequestFailedException: Could not compile project (error in running compiletime functions/expressions): \n"
        "Error in File CampaignStartupTests.wurst:468:\n"
        " Test failed: Expected <false>, Actual <true>\n"
        "Error: Could not compile project (error in running compiletime functions/expressions): \n"
        "Error in File CampaignStartupTests.wurst:468:\n"
        " Test failed: Expected <false>, Actual <true>\n"
        "❌ Wurst test failed.\n"
        "Exit code: 2\n"
        "Try: rerun with `--quiet` for a shorter error log, or `--debug` for troubleshooting details.\n"
    )
    require(log == prefix + bodies + suffix, "Transcript contains unexpected output")
    rows, issues = parse_results(log, expected)
    allowed_issues = ["non-passing or incomplete individual results", "summary does not match complete passing discovery",
                      "assertion, compiler or interpreter error in transcript"]
    require(rows == [{**row, "status": "assertion_failed"} for row in expected] == result["tests"], "Unexpected terminal results")
    require(issues == allowed_issues and result["errors"] == allowed_issues + ["grill test exited 1"], "Unexpected gate diagnostic")
    require(result["status"] == "fail" and result["executionStatus"] == "completed"
            and result["discovered"] == 2 and result["succeeded"] == 0 and result["returnCode"] == 1, "Wrong negative outcome")
    require(result["sourceRevision"] == REVISION and result["logSha256"] == sha(ATTEMPT / "execution.log"), "Transcript/source binding failed")
    require(result["compiler"]["sha256"] == sha(compiler) == receipt["compilerSha256"], "Compiler identity mismatch")
    require(receipt["status"] == "fail" and receipt["error"] == "AssertionError: ", "Original harness result changed")
    runner = (ROOT / "run-wurst.py").read_text()
    condition = "assert 'Exception' not in log and 'No builtin function' not in log and 'Error in File' not in log"
    require(runner.count(condition) == 1, "Original runner condition missing")
    outer = (ROOT / "negative-guard-attempt1.log").read_text()
    require(outer.count(log) == 1 and condition in outer and outer.rstrip().endswith("AssertionError"), "Unexpected outer harness error")
    require({p.relative_to(ROOT).as_posix(): sha(p) for p in protected} == original_hashes, "Original evidence changed during review")
    require(authored == {n: sha(p) for n, p in sorted(execution_sources(PROJECT).items())}
            and source_identity(PROJECT, REVISION) == identity, "Current authored source changed during review")
    review = {
        "format": "warcraftmap_pr536_negative_control_review_v1",
        "reviewedAt": datetime.now(timezone.utc).isoformat(),
        "status": "intended_assertions_confirmed_original_harness_fail_preserved",
        "scope": "Static read-only review of retained execution; no tests, compilers or models rerun",
        "sourceIdentity": identity,
        "originalAttemptStatus": "fail",
        "originalResultStatus": "fail",
        "expectedTests": expected,
        "terminalResults": rows,
        "completed": True,
        "succeeded": 0,
        "discovered": 2,
        "assertion": "Expected <false>, Actual <true>",
        "rawTranscriptMatchesExactExpectedOutput": True,
        "wrapper": {
            "exception": "de.peeeq.wurstio.languageserver.requests.RequestFailedException",
            "diagnosticLocation": "CampaignStartupTests.wurst:468",
            "reason": "Normal failed-test wrapper repeats the first intended boolean assertion; no distinct compile/typecheck/native failure is present",
            "compilerReportedExitCode": 2,
            "grillProcessReturnCode": 1,
        },
        "harnessFailure": {
            "error": "AssertionError",
            "cause": "Temporary runner rejected any Exception or Error in File after correctly observing two assertion_failed terminal records",
            "originalCondition": condition,
        },
        "counterfactual": "Only the two new empty-public-checkpoint encoding guards removed; all other changes are annotation-only selection of these two tests",
        "compilerInputsBeforeAfterAndResultEqual": True,
        "counterfactualSourceReconstructedExactly": True,
        "dependencyFilesUnchangedAtReview": True,
        "authoredInputsMatchCurrentIntegratedSource": True,
        "sourceInputsUnchangedDuringReview": True,
        "originalEvidenceUnchanged": True,
        "nativeStatus": "not_run",
        "nativeContinueVerifiedFixed": False,
        "limits": [
            "This confirms the two tests detect the removed guards; it is not a passing production gate",
            "The original temporary negative-control harness remains failed and is not relabeled",
            "No native Warcraft campaign launch, terrain rendering or unit control was observed",
        ],
        "evidenceSha256": original_hashes,
        "reviewScriptSha256": sha(Path(__file__)),
        "verifierSha256": {p.name: sha(p) for p in [TOOLING / "wurst_execution.py", TOOLING / "integration_evidence.py"]},
    }
    OUT.write_text(json.dumps(review, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": review["status"], "review": str(OUT), "sha256": sha(OUT)}, indent=2))


if __name__ == "__main__":
    main()
