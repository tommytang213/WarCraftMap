"""Execute the hash-bound failing selector at a recording Lua native boundary.

Uses an already-installed Lua 5.4 shared library. Installs/downloads nothing and
does not execute Warcraft, Blizzard.j/lua, native models, archives or game cache.
"""
from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from isolation_lua import isolation_script
BASELINE_SHA256 = "efaffe67682ca0c3c952722ce0a5f42be1ba954a27c5ad49177f48b6c536ebe3"


class Lua:
    def __init__(self, library: Path):
        self.api = api = ctypes.CDLL(str(library.resolve()))
        api.luaL_newstate.restype = ctypes.c_void_p
        api.luaL_openlibs.argtypes = [ctypes.c_void_p]
        api.luaL_loadbufferx.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_size_t,
                                       ctypes.c_char_p, ctypes.c_char_p]
        api.lua_pcallk.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                                  ctypes.c_ssize_t, ctypes.c_void_p]
        api.lua_tolstring.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.POINTER(ctypes.c_size_t)]
        api.lua_tolstring.restype = ctypes.c_char_p
        api.lua_getglobal.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
        api.lua_close.argtypes = [ctypes.c_void_p]

    def run(self, source: bytes, mode: str) -> dict:
        api = self.api
        state = api.luaL_newstate()
        if not state:
            raise RuntimeError("Lua state allocation failed")
        api.luaL_openlibs(state)
        error = None
        try:
            chunks = [("mode", f"MODE={json.dumps(mode)}".encode()),
                      ("boundary", (HERE / "boundary.lua").read_bytes()),
                      ("selector", source), ("exercise", (HERE / "exercise.lua").read_bytes())]
            for label, chunk in chunks:
                status = api.luaL_loadbufferx(state, chunk, len(chunk), label.encode(), b"t")
                if not status:
                    status = api.lua_pcallk(state, 0, 0, 0, 0, None)
                if status:
                    error = f"{label}: {api.lua_tolstring(state, -1, None).decode()}"
                    break
            api.lua_getglobal(state, b"TRACE_TEXT")
            output = api.lua_tolstring(state, -1, None)
            api.lua_getglobal(state, b"_VERSION")
            version = api.lua_tolstring(state, -1, None).decode()
            if version != "Lua 5.4":
                raise ValueError(f"This host wrapper requires Lua 5.4; found {version}")
            return {"mode": mode, "luaVersion": version,
                    "luaSha256": hashlib.sha256(source).hexdigest(), "error": error,
                    "trace": output.decode().splitlines() if output else []}
        finally:
            api.lua_close(state)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lua", type=Path, required=True, help="exact extracted smoke #3 war3map.lua")
    parser.add_argument("--library", type=Path, required=True, help="already installed Lua 5.4 shared library")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    source = args.lua.read_bytes()
    if hashlib.sha256(source).hexdigest() != BASELINE_SHA256:
        parser.error("input is not the exact failing smoke #3 Lua member")
    host = Lua(args.library)
    results = [host.run(source, mode) for mode in
               ("normal", "cache_unavailable", "timer_unavailable", "deliberate_nil_argument")]
    # Controlled compiled-script mutation: retain the original Bootstrap body,
    # but break its initialization call. The gate must detect the resulting error
    # and absent origin page rather than infer success from an earlier message.
    needle = b"xpcall(init_Bootstrap,"
    if source.count(needle) != 1:
        raise ValueError("expected one Bootstrap initialization call")
    mutated = source.replace(needle, b"xpcall(init_Bootstrap_Missing,", 1)
    results.append(host.run(mutated, "missing_bootstrap"))
    isolated = isolation_script(source)
    results.append(host.run(isolated, "isolation"))
    without_timer_marker = isolated.replace(b'"438: timer reached"', b'"negative control"')
    results.append(host.run(without_timer_marker, "isolation"))
    rejected = False
    try:
        isolation_script(source + b"\n")
    except ValueError:
        rejected = True
    checks = {
        "baseline_reaches_origin_page": results[0]["error"] is None,
        "missing_cache_does_not_prevent_origin_page": results[1]["error"] is None,
        "missing_timer_is_rejected": "expected bootstrap and origin messages, got 1" in (results[2]["error"] or ""),
        "nil_native_argument_is_rejected": "expected live player, got nil" in (results[3]["error"] or ""),
        "missing_bootstrap_is_rejected": "recorded Lua errors" in (results[4]["error"] or ""),
        "isolation_reaches_both_markers_without_packages": results[5]["error"] is None,
        "missing_isolation_marker_is_rejected": "timer marker missing" in (results[6]["error"] or ""),
        "isolation_rejects_wrong_baseline_hash": rejected,
    }
    report = {"format": "issue438_lua_boundary_experiment_v1", "nativeExecution": "not_run",
              "clientLuaVersion": "not_established", "librarySha256": hashlib.sha256(args.library.read_bytes()).hexdigest(),
              "harnessSha256": {name: hashlib.sha256((HERE / name).read_bytes()).hexdigest()
                                for name in ("trace.py", "boundary.lua", "exercise.lua")},
              "isolationTransformerSha256": hashlib.sha256((HERE.parent / "isolation_lua.py").read_bytes()).hexdigest(),
              "inputSha256": BASELINE_SHA256, "checks": checks, "results": results}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(checks, indent=2))
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
