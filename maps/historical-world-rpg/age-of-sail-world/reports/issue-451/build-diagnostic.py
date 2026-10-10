#!/usr/bin/env python3
"""Build all chapters after verifying a complete, current pinned execution run.

Reuses that exact execution evidence; every chapter still typechecks and compiles
with the pinned toolchain. Does not delete the local tools/evidence in _build.
"""
import argparse
from pathlib import Path
import shutil
import sys

PROJECT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT.parent / "_shared/tooling"))
import package_wurst_map
from package_wurst_campaign import build_campaign
import requirement_traceability as trace
from wurst_execution import source_revision


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--grill", required=True)
    parser.add_argument("--source-revision")
    args = parser.parse_args()
    revision = source_revision(PROJECT, args.source_revision)
    execution_dir = PROJECT / "_build/wurst-tests"
    evidence = trace.load(execution_dir / "results.json")
    transcript = (execution_dir / "execution.log").read_bytes()
    _, errors = trace.execution_results(PROJECT, evidence, transcript, revision)
    if errors:
        raise RuntimeError(errors)

    def reuse(config, executable, requested_revision=None):
        assert config.project == PROJECT and requested_revision == revision
        _, current_errors = trace.execution_results(PROJECT, evidence, transcript, revision)
        if current_errors:
            raise RuntimeError(current_errors)
        return evidence

    package_wurst_map.run_execution_tests = reuse
    # A prior interrupted diagnostic may leave assembled chapter trees. Clear
    # those generated maps while retaining the verified run and local toolchain.
    maps = PROJECT / "_build/maps"
    if maps.exists():
        shutil.rmtree(maps)
    build_campaign(PROJECT / "physical-maps.json", grill=args.grill,
                   clean_first=False, revision=revision)


if __name__ == "__main__":
    main()
