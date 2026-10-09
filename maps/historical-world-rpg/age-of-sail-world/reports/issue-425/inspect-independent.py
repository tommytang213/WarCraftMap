#!/usr/bin/env python3
"""Compare exact W3N/W3X bytes with an unmodified, separately fetched mpyq.

Fetch eagleflo/mpyq at 6bfba18ec403f702666b4109db3d95f3b97b1dc5 and place
mpyq.py on PYTHONPATH. This reader cannot decrypt Grill's nested (listfile);
that limitation is recorded, never reported as an independent pass.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import sys

import mpyq

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "_shared/tooling"))
from warcraft_campaign import MpqReader


def inspect(campaign: Path, expected_sha: str) -> dict:
    if hashlib.sha256(Path(mpyq.__file__).read_bytes()).hexdigest() != 'e10fa2f422d837345f438934a99a3cdf67fa9148c7106d421408e1ecfa83e239':
        raise ValueError("independent reader differs from the recorded mpyq revision")
    data = campaign.read_bytes()
    if hashlib.sha256(data).hexdigest() != expected_sha:
        raise ValueError("campaign does not match the supplied SHA-256")
    independent = mpyq.MPQArchive(io.BytesIO(data))
    repository = MpqReader(campaign)
    for name, payload in repository.members().items():
        if independent.read_file(name.replace("/", "\\")) != payload:
            raise ValueError(f"campaign reader disagreement: {name}")
    manifest = json.loads(independent.read_file("campaign-manifest.json"))
    rows = []
    for entry in manifest["maps"]:
        payload = independent.read_file(entry["packagePath"].replace("/", "\\"))
        if hashlib.sha256(payload).hexdigest() != entry["sha256"]:
            raise ValueError(f"manifest mismatch: {entry['id']}")
        # MpqReader accepts a filesystem archive; compare decoded bytes without
        # writing untrusted member names to disk.
        import tempfile
        with tempfile.TemporaryDirectory(prefix="mpq-check-", dir=campaign.parent) as directory:
            path = Path(directory) / "member.w3x"
            path.write_bytes(payload)
            nested = MpqReader(path)
            external = mpyq.MPQArchive(io.BytesIO(payload), listfile=False)
            checked, unsupported = [], []
            for name, member in nested.members().items():
                try:
                    decoded = external.read_file(name.replace("/", "\\"))
                except NotImplementedError as error:
                    if name != "(listfile)":
                        raise
                    unsupported.append({"member": name, "reason": str(error)})
                    continue
                if decoded != member:
                    raise ValueError(f"nested reader disagreement: {entry['id']}/{name}")
                checked.append({"member": name, "sha256": hashlib.sha256(member).hexdigest()})
            rows.append({"id": entry["id"], "sha256": entry["sha256"],
                         "checked": checked, "unsupported": unsupported})
    return {"evidenceLevel": "independent_static_archive_read", "campaignSha256": expected_sha,
            "reader": "eagleflo/mpyq", "readerRevision": "6bfba18ec403f702666b4109db3d95f3b97b1dc5",
            "readerSha256": hashlib.sha256(Path(mpyq.__file__).read_bytes()).hexdigest(),
            "campaignMembers": len(repository.members()), "maps": rows, "nativeExecuted": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("campaign", type=Path)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = inspect(args.campaign, args.sha256)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(f"Independent agreement: {len(result['maps'])} maps; "
          f"{sum(len(row['checked']) for row in result['maps'])} nested members; "
          "encrypted listfiles excluded; native NOT RUN")
