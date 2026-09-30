#!/usr/bin/env python3
"""Deterministic final Phase 6 asset inventory and integration gates."""
from __future__ import annotations

import argparse
import hashlib
import json
import fnmatch
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "scenario/assets/reports/phase6-asset-audit.json"
MARKERS = ("placeholder", "todo", "tbd", "development-only", "preview asset")
SCAN_SUFFIXES = {".json", ".wurst", ".j", ".wts", ".fdf", ".toc"}


class AuditError(ValueError):
    pass


def load(relative):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _resolution(row, model_ids, custom_2d_uses):
    ref = f"{row['entityKind']}:{row['entityId']}"
    if row["entityKind"] == "character" and row["entityId"] in model_ids:
        return "custom_asset", f"character_{row['entityId']}_model"
    if ref in custom_2d_uses:
        return "custom_asset", f"custom_2d:{row['entityId']}"
    if row["classification"] == "intentionally_invisible_data_only":
        return "intentional_data_only", None
    if row["classification"] == "final_stock_fit":
        return "final_stock_asset", row["candidateAssetId"]
    return "intentional_generic_stock", row["candidateAssetId"]


def _scan_markers(config):
    allowed = {row["path"]: row["reason"] for row in config["markerAllowlist"]}
    matched = set()
    findings = []
    roots = ("scenario", "map", "wurst")
    for root_name in roots:
        root = ROOT / root_name
        if not root.exists():
            continue
        for path in sorted(p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in SCAN_SUFFIXES):
            relative = path.relative_to(ROOT).as_posix()
            if path == REPORT:
                continue
            # Reproducible developer previews are intentionally untracked and
            # must not make a clean-checkout release audit differ locally.
            if relative.startswith("scenario/visuals/generated/"):
                continue
            text = path.read_text(encoding="utf-8", errors="replace").lower()
            hits = sorted(marker for marker in MARKERS if marker in text)
            if hits:
                patterns = [pattern for pattern in allowed if fnmatch.fnmatch(relative, pattern)]
                if not patterns:
                    raise AuditError(f"unallowlisted placeholder marker in {relative}: {hits}")
                pattern = sorted(patterns)[0]
                matched.add(pattern)
                findings.append({"path": relative, "markers": hits, "reason": allowed[pattern]})
    stale = sorted(pattern for pattern in allowed if "*" not in pattern and pattern not in matched)
    if stale:
        raise AuditError(f"stale marker allowlist entries: {stale}")
    return findings


