"""Synthetic interpreter protocol for packaging tests; never release evidence."""
import hashlib
import os
from unittest.mock import patch

import wurst_execution as execution

FAKE_EXECUTION = r'''
if sys.argv[1] == "test":
    import os, re
    mode = os.environ.get("FAKE_WURST_RESULT", "pass")
    if mode == "absent":
        sys.exit(127)
    print("Grill synthetic-packaging-fixture")
    print("verifyInstallation: detectedCompilerJar=" + str(pathlib.Path(sys.argv[0]).resolve()) + " exists=true")
    print("Running tests")
    tests = []
    for path in sorted((root / "wurst").rglob("*.wurst")):
        text = path.read_text()
        for match in re.finditer(r"@test\s+function\s+(\w+)\s*\(", text):
            tests.append((path, text[:match.start()].count("\n") + 1, match[1]))
    if mode == "zero":
        tests = []
    for path, line, name in tests:
        print(f"Running {path}:{line} - {name}..")
        if mode == "assertion":
            print("FAILED assertion: Expected true, Actual false")
        elif mode == "exception":
            print("You encountered a bug in the interpreter: NullPointerException")
        elif mode != "incomplete":
            print("\tOK!")
    if mode != "truncated":
        print(f"Tests succeeded: {len(tests)}/{len(tests)}")
        print("Finished running tests")
    sys.exit(0)
'''


def allow_synthetic_compiler(test, fake):
    """Only unit tests replace the pinned compiler digest with their fake's hash."""
    for replacement in (
        patch.object(execution, "PINNED_COMPILER_SHA256", hashlib.sha256(fake.read_bytes()).hexdigest()),
        patch.dict(os.environ, {"SOURCE_REVISION": "a" * 40}),
    ):
        replacement.start()
        test.addCleanup(replacement.stop)


def passing_evidence(revision="a" * 40):
    expected = [{"id": "wurst/Fixture.wurst:fixture", "line": 2}]
    log = b"Running tests\nRunning /test/wurst/Fixture.wurst:2 - fixture..\n\tOK!\nTests succeeded: 1/1\nFinished running tests\n"
    rows, issues = execution.parse_results(log.decode(), expected)
    inputs = {"wurst/Fixture.wurst": execution.sha(b"synthetic fixture")}
    report = {"format": execution.FORMAT, "status": "pass", "returnCode": 0,
              "sourceRevision": revision, "expected": expected, "tests": rows,
              "errors": issues, "discovered": 1, "succeeded": 1,
              "logSha256": execution.sha(log), "inputs": inputs,
              "inputSetSha256": execution.sha(execution.canonical(inputs)),
              "compiler": {"sha256": execution.PINNED_COMPILER_SHA256}}
    return report, log
