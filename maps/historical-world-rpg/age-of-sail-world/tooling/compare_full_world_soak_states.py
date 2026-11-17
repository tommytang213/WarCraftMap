#!/usr/bin/env python3
"""Compare *executed* soak end states from two complete authored checkouts.

Read-only diagnostic for issue #600 / PR #536. No fixture/hash rewriting, no
synthetic source reconstruction and no inference that headless play is native WC3.
Use two immutable git checkouts of the same project, each with its real sources.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "_shared" / "engine"))
import full_world_soak as soak  # noqa: E402

FORMAT = "warcraftmap_full_world_soak_state_comparison_v1"
PROVENANCE_KEYS = frozenset({"fixtureHash", "sourceCounts", "domains"})


def _manifest(path, config):
    base = path.resolve().parent
    files = {"config": path.resolve()}
    files.update({name: (base / relative).resolve() for name, relative in config["sources"].items()})
    return {name: {"sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                   "sizeBytes": source.stat().st_size}
            for name, source in sorted(files.items())}


def _run(config, sources, profile, seed):
    initial = soak.build_fixture(config, sources, seed)
    snapshots = []
    for mode in ("normal", "accelerated", "resumed"):
        state = copy.deepcopy(initial)
        if mode == "resumed":
            soak.advance(state, profile.checkpoint_date, profile.step_days,
                         config["workload"], profile.representation_limit)
            state = soak.resume(json.loads(soak.canonical(soak.checkpoint(state))))
        soak.advance(state, state["endDate"],
                     profile.jump_days if mode != "normal" else profile.step_days,
                     config["workload"], profile.representation_limit)
        snapshots.append((mode, state, soak.normalized_state_hash(state)))
    if len({entry[2] for entry in snapshots}) != 1:
        raise RuntimeError(f"seed {seed}: normal/jump/checkpoint execution mismatch")
    result = copy.deepcopy(snapshots[0][1])
    result.pop("activeRepresentations", None)  # Same normalization as the actual regression.
    return result, snapshots[0][2]


def _summarize(old, new):
    row = {"referenceHash": soak.digest(old), "candidateHash": soak.digest(new)}
    if isinstance(old, dict) and isinstance(new, dict):
        left, right = set(old), set(new)
        row.update({"removedKeys": sorted(left - right)[:20],
                    "addedKeys": sorted(right - left)[:20],
                    "changedKeys": sorted(k for k in left & right if old[k] != new[k])[:40],
                    "referenceLength": len(old), "candidateLength": len(new)})
    elif isinstance(old, list) and isinstance(new, list):
        row.update({"referenceLength": len(old), "candidateLength": len(new)})
        if all(isinstance(item, str) for item in old + new):
            row.update({"removedIds": sorted(set(old) - set(new))[:20],
                        "addedIds": sorted(set(new) - set(old))[:20]})
    elif isinstance(old, (str, int, float, bool, type(None))) and isinstance(new, type(old)):
        row.update({"referenceValue": old, "candidateValue": new})
    return row


def _check_compatible(reference_config, candidate_config, ref_profile, candidate_profile):
    for key in ("logicalTickDays", "workload"):
        if reference_config[key] != candidate_config[key]:
            raise ValueError(f"incomparable soak configurations: {key} differs")
    for attr in ("seeds", "step_days", "jump_days", "checkpoint_date", "representation_limit"):
        if getattr(ref_profile, attr) != getattr(candidate_profile, attr):
            raise ValueError(f"incomparable soak profiles: {attr} differs")
    if set(reference_config["sources"]) != set(candidate_config["sources"]):
        raise ValueError("incomparable soak configurations: source set differs")


def compare(reference_path, candidate_path, profile_name):
    reference_config, reference_sources, reference_profiles = soak.load_config(reference_path)
    candidate_config, candidate_sources, candidate_profiles = soak.load_config(candidate_path)
    if profile_name not in reference_profiles or profile_name not in candidate_profiles:
        raise ValueError(f"profile {profile_name!r} missing from one of the checkouts")
    ref_profile, candidate_profile = reference_profiles[profile_name], candidate_profiles[profile_name]
    _check_compatible(reference_config, candidate_config, ref_profile, candidate_profile)
    runs = []
    for seed in ref_profile.seeds:
        old, old_hash = _run(reference_config, reference_sources, ref_profile, seed)
        new, new_hash = _run(candidate_config, candidate_sources, candidate_profile, seed)
        changed = {key: _summarize(old.get(key), new.get(key))
                   for key in sorted(set(old) | set(new)) if old.get(key) != new.get(key)}
        provenance_only = bool(changed) and set(changed) <= PROVENANCE_KEYS
        runs.append({"seed": seed, "referenceNormalizedHash": old_hash,
                     "candidateNormalizedHash": new_hash,
                     "referenceGoldenMatched": old_hash == dict(ref_profile.expected_hashes)[seed],
                     "candidateGoldenMatched": new_hash == dict(candidate_profile.expected_hashes)[seed],
                     "changedFields": changed,
                     "provenanceOnlyFieldDrift": provenance_only,
                     "onlyFixtureFingerprintChanged": set(changed) == {"fixtureHash"}})
    return {"format": FORMAT, "profile": profile_name,
            "referenceInputs": _manifest(reference_path, reference_config),
            "candidateInputs": _manifest(candidate_path, candidate_config),
            "runs": runs,
            "note": "Read-only complete-source headless comparison, not authority to change golden hashes or claim retail WC3 success."}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference-config", type=Path, required=True,
                        help="Full-world soak config in complete, immutable reference checkout")
    parser.add_argument("--candidate-config", type=Path,
                        default=PROJECT / "scenario/benchmarks/full-world-soak.json")
    parser.add_argument("--profile", default="smoke")
    parser.add_argument("--output", type=Path, help="Optional JSON evidence destination")
    args = parser.parse_args(argv)
    try:
        result = compare(args.reference_config, args.candidate_config, args.profile)
    except (OSError, ValueError, RuntimeError, soak.SoakError, soak.InvariantFailure) as exc:
        parser.exit(2, f"soak state comparison failed: {exc}\n")
    encoded = json.dumps(result, sort_keys=True, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8")
    print(encoded, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