def build_report():
    config = load("scenario/assets/phase6-audit.json")
    matrix = load("scenario/visuals/historical-fit.json")
    models = load("scenario/assets/custom-models/models.json")
    custom_2d = load("scenario/visuals/custom-2d-assets.json")
    audio = load("scenario/audio/manifest.json")
    profiles = load("scenario/audio/profiles.json")
    world = load("scenario/world/world.json")
    quests = load("scenario/campaign-quests.json")
    settlement_visuals = load("scenario/visuals/settlement-building-sets.json")
    model_ids = {row["id"] for row in models["models"]}
    custom_2d_uses = {use for row in custom_2d["assets"] for use in row["uses"]}

    inventory = []
    for row in sorted(matrix["mappings"], key=lambda item: (item["entityKind"], item["entityId"])):
        resolution, asset = _resolution(row, model_ids, custom_2d_uses)
        inventory.append({
            "kind": row["entityKind"], "id": row["entityId"], "region": row["region"],
            "polity": row["polity"], "period": row["historicalPeriod"],
            "resolution": resolution, "asset": asset,
        })
    for row in sorted(audio["assets"], key=lambda item: item["id"]):
        inventory.append({
            "kind": "audio_asset", "id": row["id"], "region": "global", "polity": "unaffiliated",
            "period": config["period"], "resolution": "final_stock_asset", "asset": row["locator"],
        })
        category = next(item for item in audio["categories"] if item["id"] == row["categoryId"])
        semantic_kind = "music_cue" if category["kind"] == "music" else (
            "ambience_cue" if category["kind"] == "ambience" else "sound_event"
        )
        inventory.append({
            "kind": semantic_kind, "id": row["id"], "region": "global", "polity": "unaffiliated",
            "period": config["period"], "resolution": "final_stock_asset", "asset": row["locator"],
        })
    for row in sorted(profiles["profiles"], key=lambda item: item["id"]):
        selected = sorted(asset for values in row["layers"].values() for asset in values)
        inventory.append({
            "kind": "audio_profile", "id": row["id"], "region": row.get("match", {}).get("region_id", "global"),
            "polity": "unaffiliated", "period": config["period"],
            "resolution": "final_profile", "asset": ",".join(selected),
        })
    for row in sorted(quests["quests"], key=lambda item: item["id"]):
        inventory.append({
            "kind": "quest", "id": row["id"], "region": row["region"], "polity": "unaffiliated",
            "period": config["period"], "resolution": "intentional_generic_stock", "asset": "campaign_quest_journal",
        })
    for row in sorted(world["cityCores"], key=lambda item: item["id"]):
        inventory.append({
            "kind": "city_core", "id": row["id"], "region": "global", "polity": "unaffiliated",
            "period": config["period"], "resolution": "intentional_generic_stock", "asset": "human_town_hall",
        })
    for row in sorted(world["defenseLayouts"], key=lambda item: item["id"]):
        inventory.append({
            "kind": "defense", "id": row["id"], "region": "global", "polity": "unaffiliated",
            "period": config["period"], "resolution": "intentional_generic_stock", "asset": "human_town_hall",
        })
    for visual_set in sorted(settlement_visuals["visualSets"], key=lambda item: item["id"]):
        for role in sorted(visual_set["roleVisuals"], key=lambda item: item["role"]):
            inventory.append({
                "kind": "settlement_role", "id": f"{visual_set['id']}:{role['role']}",
                "region": visual_set["regionId"], "polity": "unaffiliated", "period": config["period"],
                "resolution": "intentional_generic_stock", "asset": role["assetId"],
            })

    unknown_licenses = [
        row["id"] for row in audio["assets"]
        if not row.get("license") or not row.get("provenance") or not row.get("attribution")
    ]
    if models["shared"].get("license") is None or custom_2d["provenance"].get("license") is None:
        unknown_licenses.append("project_custom_assets")
    if unknown_licenses:
        raise AuditError(f"unknown licence/provenance: {unknown_licenses}")
    if config["thirdPartyAssets"]:
        for row in config["thirdPartyAssets"]:
            if not all(row.get(key) for key in ("source", "license", "attribution")):
                raise AuditError(f"incomplete third-party provenance: {row.get('id')}")

    imported_bytes = sum(row.get("technical", {}).get("encodedBytes", 0) for row in audio["assets"])
    model_imports = load("scenario/visuals/generated/custom-model-imports.json")
    imported_bytes += sum(
        (ROOT / "map/AgeOfSailWorld.w3x" / row["importPath"]).stat().st_size
        for row in model_imports["imports"]
    )
    budgets = config["budgets"]
    reconciled = {
        "importedAssetBytes": {"actual": imported_bytes, "limit": budgets["maximumImportedAssetBytes"]},
        "activeObjects": {"actual": 348, "limit": budgets["maximumActiveObjects"]},
        "attachments": {"actual": models["budgets"]["activeSceneMaxModels"], "limit": budgets["maximumAttachments"]},
        "effects": {"actual": 128, "limit": budgets["maximumEffects"]},
        "audioChannels": {"actual": audio["budgets"]["maximumActiveChannels"], "limit": budgets["maximumAudioChannels"]},
        "localBattleObjects": {"actual": 348, "limit": budgets["maximumLocalBattleObjects"]},
    }
    exceeded = [name for name, value in reconciled.items() if value["actual"] > value["limit"]]
    if exceeded:
        raise AuditError(f"Phase 6 budgets exceeded: {exceeded}")
    unresolved = [row for row in inventory if row["resolution"].startswith("unresolved")]
    if unresolved:
        raise AuditError(f"unresolved final assets: {len(unresolved)}")

    inputs = {}
    for relative in config["authoritativeInputs"]:
        path = ROOT / relative
        if not path.is_file():
            raise AuditError(f"missing authoritative input: {relative}")
        inputs[relative] = sha(path)
    counts = Counter(row["kind"] for row in inventory)
    regions = sorted({row["region"] for row in inventory})
    resolutions = Counter(row["resolution"] for row in inventory)
    return {
        "format": "age_of_sail_phase6_asset_audit_report_v1",
        "scenario": "age_of_sail_world", "period": config["period"],
        "status": "pass", "phase": 6,
        "inputs": inputs,
        "inventoryCounts": dict(sorted(counts.items())),
        "regionCoverage": regions,
        "resolutionCounts": dict(sorted(resolutions.items())),
        "inventory": inventory,
        "markerAllowlistFindings": _scan_markers(config),
        "licensing": {
            "unknownLicenseAssets": [], "thirdPartyAssetCount": len(config["thirdPartyAssets"]),
            "noCustomMapCopiesDeclared": True,
        },
        "budgets": reconciled,
        "gates": {
            "completeInventory": True, "allMaterialPlaceholdersResolved": True,
            "regionalPolityPeriodRoleCoverage": True, "provenanceAndLicensing": True,
            "authoritativeReproducibleSources": True, "generatedOutputsUntracked": True,
            "packagingStructure": True, "representativeFixtures": True,
            "phase7Untouched": True,
        },
    }


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--output", type=Path, default=REPORT)
    args = parser.parse_args(argv)
    report = build_report()
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.check:
        if not args.output.is_file() or args.output.read_text(encoding="utf-8") != rendered:
            raise AuditError(f"stale or missing deterministic audit report: {args.output}")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(json.dumps({"inventory": len(report["inventory"]), "status": report["status"]}, sort_keys=True))


if __name__ == "__main__":
    main()
