#!/usr/bin/env python3
"""Compare actual archived tradeInteger functions without executing config/main."""
import argparse
import ctypes
import importlib.util
import os
from pathlib import Path
import re
import time

from continuation_common import *

BUDGET = 500_000_000  # The retained isolated compiled-helper parity safety budget.


def literal(value):
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        value = value.encode("utf-8")
    if isinstance(value, bytes):
        return '"' + "".join("\\x" + format(byte, "02x") for byte in value) + '"'
    if isinstance(value, list):
        return "{" + ",".join(literal(item) for item in value) + "}"
    if isinstance(value, dict):
        return "{" + ",".join("[" + literal(key) + "]=" + literal(item) for key, item in value.items()) + "}"
    return str(value)


def canonical_integer(value: bytes) -> bool:
    if not re.fullmatch(rb"(?:0|[1-9][0-9]*|-[1-9][0-9]*)", value):
        return False
    number = int(value)
    return -2_147_483_648 <= number <= 2_147_483_647


def cases():
    rows = []
    def add(group, value):
        value = value.encode("utf-8") if isinstance(value, str) else value
        rows.append({"id": f"{group}-{len(rows) + 1}", "value": value})
    values = ["", "-", "+", "-0", "00", "01", "-01", "+0", "+1", " 1", "1 ", "--1", "1-",
              "2147483646", "2147483647", "2147483648", "2147483649", "-2147483647", "-2147483648",
              "-2147483649", "9999999999", "-9999999999", "10000000000", "-10000000000",
              "1234567890", "-1234567890", "0123456789", "1.0", "1e2", "0x1", "1_000"]
    values += [str(value) for value in range(10)] + ["-" + str(value) for value in range(1, 10)]
    for power in range(1, 10):
        for delta in (-1, 0, 1):
            values += [str(10 ** power + delta), str(-(10 ** power + delta))]
    for value in values:
        add("canonical-boundary", value)
    for byte in range(128):
        for prefix, suffix in ((b"", b""), (b"1", b""), (b"-1", b""), (b"", b"1")):
            add("ascii", prefix + bytes([byte]) + suffix)
    for value in ("１", "١", "𝟙", "½", "²", "०", "௧", "四", "雪", "😀", "é", "−", "＋", "\u00a0", "\u200b", "�"):
        for encoded in (value, "1" + value, value + "1", "-" + value):
            add("unicode", encoded)
    for value in (b"\xff", b"\xc3", b"\xf0\x9f", b"\xc0\xaf", b"\xed\xa0\x80"):
        for prefix in (b"", b"1", b"-1"):
            add("invalid-utf8", prefix + value)
    for value in ("X", "-X", "1X", "X1", "0X", "-0X", "214748364X", "-214748364X"):
        add("injected-slice", value)
    return rows


# Raw byte slicing and the replacement-marker model are copied from the retained
# isolated compiled-helper parity probe. The additional narrow models substitute
# only a returned literal X slice, leaving alphabet lookup slices untouched. They
# test preserved fallback semantics, not any claim about native Unicode behavior.
SLICE_MODELS = {
    "raw_byte_slices": "",
    "invalid_slice_to_replacement_marker": '''
local rawSlice=SubString
SubString=function(value,first,last)
 local result=rawSlice(value,first,last)
 if utf8.len(result)==nil then return "�" end
 return result
end
''',
}
for name, replacement in (("empty", b""), ("multi_12", b"12"), ("multi_89", b"89"), ("multi_90", b"90"),
                          ("whole_alphabet", b"0123456789"), ("invalid_unicode", "１".encode())):
    SLICE_MODELS["literal_X_to_" + name] = '''
local rawSlice=SubString
SubString=function(value,first,last)
 local result=rawSlice(value,first,last)
 if result=="X" then return ''' + literal(replacement) + ''' end
 return result
end
'''


