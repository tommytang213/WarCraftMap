#!/usr/bin/env python3
"""Verify the exact CI release payload and write upload-bound evidence."""
import argparse
import hashlib
import json
import zipfile
from pathlib import Path

from package_release_candidate import CONFIG, load_release_config, verify_release_archive


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("archive", type=Path)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--evidence", required=True, type=Path)
    args = parser.parse_args()
    verify_release_archive(args.archive, load_release_config(CONFIG))
    payload = args.archive.read_bytes()
    with zipfile.ZipFile(args.archive) as archive:
        manifest = json.loads(archive.read("Metadata/artifact-manifest.json"))
        provenance = json.loads(archive.read("Metadata/build-provenance.json"))
    revisions = {manifest.get("sourceRevision"), provenance.get("sourceRevision")}
    if revisions != {args.source_revision}:
        raise SystemExit(f"release source revision mismatch: {sorted(str(x) for x in revisions)}")
    evidence = {
        "format": "warcraftmap_ci_uploaded_artifact_v1",
        "sourceRevision": args.source_revision,
        "fileName": args.archive.name,
        "bytes": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "releaseCandidateId": manifest["releaseCandidateId"],
        "verification": "package_release_candidate.verify_release_archive",
    }
    args.evidence.write_text(json.dumps(evidence, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
