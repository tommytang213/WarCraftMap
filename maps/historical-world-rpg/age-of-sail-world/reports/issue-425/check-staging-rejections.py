#!/usr/bin/env python3
"""Negative checks against the exact revised campaign and Wurst receipts."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
import tempfile

PROJECT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT / "tooling"))
from stage_launch_smoke import stage
from warcraft_campaign import MpqReader, write_mpq


def check(campaign: Path, execution: Path, revision: str) -> dict:
    outcomes = []
    with tempfile.TemporaryDirectory(prefix="staging-rejections-", dir=campaign.parent) as directory:
        root = Path(directory)

        def reject(label, artifact, source_revision, reason):
            output = root / label
            try:
                stage(artifact, execution, output, source_revision)
            except (ValueError, RuntimeError) as error:
                if reason not in str(error):
                    raise AssertionError(f"unexpected rejection: {error}") from error
                if output.exists():
                    raise AssertionError("staging wrote output before validation finished")
                outcomes.append({"case": label, "status": "rejected_before_staging", "error": str(error)})
            else:
                raise AssertionError(f"staging accepted {label}")

        reject("stale-revision", campaign, "0" * 40, "mismatched Wurst execution evidence")
        files = MpqReader(campaign).members()
        manifest = json.loads(files["campaign-manifest.json"])
        first = next(row for row in manifest["maps"] if row["bootstrap"])
        member = next(name for name in files if name.casefold() == first["packagePath"].casefold())
        nested = root / "bootstrap.w3x"
        nested.write_bytes(files[member])
        members = MpqReader(nested).members()
        script, count = re.subn(rb"^\s*SetDayNightModels\([^\n]*\)\n", b"", members["war3map.lua"], count=1, flags=re.M)
        if count != 1:
            raise AssertionError("revised bootstrap lacks the controlled lighting call")
        members["war3map.lua"] = script
        write_mpq(nested, members)
        files[member] = nested.read_bytes()
        # Preserve a self-consistent manifest and source stamp: only checking
        # hashes/identity would incorrectly accept this damaged compiled member.
        first["sha256"] = hashlib.sha256(files[member]).hexdigest()
        files["campaign-manifest.json"] = json.dumps(manifest).encode()
        damaged = root / "missing-lighting.w3n"
        write_mpq(damaged, files)
        reject("archived-lighting-omitted", damaged, revision, "lighting")
    return {"evidenceLevel": "automated_staging_negative_controls", "nativeExecuted": False,
            "campaignSha256": hashlib.sha256(campaign.read_bytes()).hexdigest(), "checks": outcomes}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--campaign", type=Path, required=True)
    parser.add_argument("--execution", type=Path, required=True)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = check(args.campaign, args.execution, args.source_revision)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print("Stale revision and damaged archived Lua rejected before diagnostic staging.")
