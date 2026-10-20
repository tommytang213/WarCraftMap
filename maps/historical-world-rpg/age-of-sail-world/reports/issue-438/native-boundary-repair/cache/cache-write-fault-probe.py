#!/usr/bin/env python3
"""Bounded exact-compiled-code cache fault probe; no Warcraft client is run."""
from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
from pathlib import Path
import time


def identity(path: Path) -> dict:
    data = path.read_bytes()
    return {"path": str(path.resolve()), "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest()}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lua-path", type=Path, required=True)
    parser.add_argument("--expected-sha256", required=True)
    parser.add_argument("--library", type=Path, required=True)
    parser.add_argument("--expect", choices=("legacy-false-success", "rejected-write"), required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    if args.report.exists():
        raise RuntimeError("Preserve the existing result; choose a new report path")
    report = {
        "format": "compiled_game_cache_false_success_probe_v1", "status": "failed",
        "nativeStatus": "not_run", "expectedBehavior": args.expect,
        "instructionBudget": 100000, "productionFunctionOverrides": False,
        "limitations": [
            "Stock Lua with explicit success/failure native stubs; not native Warcraft execution.",
            "Only compiled storage code and global bootstrap execute; config/main/campaign startup are not called.",
            "This establishes a cache transaction result defect, not the cause of the observed unresponsive window.",
            "Cache readback observes the in-memory API; it does not establish disk durability or reopen behavior.",
        ],
    }
    state = None
    began = time.monotonic()
    try:
        case = Path(__file__).with_suffix(".lua")
        report["inputs"] = {"compiledLua": identity(args.lua_path), "case": identity(case),
                            "runner": identity(Path(__file__)), "runtimeLibrary": identity(args.library)}
        if report["inputs"]["compiledLua"]["sha256"] != args.expected_sha256:
            raise RuntimeError("Actual compiled Lua does not match the explicit expected digest")
        lib = ctypes.CDLL(str(args.library.resolve()))
        lib.luaL_newstate.restype = ctypes.c_void_p
        lib.luaL_openlibs.argtypes = [ctypes.c_void_p]
        lib.luaL_loadfilex.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_char_p]
        lib.luaL_loadfilex.restype = ctypes.c_int
        lib.lua_pcallk.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                                  ctypes.c_longlong, ctypes.c_void_p]
        lib.lua_pcallk.restype = ctypes.c_int
        lib.lua_tolstring.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.POINTER(ctypes.c_size_t)]
        lib.lua_tolstring.restype = ctypes.c_void_p
        lib.lua_getglobal.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
        lib.lua_settop.argtypes = [ctypes.c_void_p, ctypes.c_int]
        lib.lua_close.argtypes = [ctypes.c_void_p]
        state = lib.luaL_newstate()
        if not state:
            raise RuntimeError("Cannot create stock Lua state")
        lib.luaL_openlibs(state)

        def read_top() -> str:
            size = ctypes.c_size_t()
            address = lib.lua_tolstring(state, -1, ctypes.byref(size))
            if not address:
                raise RuntimeError("Expected Lua string")
            return ctypes.string_at(address, size.value).decode()

        def execute(path: Path) -> None:
            status = lib.luaL_loadfilex(state, str(path.resolve()).encode(), b"t")
            if not status:
                status = lib.lua_pcallk(state, 0, 0, 0, 0, None)
            if status:
                raise RuntimeError(read_top())

        lib.lua_getglobal(state, b"_VERSION")
        report["runtimeVersion"] = read_top()
        lib.lua_settop(state, 0)
        if report["runtimeVersion"] != "Lua 5.3":
            raise RuntimeError("This retained control requires stock Lua 5.3")
        execute(args.lua_path)
        execute(case)
        lib.lua_getglobal(state, b"__cache_probe_result")
        result = json.loads(read_top())
        report["execution"] = result
        assert result["productionFunctionsUnchanged"] is True
        assert result["mainCalled"] is False and result["configCalled"] is False
        assert result["nativeStatus"] == "not_run" and result["stored"] is False
        assert result["nativeCalls"]["StoreString"] == 1
        assert result["sampledInstructions"] <= report["instructionBudget"]
        if args.expect == "legacy-false-success":
            assert result["returned"] is True and result["diagnostic"] == ""
            assert result["nativeCalls"]["SaveGameCache"] == 1
            report["status"] = "reproduced_legacy_false_success_under_explicit_stubs"
        else:
            assert result["returned"] is False and result["diagnostic"]
            report["status"] = "pass_rejected_write_under_explicit_stubs"
        for name, path in (("compiledLua", args.lua_path), ("case", case),
                           ("runner", Path(__file__)), ("runtimeLibrary", args.library)):
            assert identity(path) == report["inputs"][name], "Input changed during probe: " + name
    except Exception as exc:
        report["status"] = "failed"
        report["error"] = str(exc) or type(exc).__name__
    finally:
        if state:
            lib.lua_close(state)
        report["wallSeconds"] = round(time.monotonic() - began, 6)
        args.report.parent.mkdir(parents=True, exist_ok=True)
        with args.report.open("x") as output:
            json.dump(report, output, indent=2, sort_keys=True)
            output.write("\n")
    print(json.dumps({key: report[key] for key in ("status", "nativeStatus", "wallSeconds")}))
    if report["status"] == "failed":
        print(report["error"])
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
