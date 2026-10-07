#!/usr/bin/env python3
"""Run the headless oracle and, when configured, the native Warcraft runner."""

from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT.parent / "_shared" / "engine"))
import native_save_regression as regression  # noqa: E402


def emit(value: dict, output: Path | None) -> None:
    text = regression.canonical(value) + "\n"
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text, encoding="utf-8")
    print(text, end="")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=PROJECT / "scenario/benchmarks/native-save.json")
    parser.add_argument("--map", type=Path, help="packaged fixture .w3x supplied by CI")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--require-runtime", action="store_true")
    args = parser.parse_args(argv)
    config = json.loads(args.config.read_text(encoding="utf-8"))
    oracle = regression.run_headless_cycle(config["loads"], "fleet:sample_fleet")
    decisions = {str(item): regression.save_decision(item) for item in config["safeTransactions"] + config["unsafeTransactions"]}
    if not oracle["passed"]:
        emit({"status": "failure", "kind": "headless_oracle_failure", "oracle": oracle}, args.output)
        return 1

    variable = config["runner"]["environmentVariable"]
    command_text = os.environ.get(variable, "").strip()
    if not command_text:
        result = {"status": "skip", "kind": "runtime_unavailable", "environmentVariable": variable,
                  "message": f"native Warcraft runner unavailable; set {variable}", "oracle": oracle,
                  "saveDecisions": decisions}
        emit(result, args.output)
        return 1 if args.require_runtime else 0
    if not args.map or not args.map.is_file():
        emit({"status": "failure", "kind": "fixture_map_missing", "message": "--map must name the packaged native-save fixture"}, args.output)
        return 1

    with tempfile.TemporaryDirectory(prefix="wc3-native-save-") as directory:
        root = Path(directory)
        request = root / "request.json"
        response = root / "result.json"
        request.write_text(regression.canonical({
            "protocol": config["runner"]["protocol"], "fixtureId": config["id"],
            "map": str(args.map.resolve()), "saveName": config["saveName"], "loads": config["loads"],
            "expected": oracle, "transactions": decisions,
        }) + "\n", encoding="utf-8")
        command = [*shlex.split(command_text), "--request", str(request), "--result", str(response)]
        try:
            completed = subprocess.run(command, capture_output=True, text=True, timeout=config["runner"]["timeoutSeconds"], check=False)
        except (OSError, subprocess.TimeoutExpired) as error:
            emit({"status": "failure", "kind": "runner_launch_failure", "message": str(error)}, args.output)
            return 1
        if completed.returncode or not response.is_file():
            emit({"status": "failure", "kind": "runner_failure", "returnCode": completed.returncode,
                  "stdout": completed.stdout[-2000:], "stderr": completed.stderr[-2000:]}, args.output)
            return 1
        try:
            native = json.loads(response.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            emit({"status": "failure", "kind": "invalid_runner_result", "message": str(error)}, args.output)
            return 1
        required = {"authoritativeDigestBefore", "authoritativeDigestAfter", "runtimeIndex", "transientHandlesRecreated", "eventDeliveryCount", "loads"}
        missing = sorted(required - native.keys())
        failures = []
        if missing:
            failures.append("missing result fields: " + ", ".join(missing))
        else:
            if native["authoritativeDigestBefore"] != oracle["authoritativeDigestBefore"] or native["authoritativeDigestAfter"] != oracle["authoritativeDigestAfter"]:
                failures.append("native authoritative state differs from deterministic fixture")
            if native["runtimeIndex"] != oracle["runtimeIndex"]:
                failures.append("native reconstructed runtime index differs from oracle")
            if not native["transientHandlesRecreated"]:
                failures.append("native transient handles were retained as authority")
            if native["eventDeliveryCount"] != 1:
                failures.append("post-load event was delivered more or less than once")
            if native["loads"] != config["loads"]:
                failures.append("runner did not complete every requested native load")
        result = {"status": "failure" if failures else "passed", "kind": "native_runtime_regression",
                  "failures": failures, "oracle": oracle, "native": native, "saveDecisions": decisions}
        emit(result, args.output)
        return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