def run(module, script, model, vectors):
    lib = module.lib
    pointer = ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int,
                              ctypes.POINTER(ctypes.c_size_t))(("lua_tolstring", lib))
    state = lib.luaL_newstate()
    assert state
    lib.luaL_openlibs(state)
    def get(name):
        lib.lua_getglobal(state, name.encode())
        length = ctypes.c_size_t()
        address = pointer(state, -1, ctypes.byref(length))
        assert address, name
        value = ctypes.string_at(address, length.value)
        lib.lua_settop(state, 0)
        return value
    try:
        assert get("_VERSION") == b"Lua 5.3"
        status = lib.luaL_loadfilex(state, str(script).encode(), b"t")
        if not status:
            status = lib.lua_pcallk(state, 0, 0, 0, 0, None)
        if status:
            raise RuntimeError(lib.lua_tolstring(state, -1, None).decode(errors="replace"))
        names = re.findall(r"^function ([A-Za-z_][A-Za-z0-9_]*)\(", script.read_text(), re.M)
        assert "tradeInteger" in names, "Actual compiled tradeInteger was eliminated or renamed; review instead of reconstructing it"
        module.execute(state, "__integer_original_functions={}\nfor _,name in ipairs(" + literal(names) + ") do "
                       'assert(type(_G[name])=="function",name);__integer_original_functions[name]=_G[name] end')
        module.execute(state, module.PRELUDE)
        module.execute(state, SLICE_MODELS[model])
        module.execute(state, "__wurst_init_bootstrap()")
        unchanged = ('for name,original in pairs(__integer_original_functions) do '
                     'assert(_G[name]==original,"Compiled function replaced: "..name) end')
        module.execute(state, unchanged)
        module.execute(state, "__integer_cases=" + literal(vectors) + "\n__integer_budget=" + str(BUDGET))
        module.execute(state, '''
local instructions=0
debug.sethook(function()
 instructions=instructions+10000
 if instructions>__integer_budget then debug.sethook();error("PARITY_SAFETY_BUDGET",0) end
end,"",10000)
local results={}
local callStart=__probe.nativeCalls.SubString or 0
for _,case in ipairs(__integer_cases) do
 local value=tradeInteger(case.value,"actual archived tradeInteger differential")
 assert(type(value)=="boolean",case.id)
 results[#results+1]={id=case.id,accepted=value}
end
debug.sethook()
__integer_result=__probe.json({results=results,instructions=instructions,
 substringCalls=(__probe.nativeCalls.SubString or 0)-callStart,nativeCalls=__probe.nativeCalls})
''')
        module.execute(state, unchanged)
        result = json.loads(get("__integer_result"))
        result["compiledFunctionsCheckedUnchanged"] = len(names)
        assert result["instructions"] <= BUDGET
        return result
    finally:
        lib.lua_close(state)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "trade-integer-differential")
    args = parser.parse_args()
    no_compiler()
    assert not args.output.exists(), "Preserve prior evidence"
    frozen_inputs = check_frozen()
    builds = {mode: load_build(ROOT / mode / "build-result.json", mode) for mode in ("baseline", "revised")}
    args.output.mkdir(parents=True)
    vectors = cases()
    write(args.output / "cases.json", [{"id": row["id"], "valueHex": row["value"].hex(),
          "canonicalAsciiExpected": canonical_integer(row["value"])} for row in vectors])
    write(args.output / "native-slice-models.json", SLICE_MODELS)
    report = {"format": "pr536_actual_compiled_trade_integer_differential_v1", "status": "running",
        "sourceRevision": REVISION, "nativeStatus": "not_run", "productionFunctionOverrides": False,
        "configOrMainExecuted": False, "instructionBudgetPerState": BUDGET,
        "inputs": {"runner": identity(Path(__file__)), "cases": identity(args.output / "cases.json"),
                   "sliceModels": identity(args.output / "native-slice-models.json"), "frozen": frozen_inputs,
                   "baselineBuild": identity(ROOT / "baseline/build-result.json"), "revisedBuild": identity(ROOT / "revised/build-result.json")},
        "limitations": [
            "Whole actual archived Lua scripts are loaded; their compiled tradeInteger functions are called without config/main.",
            "The retained frozen PRELUDE is unchanged. Additional isolated SubString models are explicit differential inputs, not modifications to startup stubs.",
            "Empty and multi-character X slices exercise legacy indexOf fallback behavior; they do not assert how Warcraft slices Unicode.",
            "The 500M sampled helper budget is the retained local safety bound, not a Warcraft limit.",
            "This differential is not native Warcraft execution or evidence of controllable-unit movement."], "models": []}
    began = time.monotonic()
    try:
        os.environ["WC3_LUA_PROBE_LIBRARY"] = str(LIBRARY)
        spec = importlib.util.spec_from_file_location("frozen_integer_probe", FROZEN / "probe-lua54-initialization.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        for model in SLICE_MODELS:
            pair = {}
            for mode in ("baseline", "revised"):
                print(f"tradeInteger: {model}, {mode}", flush=True)
                result = run(module, Path(builds[mode]["compiledScript"]), model, vectors)
                write(args.output / f"{model}-{mode}.json", result)
                pair[mode] = result
            assert pair["baseline"]["results"] == pair["revised"]["results"], model
            expected_ids = [row["id"] for row in vectors]
            actual = pair["revised"]["results"]
            assert [row["id"] for row in actual] == expected_ids
            ordinary = model in {"raw_byte_slices", "invalid_slice_to_replacement_marker"}
            if ordinary:
                assert [row["accepted"] for row in actual] == [canonical_integer(row["value"]) for row in vectors], model
            if model.startswith("literal_X_to_"):
                x_result = next(row["accepted"] for row, vector in zip(actual, vectors)
                                if vector["id"].startswith("injected-slice-") and vector["value"] == b"X")
                assert x_result == (model in {"literal_X_to_empty", "literal_X_to_multi_12", "literal_X_to_multi_89", "literal_X_to_whole_alphabet"})
            report["models"].append({"sliceModel": model, "cases": len(vectors), "exactBooleanResultsEqual": True,
                "canonicalAsciiOracleChecked": ordinary, "status": "pass",
                "outputsSha256": hashlib.sha256(json.dumps(actual, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
                "substringCalls": {mode: result["substringCalls"] for mode, result in pair.items()},
                "instructions": {mode: result["instructions"] for mode, result in pair.items()},
                "results": {mode: identity(args.output / f"{model}-{mode}.json") for mode in pair}})
        raw = report["models"][0]
        assert raw["substringCalls"]["revised"] < raw["substringCalls"]["baseline"]
        check_frozen()
        for mode in ("baseline", "revised"):
            load_build(ROOT / mode / "build-result.json", mode)
        report["status"] = "pass_under_explicit_models"
    except BaseException as exc:
        report.update(status="fail", error=f"{type(exc).__name__}: {exc}")
        raise
    finally:
        report["wallSeconds"] = round(time.monotonic() - began, 6)
        write(args.output / "receipt.json", report)
    print(json.dumps({"status": report["status"], "models": len(report["models"]), "casesPerModel": len(vectors)}), flush=True)


if __name__ == "__main__":
    main()
