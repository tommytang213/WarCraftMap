#!/usr/bin/env python3
"""Validate/resolve scenario-neutral Warcraft asset catalogues and fit matrices."""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

KINDS = {"unit_model", "building_model", "item_model", "effect_model", "terrain_texture", "icon", "portrait", "sound", "interface_texture"}
CLASSES = {"final_stock_fit", "acceptable_stock_variation", "temporary_placeholder", "custom_icon_texture_candidate", "custom_model_candidate", "sound_candidate", "intentionally_invisible_data_only"}
RENDERERS = {"classic", "reforged"}
ENTITY_KINDS = {"runtime_template", "ship", "unit", "character", "settlement", "building", "equipment", "treasure", "ability", "effect", "terrain_feature", "ui_concept"}

class AssetValidationError(ValueError): pass

def load(path):
    with Path(path).open(encoding="utf-8") as handle: return json.load(handle)

def _unique(rows, label):
    ids = [x.get("id") for x in rows]
    duplicates = sorted(k for k, count in Counter(ids).items() if count > 1)
    if duplicates: raise AssetValidationError(f"duplicate {label} IDs: {duplicates}")

def validate_manifest(data):
    if data.get("format") != "warcraft_asset_manifest_v1": raise AssetValidationError("invalid manifest format")
    assets = data.get("assets", []); _unique(assets, "asset")
    by_id = {x["id"]: x for x in assets}
    locators = set()
    for asset in assets:
        aid = asset["id"]
        if not isinstance(aid, str) or not re.fullmatch(r"[a-z][a-z0-9_]*", aid): raise AssetValidationError(f"{aid}: unstable asset ID")
        if asset.get("kind") not in KINDS: raise AssetValidationError(f"{aid}: invalid asset kind")
        locator = asset.get("locator", {})
        if locator.get("type") not in {"path", "object_id"} or not locator.get("value"): raise AssetValidationError(f"{aid}: missing path or ID")
        locators.add((locator["type"], locator["value"]))
        renderers = set(asset.get("renderers", []))
        if not renderers or not renderers <= RENDERERS: raise AssetValidationError(f"{aid}: unsupported renderer assumption")
        scale = asset.get("scale", {})
        if not (0 < scale.get("min", 0) <= scale.get("max", 0)): raise AssetValidationError(f"{aid}: invalid scale limits")
        provenance = asset.get("provenance", {})
        if provenance.get("origin") == "external" and (not provenance.get("source") or not provenance.get("attribution")): raise AssetValidationError(f"{aid}: undocumented external provenance")
        if not asset.get("license"): raise AssetValidationError(f"{aid}: missing license")
        if asset.get("validation", {}).get("status") not in {"verified", "metadata_verified", "pending"}: raise AssetValidationError(f"{aid}: invalid validation status")
    for asset in assets:
        for key, target in asset.get("relationships", {}).items():
            if target not in by_id: raise AssetValidationError(f"{asset['id']}: broken {key}")
            expected = {"portraitAssetId":"portrait", "iconAssetId":"icon", "modelAssetId":None}[key]
            if expected and by_id[target]["kind"] != expected: raise AssetValidationError(f"{asset['id']}: invalid {key}")
        for target in asset.get("soundDependencies", []):
            if target not in by_id or by_id[target]["kind"] != "sound": raise AssetValidationError(f"{asset['id']}: broken sound dependency")
    return by_id

def validate_matrix(data, assets):
    if data.get("format") != "historical_fit_matrix_v1": raise AssetValidationError("invalid matrix format")
    mappings = data.get("mappings", []); _unique(mappings, "mapping")
    refs = [(x.get("entityKind"), x.get("entityId")) for x in mappings]
    duplicates = sorted(k for k, count in Counter(refs).items() if count > 1)
    if duplicates: raise AssetValidationError(f"duplicate scenario references: {duplicates}")
    for row in mappings:
        rid = row["id"]
        if not re.fullmatch(r"[a-z][a-z0-9_]*", rid): raise AssetValidationError(f"{rid}: unstable mapping ID")
        if row.get("entityKind") not in ENTITY_KINDS: raise AssetValidationError(f"{rid}: invalid entity kind")
        if row.get("classification") not in CLASSES: raise AssetValidationError(f"{rid}: invalid classification")
        asset_id = row.get("candidateAssetId")
        if row["classification"] != "intentionally_invisible_data_only" and asset_id not in assets: raise AssetValidationError(f"{rid}: missing candidate asset")
        for required in ("historicalPeriod", "culturalApplicability", "readabilityStrengths", "knownMismatches", "permittedVariation", "replacementPriority"):
            if required not in row: raise AssetValidationError(f"{rid}: missing {required}")
        if asset_id:
            asset = assets[asset_id]; variation = row["permittedVariation"]
            if not set(variation.get("renderers", [])) <= set(asset["renderers"]): raise AssetValidationError(f"{rid}: renderer outside asset constraints")
            if not asset["scale"]["min"] <= variation.get("scale", 1) <= asset["scale"]["max"]: raise AssetValidationError(f"{rid}: scale outside asset constraints")
            if variation.get("tint", False) and not asset["tintSuitable"]: raise AssetValidationError(f"{rid}: tint outside asset constraints")
            if not set(variation.get("attachments", [])) <= set(asset["attachmentPoints"]): raise AssetValidationError(f"{rid}: attachment outside asset constraints")
            if not set(variation.get("animations", [])) <= set(asset["animations"]): raise AssetValidationError(f"{rid}: animation outside asset constraints")
            if variation.get("footprint") != asset["footprint"]: raise AssetValidationError(f"{rid}: footprint variation is not permitted")
    return mappings

def coverage(mappings):
    report = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(int))))
    unresolved = []
    for row in sorted(mappings, key=lambda x: (x["region"], x["polity"], x["entityKind"], x["replacementPriority"], x["entityId"])):
        report[row["region"]][row["polity"]][row["entityKind"]][str(row["replacementPriority"])] += 1
        if row["classification"] in {"temporary_placeholder", "custom_icon_texture_candidate", "custom_model_candidate", "sound_candidate"}:
            unresolved.append({k: row[k] for k in ("region", "polity", "entityKind", "entityId", "replacementPriority", "classification")})
    return report, unresolved

def resolved_manifest(mappings, assets):
    return [{"entityKind": row["entityKind"], "entityId": row["entityId"], "classification": row["classification"],
             "assetId": row.get("candidateAssetId"), "locator": assets[row["candidateAssetId"]]["locator"] if row.get("candidateAssetId") else None}
            for row in sorted(mappings, key=lambda x: (x["entityKind"], x["entityId"]))]

def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True); parser.add_argument("--matrix", required=True)
    parser.add_argument("--coverage-out"); parser.add_argument("--unresolved-out"); parser.add_argument("--resolved-out"); args = parser.parse_args(argv)
    assets = validate_manifest(load(args.manifest)); mappings = validate_matrix(load(args.matrix), assets)
    report, unresolved = coverage(mappings)
    for path, payload in ((args.coverage_out, report), (args.unresolved_out, unresolved), (args.resolved_out, resolved_manifest(mappings, assets))):
        if path: Path(path).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"assets": len(assets), "mappings": len(mappings), "unresolved": len(unresolved)}, sort_keys=True))

if __name__ == "__main__": main()
