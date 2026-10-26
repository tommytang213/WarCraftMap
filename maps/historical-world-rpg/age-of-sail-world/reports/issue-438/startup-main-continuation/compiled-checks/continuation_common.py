"""Pinned bindings shared by developer-only PR #536 continuation checks."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
CONTINUATION = ROOT.parent
WORKSPACE = CONTINUATION.parent
REPO = WORKSPACE / "WarCraftMap"
PROJECT = REPO / "maps/historical-world-rpg/age-of-sail-world"
PREVIOUS = Path("/workspace/scratch/243ebc79fa0a")
EVIDENCE = PREVIOUS / "WarCraftMap/maps/historical-world-rpg/age-of-sail-world/reports/issue-438"
REVISION = "d6697380d979f96b2f3543593c6383402ba26e5b"
LAUNCHER = CONTINUATION / "toolchain/grill"
LAUNCHER_SHA = "24c86255934e5076b4217eacea3c94a37f46c4c133c4958bc00bb5ccac9be89e"
COMPILER = CONTINUATION / "toolchain/home/.wurst/wurst-compiler/wurstscript.jar"
DEPENDENCY = PREVIOUS / "pinned-wurst/WurstStdlib2"
DEPENDENCY_REVISION = "cce79096e71dcb066cf94785bc5cb48ef66c26db"
LIBRARY = PREVIOUS / "validation-536/lua53-runtime/liblua5.3.6-probe.so"
LIBRARY_SHA = "fdaa987d06dd329be3232a65ea71cae427f3bfd26f5b757d8853628d33d9492a"
INDEPENDENT_READER = PREVIOUS / "validation-536/mpyq-reviewed.py"
FROZEN = ROOT / "frozen"
FROZEN_FILES = {
    "probe-lua54-initialization.py": (EVIDENCE / "native-boundary-repair/common/probe-lua54-initialization.py",
        "b3bd4b946cd4ceb9b46a7c254fb1c9d498868c9deae31cf72836ff8dc1225948"),
    "late-startup-stubs.lua": (EVIDENCE / "native-boundary-repair/common/late-startup-stubs.lua",
        "3c7eda8627f7ba5d4c3d3f49328be834d7598f1e8616462f665b02ae8cdaa630"),
    "observe-startup.lua": (EVIDENCE / "startup-work-reduction/observer-parse-once/observe-startup.lua",
        "cfd547d94e6d36c8183677f471a47b53dcbf912d54dfc1888d79305880ad0fe9"),
    "observe-startup-template.py": (EVIDENCE / "native-boundary-repair/compiled/observer/observe-startup.py",
        "a461746fb1fb5f5eec6a0dfa7d06b540860495d6090f0566a41a884b9b04e2b1"),
    "full-scale-roundtrip.lua": (EVIDENCE / "trade-startup/full-scale-roundtrip.lua",
        "8151d852ac6e7d3546494038901a9b19efd342f91604e5450aee58ece9a44f10"),
    "verify-trade-full-scale-original.py": (EVIDENCE / "trade-startup/verify-trade-full-scale.py",
        "2cfe851ac54ce3ec9da874a4adf9b1addcc66debc85a439814e24f3ebed63e35"),
}
WPM_SHA = "7cf3b29475751ebe1d962e17651b0c42ace030b9fa2e4523cf935adf27aee0bd"
REVISED_TRADE_SHA = "4b7ddfc925f7e762e1f93a76994700be8af0c2b1b7f1b4b1bbd48c92b36d8e83"
SOURCE_TREE_SHA = "d08445f912a604b5fdb43beed2ec9573904075beb2e1ed6c40771df75852be37"
# The exact digest is checked again against the committed source during preparation.
CHANGED_INPUTS = {"wurst/PlayableTrade.wurst", "wurst/PlayableCampaignRuntime.wurst"}

sys.path.insert(0, str(PROJECT.parent / "_shared/tooling"))
from integration_evidence import source_identity


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def identity(path: Path) -> dict:
    return {"path": str(path.resolve()), "bytes": path.stat().st_size, "sha256": sha(path)}


def tree(path: Path) -> dict:
    return {p.relative_to(path).as_posix(): sha(p) for p in sorted(path.rglob("*"))
            if p.is_file() and ".git" not in p.relative_to(path).parts
            and "__pycache__" not in p.parts and p.suffix not in {".pyc", ".pyo"}}


def read(path: Path):
    return json.loads(path.read_text())


def write(path: Path, value):
    temporary = path.with_name(path.name + ".part")
    temporary.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n")
    os.replace(temporary, path)


def git(*args, cwd=REPO):
    return subprocess.check_output(["git", *args], cwd=cwd, text=True).strip()


def check_repository() -> dict:
    assert git("rev-parse", "HEAD") == REVISION, "This continuation is pinned to integrated d669"
    assert not git("status", "--porcelain"), "Compile the clean integrated source; preserve dirty work"
    result = source_identity(PROJECT, REVISION)
    assert result["sourceTreeSha256"] == SOURCE_TREE_SHA, "Integrated source inputs differ from the reviewed d669 tree"
    assert sha(PROJECT.parent / "_shared/wurst/PlayableTrade.wurst") == REVISED_TRADE_SHA
    return result


def no_compiler():
    found = []
    for proc in Path("/proc").iterdir():
        if not proc.name.isdigit():
            continue
        try:
            command = (proc / "cmdline").read_bytes().split(b"\0")
        except OSError:
            continue
        if command and command[0].endswith(b"java") and any(arg.endswith((b"/wurstscript.jar", b"/grill.jar")) for arg in command):
            found.append(proc.name)
    assert not found, f"Wait for active Wurst/Grill JVMs to finish: {found}"


def revert_continuation(relative: str, content: bytes) -> bytes:
    """Revert only the two requested production edits in a disposable assembly."""
    text = content.decode("utf-8")
    if relative == "wurst/PlayableCampaignRuntime.wurst":
        for slot, variable in (("session_start", "session"), ("major_milestone", "milestone")):
            before = f'if {variable} == "" or not saves.storage.writeTransactional("{slot}", {variable})'
            after = f'if not saves.storage.writeTransactional("{slot}", {variable})'
            assert text.count(before) == 1, (relative, before)
            text = text.replace(before, after)
    elif relative == "wurst/PlayableTrade.wurst":
        start = text.index("// Decimal digits are the common case in every market/store record. Avoid a\n")
        end = text.index("function tradeInteger(string value) returns boolean\n", start)
        helper = text[start:end]
        assert helper.count("function tradeDecimalDigit(string character) returns int") == 1
        assert helper.count("\nfunction ") == 1
        text = text[:start] + text[end:]
        before = "let digit=tradeDecimalDigit(SubString(value,i,i+1))"
        after = 'let digit="0123456789".indexOf(SubString(value,i,i+1))'
        assert text.count(before) == 1
        text = text.replace(before, after)
        assert "tradeDecimalDigit" not in text
    else:
        assert relative not in CHANGED_INPUTS
    return text.encode("utf-8")


def check_frozen() -> dict:
    result = {}
    for name, (original, expected) in FROZEN_FILES.items():
        copy = FROZEN / name
        assert sha(original) == sha(copy) == expected, name
        result[name] = {"original": identity(original), "copy": identity(copy)}
    assert sha(LIBRARY) == LIBRARY_SHA
    matches = re.findall(r"io\.open\('([^']+war3map\.wpm)'", (FROZEN / "late-startup-stubs.lua").read_text())
    assert len(matches) == 1
    pathing = Path(matches[0])
    assert sha(pathing) == WPM_SHA
    result["library"] = identity(LIBRARY)
    result["frozenPathing"] = identity(pathing)
    return result


def load_build(path: Path, mode: str) -> dict:
    build = read(path)
    assert build["status"] == "pass" and build["mode"] == mode
    assert build["sourceRevision"] == REVISION
    assert build["compilerInputsUnchangedDuringBuild"] and build["independentKnownMembersEqual"]
    assert build["typecheckExitCode"] == build["buildExitCode"] == 0
    assert identity(Path(build["compiledScript"]))["sha256"] == build["compiledScriptSha256"]
    assert identity(Path(build["archive"]["path"])) == build["archive"]
    seed = read(ROOT / "europe-seed/seed-receipt.json")
    assert seed["status"] == "pass" and seed["sourceRevision"] == REVISION and seed["schema"] == 17
    assert seed["sourceIdentityAtAssembly"] == {"sourceRevision": REVISION, "sourceTreeSha256": SOURCE_TREE_SHA}
    assert build["schema"] == 17
    assert build["seedReceipt"] == identity(ROOT / "europe-seed/seed-receipt.json")
    expected = dict(seed["compilerInputs"])
    if mode == "baseline":
        for relative in CHANGED_INPUTS:
            expected[relative] = hashlib.sha256(revert_continuation(relative,
                (ROOT / "europe-seed/compile" / relative).read_bytes())).hexdigest()
    assert build["compilerInputs"] == expected
    assert build["wurstInputs"] == {name: value for name, value in expected.items() if name.startswith("wurst/")}
    assert read(path.parent / "inputs-before.json") == read(path.parent / "inputs-after.json") == expected
    assert build["mapInputs"] == seed["mapInputs"]
    assert build["sourceIdentityAtAssembly"] == seed["sourceIdentityAtAssembly"]
    assert sha(path.parent / "war3map.wpm") == WPM_SHA, "Frozen pathing is not the current compiled pathing"
    return build
