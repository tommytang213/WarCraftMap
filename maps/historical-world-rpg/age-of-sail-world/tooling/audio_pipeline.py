#!/usr/bin/env python3
"""Validate the scenario audio catalogue/profiles and emit bounded JSON reports."""
from __future__ import annotations
import argparse
import hashlib
import json
import wave
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(ROOT.parent / "_shared/tooling"))
from validate_audio import AudioValidationError, load, validate as validate_audio

def validate(manifest, profiles, import_root=None):
    return validate_audio(manifest, profiles, import_root or ROOT,
                          profile_format="age_of_sail_audio_profiles_v1")


def reports(manifest, profiles):
    checked = validate(manifest, profiles)
    contexts = {key: [] for key in ("region", "settlement", "travel", "combat", "modal", "event")}
    for row in profiles["profiles"]:
        for key in contexts:
            field = key + "_id" if key == "region" else ("settlement_type" if key == "settlement" else key)
            if field in row["match"]: contexts[key].append({"value":row["match"][field],"profileId":row["id"],"categories":sorted(row["layers"])})
    coverage={"format":"audio_coverage_report_v1","contexts":contexts,"feedback":profiles["feedback"],"assetCount":len(checked["assets"]),"importedBytes":checked["importedBytes"],"decodedBytes":checked["decodedBytes"]}
    waveform={"format":"audio_waveform_summary_v1","assets":[{"id":x["id"],"durationMs":x["technical"]["durationMs"],"sampleRateHz":x["technical"]["sampleRateHz"],"channels":x["technical"]["channels"],"integratedLufs":x["technical"]["integratedLufs"],"peakDbfs":x["technical"]["peakDbfs"],"loop":x["technical"]["loop"],"source":x["source"],"diagnostics":[]} for x in manifest["assets"]]}
    return coverage, waveform

def main(argv=None):
    parser=argparse.ArgumentParser(); parser.add_argument("--check",action="store_true"); parser.add_argument("--output",type=Path,default=ROOT/"scenario/audio/reports"); args=parser.parse_args(argv)
    manifest=load(ROOT/"scenario/audio/manifest.json"); profiles=load(ROOT/"scenario/audio/profiles.json"); coverage,waveform=reports(manifest,profiles)
    expected={"coverage.json":coverage,"waveform-loudness.json":waveform}
    if args.check:
        for name,data in expected.items():
            if load(args.output/name) != data: raise AudioValidationError(f"stale audio report: {name}")
    else:
        args.output.mkdir(parents=True,exist_ok=True)
        for name,data in expected.items(): (args.output/name).write_text(json.dumps(data,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    return 0

if __name__ == "__main__": raise SystemExit(main())
