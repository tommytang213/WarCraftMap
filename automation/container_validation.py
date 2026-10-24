#!/usr/bin/env python3
"""Keep a private validation container until its evidence is safely published."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
import threading

REPOSITORY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY / "maps/historical-world-rpg/_shared/tooling"))
from execution_transport import invalidate, read_bundle, unpack
from wurst_execution import PINNED_IMAGE

EXPORT_TIMEOUT_SECONDS = 60


def export(container: str, project: Path, revision: str) -> None:
    build = project / "_build"
    build.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".execution-export-", dir=build) as temporary:
        stage = Path(temporary) / "bundle"
        stage.mkdir()
        with tempfile.TemporaryFile() as errors:
            process = subprocess.Popen(["docker", "cp", f"{container}:/tmp/wurst-evidence/.", "-"],
                                       stdout=subprocess.PIPE, stderr=errors)
            timer = threading.Timer(EXPORT_TIMEOUT_SECONDS, process.kill)
            timer.start()
            try:
                with process.stdout:
                    unpack(process.stdout, stage)
                if process.wait(timeout=EXPORT_TIMEOUT_SECONDS):
                    raise ValueError("Docker evidence copy failed")
            finally:
                timer.cancel()
                if process.poll() is None:
                    process.kill()
                process.wait()
        read_bundle(stage, project, revision)
        destination = build / "wurst-tests"
        if destination.exists():
            shutil.rmtree(destination)
        os.replace(stage, destination)


def validate(repository: Path, revision: str) -> int:
    project = repository / "maps/historical-world-rpg/age-of-sail-world"
    invalidate(project)
    container = None
    status = 1
    try:
        (repository / "_build").mkdir(exist_ok=True)
        # The cidfile also permits cleanup if create is interrupted after Docker
        # allocates a container but before its stdout reaches the caller.
        with tempfile.TemporaryDirectory(prefix="wurst-container-", dir=repository / "_build") as temporary:
            cidfile = Path(temporary) / "cid"
            try:
                result = subprocess.run([
                    "docker", "create", "--cidfile", str(cidfile), "--user", "root",
                    "--entrypoint", "/bin/sh", "-e", f"SOURCE_REVISION={revision}",
                    "-e", f"WURST_IMAGE={PINNED_IMAGE}", "-v", f"{repository}:/source:ro",
                    PINNED_IMAGE, "-lc", (repository / "automation/wurst_container.sh").read_text()],
                    check=True, capture_output=True, text=True)
                container = result.stdout.strip()
                status = subprocess.run(["docker", "start", "--attach", container]).returncode
                if status == 0:
                    # Unlike docker run, start --attach can return zero after a
                    # failed process on some clients. Inspect the actual exit.
                    state = subprocess.run(["docker", "inspect", "--format", "{{.State.ExitCode}}", container],
                                           check=True, capture_output=True, text=True)
                    status = int(state.stdout.strip())
                if status == 0:
                    export(container, project, revision)
            finally:
                if container is None and cidfile.is_file():
                    container = cidfile.read_text().strip()
                if container:
                    cleanup = subprocess.run(["docker", "rm", "--force", container]).returncode
                    if cleanup and status == 0:
                        invalidate(project)
                        status = cleanup
    except (OSError, ValueError, RuntimeError, tarfile.TarError, subprocess.SubprocessError) as error:
        invalidate(project)
        print(f"Wurst container validation failed: {error}", file=sys.stderr)
        return 1
    return status


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-revision", required=True)
    args = parser.parse_args()
    return validate(REPOSITORY, args.source_revision)


if __name__ == "__main__":
    raise SystemExit(main())
