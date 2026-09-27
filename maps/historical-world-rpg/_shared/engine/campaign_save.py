"""Headless campaign save contracts.

Warcraft-native storage is intentionally outside this module.  Callers provide
authoritative simulation dictionaries and persist the returned UTF-8 bytes only
after ``load_save``/``serialize_save`` succeeds.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any, Callable, Mapping


CURRENT_SCHEMA_VERSION = 1
AUTOSAVE_SLOT_COUNT = 15
CHECKSUM_ALGORITHM = "sha256"
CANONICALIZATION = "json_utf8_sorted_v1"

_VERSION_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]*$")
_CHECKSUM_RE = re.compile(r"^[0-9a-f]{64}$")
_TRANSIENT_KEY_RE = re.compile(r"handle|widget", re.IGNORECASE)


class SaveError(ValueError):
    """Base class for a rejected campaign save."""


class IntegrityError(SaveError):
    """The stored checksum does not match the stored document."""


class IncompatibleSaveError(SaveError):
    """The save cannot be migrated to the current schema."""


@dataclass(frozen=True)
class SaveSlot:
    kind: str
    index: int | None = None

    def __post_init__(self) -> None:
        allowed = {"autosave", "manual", "session_start", "major_milestone"}
        if self.kind not in allowed:
            raise SaveError(f"unknown save slot kind {self.kind!r}")
        if self.kind == "autosave" and (
            isinstance(self.index, bool)
            or not isinstance(self.index, int)
            or not 1 <= self.index <= AUTOSAVE_SLOT_COUNT
        ):
            raise SaveError("autosave slot index must be between 1 and 15")
        if self.kind == "manual" and (
            isinstance(self.index, bool) or not isinstance(self.index, int) or self.index < 1
        ):
            raise SaveError("manual slot index must be a positive integer")
        if self.kind in {"session_start", "major_milestone"} and self.index is not None:
            raise SaveError(f"{self.kind} checkpoint does not have an index")

    @property
    def stable_id(self) -> str:
        return f"{self.kind}_{self.index:02d}" if self.index is not None else self.kind

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {"kind": self.kind, "id": self.stable_id}
        if self.index is not None:
            result["index"] = self.index
        return result


def slot_layout(manual_slot_count: int) -> tuple[SaveSlot, ...]:
    """Return the complete stable slot layout for a configured campaign UI."""
    if isinstance(manual_slot_count, bool) or not isinstance(manual_slot_count, int) or manual_slot_count < 1:
        raise SaveError("manual_slot_count must be a positive integer")
    return tuple(
        [SaveSlot("autosave", index) for index in range(1, AUTOSAVE_SLOT_COUNT + 1)]
        + [SaveSlot("manual", index) for index in range(1, manual_slot_count + 1)]
        + [SaveSlot("session_start"), SaveSlot("major_milestone")]
    )


Migration = Callable[[dict[str, Any]], dict[str, Any]]


class MigrationRegistry:
    """Registry of one-version, pure save migrations."""

    def __init__(self, current_version: int = CURRENT_SCHEMA_VERSION) -> None:
        self.current_version = current_version
        self._migrations: dict[int, Migration] = {}

    def register(self, source_version: int, migration: Migration) -> None:
        if source_version < 0 or source_version >= self.current_version:
            raise ValueError("migration source must be older than the current schema")
        if source_version in self._migrations:
            raise ValueError(f"migration from schema {source_version} is already registered")
        self._migrations[source_version] = migration

    def migrate(self, document: Mapping[str, Any]) -> dict[str, Any]:
        result = copy.deepcopy(dict(document))
        version = _integer(result.get("schemaVersion"), "schemaVersion", minimum=0)
        if version > self.current_version:
            raise IncompatibleSaveError(
                f"save schema {version} is newer than supported schema {self.current_version}"
            )
        while version < self.current_version:
            migration = self._migrations.get(version)
            if migration is None:
                raise IncompatibleSaveError(f"no migration registered from schema {version}")
            migrated = migration(copy.deepcopy(result))
            if not isinstance(migrated, dict) or migrated.get("schemaVersion") != version + 1:
                raise IncompatibleSaveError(
                    f"migration from schema {version} must produce schema {version + 1}"
                )
            result = migrated
            version += 1
        return result


def serialize_save(
    *,
    build_version: str,
    scenario_id: str,
    scenario_version: str,
    slot: SaveSlot,
    created_at: str,
    world_state: Mapping[str, Any],
    player_state: Mapping[str, Any],
) -> bytes:
    """Create deterministic UTF-8 save bytes from authoritative simulation state."""
    document: dict[str, Any] = {
        "format": "warcraftmap_campaign",
        "schemaVersion": CURRENT_SCHEMA_VERSION,
        "buildVersion": build_version,
        "scenario": {"id": scenario_id, "version": scenario_version},
        "slot": slot.to_dict(),
        "createdAt": created_at,
        "state": {
            "world": copy.deepcopy(dict(world_state)),
            "players": copy.deepcopy(dict(player_state)),
        },
        "integrity": {
            "algorithm": CHECKSUM_ALGORITHM,
            "canonicalization": CANONICALIZATION,
            "checksum": "",
        },
    }
    _validate_document(document, require_current=True)
    document["integrity"]["checksum"] = _checksum(document)
    return _canonical_bytes(document)


def load_save(raw: bytes | str, registry: MigrationRegistry | None = None) -> dict[str, Any]:
    """Verify and load without mutating or rewriting the source save.

    Integrity is checked before migration.  The returned document is an in-memory
    migrated copy; persistence of that copy is a separate, explicit caller action.
    """
    try:
        document = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError) as exc:
        raise SaveError(f"invalid campaign save JSON: {exc}") from exc
    if not isinstance(document, dict):
        raise SaveError("campaign save root must be an object")
    _verify_integrity(document)
    migrated = (registry or MigrationRegistry()).migrate(document)
    _validate_document(migrated, require_current=True)
    # Migration changes the protected content, so expose accurate in-memory metadata.
    migrated["integrity"]["checksum"] = _checksum(migrated)
    return migrated


def _canonical_bytes(value: Any) -> bytes:
    try:
        return json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise SaveError(f"state is not canonical JSON data: {exc}") from exc


def _checksum(document: Mapping[str, Any]) -> str:
    protected = copy.deepcopy(dict(document))
    integrity = protected.get("integrity")
    if not isinstance(integrity, dict):
        raise SaveError("integrity must be an object")
    integrity["checksum"] = ""
    return hashlib.sha256(_canonical_bytes(protected)).hexdigest()


def _verify_integrity(document: Mapping[str, Any]) -> None:
    integrity = document.get("integrity")
    if not isinstance(integrity, dict):
        raise IntegrityError("missing integrity metadata")
    if integrity.get("algorithm") != CHECKSUM_ALGORITHM:
        raise IntegrityError("unsupported checksum algorithm")
    if integrity.get("canonicalization") != CANONICALIZATION:
        raise IntegrityError("unsupported canonicalization")
    checksum = integrity.get("checksum")
    if not isinstance(checksum, str) or not _CHECKSUM_RE.fullmatch(checksum):
        raise IntegrityError("invalid checksum metadata")
    if checksum != _checksum(document):
        raise IntegrityError("campaign save checksum mismatch")


def _integer(value: Any, context: str, minimum: int = 1) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise SaveError(f"{context} must be an integer >= {minimum}")
    return value


def _nonempty_version(value: Any, context: str) -> None:
    if not isinstance(value, str) or not _VERSION_RE.fullmatch(value):
        raise SaveError(f"{context} must be a stable version token")


def _reject_transient_values(value: Any, path: str = "state") -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if not isinstance(key, str):
                raise SaveError(f"{path}: JSON object keys must be strings")
            if _TRANSIENT_KEY_RE.search(key):
                raise SaveError(f"{path}.{key}: transient Warcraft handles cannot be persisted")
            _reject_transient_values(child, f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            _reject_transient_values(child, f"{path}[{index}]")
    elif value is not None and not isinstance(value, (str, int, float, bool)):
        raise SaveError(f"{path}: only authoritative JSON values may be persisted")


def _validate_document(document: Mapping[str, Any], *, require_current: bool) -> None:
    if document.get("format") != "warcraftmap_campaign":
        raise SaveError("unsupported campaign save format")
    version = _integer(document.get("schemaVersion"), "schemaVersion", minimum=0)
    if require_current and version != CURRENT_SCHEMA_VERSION:
        raise IncompatibleSaveError(f"expected save schema {CURRENT_SCHEMA_VERSION}, got {version}")
    _nonempty_version(document.get("buildVersion"), "buildVersion")
    scenario = document.get("scenario")
    if not isinstance(scenario, dict):
        raise SaveError("scenario metadata must be an object")
    _nonempty_version(scenario.get("id"), "scenario.id")
    _nonempty_version(scenario.get("version"), "scenario.version")
    if not isinstance(document.get("createdAt"), str) or not document["createdAt"]:
        raise SaveError("createdAt must be a non-empty timestamp")
    slot_data = document.get("slot")
    if not isinstance(slot_data, dict):
        raise SaveError("slot must be an object")
    slot = SaveSlot(slot_data.get("kind"), slot_data.get("index"))
    if slot_data.get("id") != slot.stable_id:
        raise SaveError("slot.id does not match its kind and index")
    state = document.get("state")
    if not isinstance(state, dict) or not isinstance(state.get("world"), dict) or not isinstance(state.get("players"), dict):
        raise SaveError("state.world and state.players must be objects")
    _reject_transient_values(state)
