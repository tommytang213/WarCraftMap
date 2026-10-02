"""Machine-verifiable release compatibility policy for campaign persistence."""
from __future__ import annotations

import copy
import hashlib
import json
import time
from pathlib import Path
from typing import Any, Mapping

import campaign_save
import cross_map_persistence

MATRIX_FORMAT = "warcraftmap_release_save_compatibility_v1"
DIAGNOSTICS = {
    "compatible": "Save is compatible.",
    "migrated": "Save upgraded safely to the current release format.",
    "unsupported": "Save is not supported by this release.",
    "corrupt": "Save is damaged or incomplete and was not loaded.",
}
TRANSIENT_TERMS = ("handle", "widget", "frame", "camera", "effect", "audio", "sound", "timer", "trigger", "ui")


class CompatibilityError(ValueError): pass


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def compatibility_matrix(registry: campaign_save.MigrationRegistry | None = None) -> dict[str, Any]:
    save_registry = registry or campaign_save.MigrationRegistry()
    transfer_registry = cross_map_persistence.TransferMigrationRegistry()
    return {
        "format": MATRIX_FORMAT,
        "campaign": {
            "current": save_registry.current_version,
            "supportedSources": list(save_registry.supported_source_versions()),
            "paths": {str(v): list(save_registry.migration_path(v))
                      for v in save_registry.supported_source_versions()},
        },
        "crossMapTransfer": {
            "current": transfer_registry.current_version,
            "supportedSources": list(range(transfer_registry.current_version + 1)),
            "paths": {"0": [0, 1], "1": [1]},
        },
        "autosaveMetadata": {"current": 1, "supportedSources": [0, 1]},
        "nativeSaveIntegration": {"current": 1, "supportedSources": [1]},
        "visitedMapReconstruction": {"current": 1, "supportedSources": [0, 1]},
        "slots": ["autosave_01..autosave_15", "manual_N", "session_start", "major_milestone"],
    }


def load_manifest(path: str | Path) -> dict[str, Any]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if raw.get("format") != MATRIX_FORMAT:
        raise CompatibilityError("unsupported release compatibility manifest")
    if raw.get("matrix") != compatibility_matrix():
        raise CompatibilityError("compatibility manifest does not match executable migration registry")
    fixtures = raw.get("fixtures")
    if not isinstance(fixtures, list) or {x.get("schemaVersion") for x in fixtures if isinstance(x, dict)} != set(range(1, campaign_save.CURRENT_SCHEMA_VERSION + 1)):
        raise CompatibilityError("one immutable fixture is required for every supported campaign schema")
    return raw


def expand_fixture(manifest: Mapping[str, Any], fixture: Mapping[str, Any]) -> dict[str, Any]:
    """Expand a fixture over the pinned baseline without mutating either input."""
    result = copy.deepcopy(dict(fixture))
    result["document"] = copy.deepcopy(manifest["baselineDocument"])
    result["expectedCurrentAuthority"] = copy.deepcopy(manifest["expectedCurrentAuthority"])
    return result


def fixture_payload(fixture: Mapping[str, Any]) -> bytes:
    """Build the signed historical envelope represented by an immutable fixture."""
    document = copy.deepcopy(dict(fixture["document"]))
    document["schemaVersion"] = fixture["schemaVersion"]
    document["integrity"] = {"algorithm": campaign_save.CHECKSUM_ALGORITHM,
        "canonicalization": campaign_save.CANONICALIZATION, "checksum": ""}
    document["integrity"]["checksum"] = campaign_save._checksum(document)
    return canonical(document)


def normalized_authority(document: Mapping[str, Any]) -> dict[str, Any]:
    return copy.deepcopy(document["state"])


def classify_load(raw: bytes | str, registry: campaign_save.MigrationRegistry | None = None,
                  *, scenario_id: str = "age_of_sail_world", scenario_version: str = "1",
                  build_version: str = "phase8.1") -> tuple[str, str, dict[str, Any] | None]:
    """Return bounded English status; never expose parser or migration internals."""
    try:
        source = json.loads(raw)
        source_version = source.get("schemaVersion") if isinstance(source, dict) else None
        loaded = campaign_save.load_save(raw, registry)
        if (loaded["scenario"]["id"], loaded["scenario"]["version"], loaded["buildVersion"]) != \
                (scenario_id, scenario_version, build_version):
            raise campaign_save.IncompatibleSaveError("release identity mismatch")
        status = "compatible" if source_version == campaign_save.CURRENT_SCHEMA_VERSION else "migrated"
        return status, DIAGNOSTICS[status], loaded
    except campaign_save.IntegrityError:
        return "corrupt", DIAGNOSTICS["corrupt"], None
    except campaign_save.SaveError:
        return "unsupported", DIAGNOSTICS["unsupported"], None
    except (TypeError, ValueError, json.JSONDecodeError):
        return "corrupt", DIAGNOSTICS["corrupt"], None


def validate_release_fixture(fixture: Mapping[str, Any], budgets: Mapping[str, Any]) -> dict[str, Any]:
    payload = fixture_payload(fixture)
    started = time.perf_counter_ns(); status, _, loaded = classify_load(payload)
    elapsed_ms = (time.perf_counter_ns() - started) / 1e6
    if loaded is None or status not in {"compatible", "migrated"}:
        raise CompatibilityError("release fixture did not load")
    authority = normalized_authority(loaded)
    expected = fixture["expectedCurrentAuthority"]
    if authority != expected or digest(authority) != fixture["expectedAuthoritySha256"]:
        raise CompatibilityError("migrated authority differs from immutable expected snapshot")
    encoded = canonical(loaded)
    reload_started = time.perf_counter_ns(); reloaded = campaign_save.load_save(encoded)
    reload_ms = (time.perf_counter_ns() - reload_started) / 1e6
    if normalized_authority(reloaded) != authority:
        raise CompatibilityError("load/resave cycle is not deterministic")
    text = json.dumps(authority, sort_keys=True).lower()
    if any(term in text for term in TRANSIENT_TERMS):
        raise CompatibilityError("fixture made reconstructible presentation state authoritative")
    growth = max(0, len(encoded) - len(payload))
    if (len(encoded) > budgets["serializedStateBytes"] or
            elapsed_ms > budgets["migrationTimeMs"] or
            reload_ms > budgets["loadTimeMs"] or growth > budgets["stateGrowthBytes"]):
        raise CompatibilityError("release compatibility budget exceeded")
    return {"schemaVersion": fixture["schemaVersion"], "status": status,
            "authoritySha256": digest(authority), "bytes": len(encoded),
            "migrationMs": elapsed_ms, "loadMs": reload_ms, "stateGrowthBytes": growth}
