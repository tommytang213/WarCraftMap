#!/usr/bin/env python3
"""Package a conformance consumer and its content mutation with the pinned gate."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

from framework_conformance import mutate_content
from package_wurst_campaign import build_campaign


def source_hashes(shared):
    return {path.relative_to(shared).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(shared.rglob("*"))
            if path.is_file() and "__pycache__" not in path.parts}


def validate_fixture(project):
    project = project.resolve()
    shared = project.parent / "_shared"
    before = source_hashes(shared)
    original = build_campaign(project / "physical-maps.json")
    mutation_root = project / "_build/mutation"
    shutil.copytree(shared, mutation_root / "_shared",
                    ignore=shutil.ignore_patterns("__pycache__"))
    mutant = mutation_root / "campaign"
    mutate_content(project, mutant)
    mutated = build_campaign(mutant / "physical-maps.json")
    if before != source_hashes(shared) or before != source_hashes(mutation_root / "_shared"):
        raise RuntimeError("mutation changed framework source")
    report = {"status": "pass", "frameworkSources": before,
              "originalArchiveSha256": hashlib.sha256(original.read_bytes()).hexdigest(),
              "mutatedArchiveSha256": hashlib.sha256(mutated.read_bytes()).hexdigest(),
              "mutation": json.loads((project / "mutation.json").read_text())}
    (project / "_build/conformance-report.json").write_text(json.dumps(report, indent=2) + "\n")
    print("OK: original and content-mutated campaigns built with unchanged framework sources")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path)
    args = parser.parse_args()
    validate_fixture(args.project)


if __name__ == "__main__":
    main()
