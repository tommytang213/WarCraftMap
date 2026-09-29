"""Scenario-neutral, transactional state transfer between physical maps.

Physical maps are presentation slices.  This module transports one authoritative
campaign state and asks registered adapters to rebuild only the destination slice.
It deliberately has no Warcraft API dependency and never serializes map objects.
"""
from __future__ import annotations

import copy
import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Protocol, Sequence

from campaign_save import CANONICALIZATION, CHECKSUM_ALGORITHM, MigrationRegistry

TRANSFER_FORMAT = "warcraftmap_cross_map_transfer"
CURRENT_TRANSFER_SCHEMA = 1
_TOKEN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]*$")
_ID = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_TRANSIENT = re.compile(
    r"(?:handle|widget|frame|camera|effect|lightning|timer|trigger|unitobject|"
    r"runtimeobject|localruntime|uiobject)", re.IGNORECASE
)


class TransferError(ValueError): pass
class TransferIntegrityError(TransferError): pass
class IncompatibleTransferError(TransferError): pass
class DestinationContentError(TransferError): pass
class ReconstructionError(TransferError): pass
class TransferStorageError(TransferError): pass


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=False, allow_nan=False).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise TransferError(f"transfer contains non-canonical data: {exc}") from exc


def _checksum(document: Mapping[str, Any]) -> str:
    protected = copy.deepcopy(dict(document))
    integrity = protected.get("integrity")
    if not isinstance(integrity, dict):
        raise TransferIntegrityError("missing transfer integrity metadata")
    integrity["checksum"] = ""
    return hashlib.sha256(_canonical(protected)).hexdigest()


def _reject_transient(value: Any, path: str = "state") -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            if not isinstance(key, str):
                raise TransferError(f"{path}: object keys must be strings")
            if _TRANSIENT.search(key):
                raise TransferError(f"{path}.{key}: transient map-local data cannot be transferred")
            _reject_transient(child, f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            _reject_transient(child, f"{path}[{index}]")
    elif value is not None and not isinstance(value, (str, int, float, bool)):
        raise TransferError(f"{path}: only authoritative JSON values may be transferred")


class TransferMigrationRegistry:
    """Pure, one-version migration registry for transfer envelopes."""
    def __init__(self, current_version: int = CURRENT_TRANSFER_SCHEMA) -> None:
        self.current_version = current_version
        self._migrations: dict[int, Callable[[dict[str, Any]], dict[str, Any]]] = {}
        if current_version == 1:
            self.register(0, self._v0_to_v1)

    def register(self, version: int, migration: Callable[[dict[str, Any]], dict[str, Any]]) -> None:
        if version < 0 or version >= self.current_version or version in self._migrations:
            raise ValueError("invalid or duplicate transfer migration source")
        self._migrations[version] = migration

    def migrate(self, document: Mapping[str, Any]) -> dict[str, Any]:
        result = copy.deepcopy(dict(document))
        version = result.get("schemaVersion")
        if isinstance(version, bool) or not isinstance(version, int) or version < 0:
            raise IncompatibleTransferError("invalid transfer schema version")
        if version > self.current_version:
            raise IncompatibleTransferError("transfer schema is newer than this build")
        while version < self.current_version:
            migration = self._migrations.get(version)
            if migration is None:
                raise IncompatibleTransferError(f"no transfer migration from schema {version}")
            try:
                candidate = migration(copy.deepcopy(result))
            except Exception as exc:
                raise IncompatibleTransferError(f"transfer migration from schema {version} failed: {exc}") from exc
            if not isinstance(candidate, dict) or candidate.get("schemaVersion") != version + 1:
                raise IncompatibleTransferError(f"transfer migration from schema {version} is invalid")
            result, version = candidate, version + 1
        return result

    @staticmethod
    def _v0_to_v1(document: dict[str, Any]) -> dict[str, Any]:
        document.setdefault("visitedMaps", {})
        document["schemaVersion"] = 1
        return document


def serialize_transfer(*, scenario_id: str, scenario_version: str, build_version: str,
                       campaign_schema: int, source_map_id: str, destination_map_id: str,
                       transition: Mapping[str, Any], transaction_id: str, sequence: int,
                       state: Mapping[str, Any], visited_maps: Mapping[str, Any]) -> bytes:
    """Serialize the complete stable-ID authority, never a local projection."""
    document = {
        "format": TRANSFER_FORMAT, "schemaVersion": CURRENT_TRANSFER_SCHEMA,
        "scenario": {"id": scenario_id, "version": scenario_version},
        "buildVersion": build_version, "campaignSchemaVersion": campaign_schema,
        "sourceMapId": source_map_id, "destinationMapId": destination_map_id,
        "transition": copy.deepcopy(dict(transition)),
        "transaction": {"id": transaction_id, "sequence": sequence},
        "state": copy.deepcopy(dict(state)), "visitedMaps": copy.deepcopy(dict(visited_maps)),
        "integrity": {"algorithm": CHECKSUM_ALGORITHM, "canonicalization": CANONICALIZATION,
                      "checksum": ""},
    }
    _validate(document)
    document["integrity"]["checksum"] = _checksum(document)
    return _canonical(document)


def load_transfer(raw: bytes | str, *, scenario_id: str, scenario_version: str,
                  build_version: str, campaign_schema: int,
                  registry: TransferMigrationRegistry | None = None) -> dict[str, Any]:
    """Integrity-check and migrate a payload without mutating active state."""
    try:
        document = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError) as exc:
        raise TransferError(f"invalid transfer JSON: {exc}") from exc
    if not isinstance(document, dict):
        raise TransferError("transfer root must be an object")
    integrity = document.get("integrity")
    if not isinstance(integrity, dict) or integrity.get("algorithm") != CHECKSUM_ALGORITHM \
            or integrity.get("canonicalization") != CANONICALIZATION:
        raise TransferIntegrityError("unsupported or missing transfer integrity metadata")
    checksum = integrity.get("checksum")
    if not isinstance(checksum, str) or not _SHA256.fullmatch(checksum) or checksum != _checksum(document):
        raise TransferIntegrityError("transfer checksum mismatch")
    migrated = (registry or TransferMigrationRegistry()).migrate(document)
    _validate(migrated)
    expected = (scenario_id, scenario_version, build_version, campaign_schema)
    actual = (migrated["scenario"]["id"], migrated["scenario"]["version"],
              migrated["buildVersion"], migrated["campaignSchemaVersion"])
    if actual != expected:
        raise IncompatibleTransferError("transfer scenario, build, or campaign schema is incompatible")
    migrated["integrity"]["checksum"] = _checksum(migrated)
    return migrated


def _validate(document: Mapping[str, Any]) -> None:
    if document.get("format") != TRANSFER_FORMAT or document.get("schemaVersion") != CURRENT_TRANSFER_SCHEMA:
        raise IncompatibleTransferError("unsupported transfer format or schema")
    scenario = document.get("scenario")
    tokens = [document.get("buildVersion"), scenario.get("id") if isinstance(scenario, dict) else None,
              scenario.get("version") if isinstance(scenario, dict) else None]
    if any(not isinstance(x, str) or not _TOKEN.fullmatch(x) for x in tokens):
        raise TransferError("invalid scenario or build metadata")
    for name in ("sourceMapId", "destinationMapId"):
        if not isinstance(document.get(name), str) or not _ID.fullmatch(document[name]):
            raise TransferError(f"{name} is not a stable ID")
    schema = document.get("campaignSchemaVersion")
    if isinstance(schema, bool) or not isinstance(schema, int) or schema < 0:
        raise TransferError("invalid campaign schema version")
    transaction = document.get("transaction")
    if not isinstance(transaction, dict) or not isinstance(transaction.get("id"), str) or not transaction["id"]:
        raise TransferError("invalid transfer transaction metadata")
    sequence = transaction.get("sequence")
    if isinstance(sequence, bool) or not isinstance(sequence, int) or sequence < 1:
        raise TransferError("invalid transfer transaction sequence")
    if not isinstance(document.get("transition"), dict) or not isinstance(document.get("state"), dict) \
            or not isinstance(document.get("visitedMaps"), dict):
        raise TransferError("transition, state, and visitedMaps must be objects")
    _reject_transient(document["state"])
    _reject_transient(document["visitedMaps"], "visitedMaps")
    _reject_transient(document["transition"], "transition")


@dataclass(frozen=True)
class MapAssignment:
    id: str
    package_path: str
    logical_region_ids: tuple[str, ...]
    regional_instance_ids: tuple[str, ...]
    generated_terrain_ids: tuple[str, ...]

    @property
    def fingerprint(self) -> str:
        return hashlib.sha256(_canonical({"id": self.id, "packagePath": self.package_path,
            "logicalRegionIds": self.logical_region_ids, "regionalInstanceIds": self.regional_instance_ids,
            "generatedTerrainIds": self.generated_terrain_ids})).hexdigest()


class PhysicalMapManifest:
    """Minimal runtime view of scenario-owned physical-map configuration."""
    def __init__(self, raw: Mapping[str, Any]) -> None:
        if raw.get("format") != "warcraftmap_physical_maps_v1" or raw.get("formatVersion") != 1:
            raise DestinationContentError("unsupported physical-map manifest")
        entries = raw.get("physicalMaps")
        if not isinstance(entries, list):
            raise DestinationContentError("physical-map manifest has no map list")
        self.maps: dict[str, MapAssignment] = {}
        for item in entries:
            assignments = item.get("assignments", {}) if isinstance(item, dict) else {}
            map_id = item.get("id") if isinstance(item, dict) else None
            values = [assignments.get(k, []) for k in ("logicalRegionIds", "regionalInstanceIds", "generatedTerrainIds")]
            if not isinstance(map_id, str) or not _ID.fullmatch(map_id) or any(not isinstance(v, list) for v in values):
                raise DestinationContentError("invalid physical-map assignment")
            if map_id in self.maps:
                raise DestinationContentError("duplicate physical-map assignment")
            self.maps[map_id] = MapAssignment(map_id, str(item.get("packagePath", "")),
                                               *(tuple(sorted(v)) for v in values))

    def assignment(self, map_id: str) -> MapAssignment:
        try: return self.maps[map_id]
        except KeyError as exc: raise DestinationContentError(f"unknown destination map {map_id}") from exc

    def validate_content(self, map_id: str, content: Mapping[str, Any]) -> MapAssignment:
        assignment = self.assignment(map_id)
        physical = content.get("physicalMap")
        if not isinstance(physical, dict) or physical.get("id") != map_id:
            raise DestinationContentError(f"destination content does not identify {map_id}")
        actual = MapAssignment(map_id, assignment.package_path,
            tuple(sorted(physical.get("logicalRegionIds", []))),
            tuple(sorted(physical.get("regionalInstanceIds", []))),
            tuple(sorted(physical.get("generatedTerrainIds", assignment.generated_terrain_ids))))
        if actual.fingerprint != assignment.fingerprint:
            raise DestinationContentError(f"stale content assignment for {map_id}")
        return assignment


class TransferStorage(Protocol):
    def read_committed(self) -> bytes | None: ...
    def commit_transactional(self, payload: bytes) -> None: ...


class MemoryTransferStorage:
    def __init__(self) -> None:
        self._committed: bytes | None = None
        self.fail_next_commit = False
    def read_committed(self) -> bytes | None:
        return bytes(self._committed) if self._committed is not None else None
    def commit_transactional(self, payload: bytes) -> None:
        candidate = bytes(payload)
        if self.fail_next_commit:
            self.fail_next_commit = False
            raise TransferStorageError("interrupted transfer commit")
        self._committed = candidate


@dataclass(frozen=True)
class ReconstructionAdapter:
    name: str
    reconstruct: Callable[[Mapping[str, Any], Mapping[str, Any], MapAssignment], Any]
    priority: int = 100


@dataclass(frozen=True)
class TransferResult:
    transaction_id: str
    sequence: int
    source_map_id: str
    destination_map_id: str
    reconstructed: tuple[str, ...]


def _merge_defaults(authority: dict[str, Any], defaults: Mapping[str, Any]) -> None:
    """Add absent first-visit values recursively; authority always wins."""
    for key in sorted(defaults):
        value = defaults[key]
        if key not in authority:
            authority[key] = copy.deepcopy(value)
        elif isinstance(authority[key], dict) and isinstance(value, Mapping):
            _merge_defaults(authority[key], value)


class CrossMapTransferManager:
    """Two-phase coordinator: validate/rebuild, commit authority, then activate."""
    def __init__(self, *, scenario_id: str, scenario_version: str, build_version: str,
                 campaign_schema: int, manifest: PhysicalMapManifest, storage: TransferStorage,
                 capture_state: Callable[[], Mapping[str, Any]],
                 load_destination_content: Callable[[str], Mapping[str, Any]],
                 activate: Callable[[str, Mapping[str, Any], Mapping[str, Any]], None],
                 adapters: Sequence[ReconstructionAdapter],
                 first_visit_defaults: Callable[[str, Mapping[str, Any]], Mapping[str, Any]] | None = None,
                 save_manager: Any | None = None,
                 migration_registry: TransferMigrationRegistry | None = None) -> None:
        self.scenario_id, self.scenario_version = scenario_id, scenario_version
        self.build_version, self.campaign_schema = build_version, campaign_schema
        self.manifest, self.storage, self.capture_state = manifest, storage, capture_state
        self.load_destination_content, self.activate = load_destination_content, activate
        names = [adapter.name for adapter in adapters]
        if len(names) != len(set(names)):
            raise ValueError("duplicate reconstruction adapter name")
        self.adapters = tuple(sorted(adapters, key=lambda item: (item.priority, item.name)))
        self.first_visit_defaults = first_visit_defaults or (lambda _map, _content: {})
        self.save_manager, self.registry = save_manager, migration_registry or TransferMigrationRegistry()
        self.visited_maps: dict[str, Any] = {}
        self.sequence = 0
        self.in_progress = False

    @property
    def is_save_safe(self) -> bool: return not self.in_progress

    def transfer(self, source_map_id: str, destination_map_id: str,
                 transition: Mapping[str, Any], transaction_id: str) -> TransferResult:
        if self.in_progress: raise TransferError("a cross-map transfer is already in progress")
        self.manifest.assignment(source_map_id)
        self.in_progress = True
        try:
            authority = copy.deepcopy(dict(self.capture_state()))
            _reject_transient(authority)
            content = copy.deepcopy(dict(self.load_destination_content(destination_map_id)))
            assignment = self.manifest.validate_content(destination_map_id, content)
            if destination_map_id not in self.visited_maps:
                defaults = self.first_visit_defaults(destination_map_id, content)
                if not isinstance(defaults, Mapping): raise DestinationContentError("first-visit defaults must be an object")
                _reject_transient(defaults, "defaults")
                _merge_defaults(authority, defaults)
            next_visited = copy.deepcopy(self.visited_maps)
            next_visited[destination_map_id] = {"assignmentFingerprint": assignment.fingerprint,
                                                "firstSequence": self.sequence + 1}
            reconstructed: dict[str, Any] = {}
            try:
                for adapter in self.adapters:
                    reconstructed[adapter.name] = adapter.reconstruct(authority, content, assignment)
            except Exception as exc:
                raise ReconstructionError(f"reconstruction adapter failed: {exc}") from exc
            payload = serialize_transfer(scenario_id=self.scenario_id,
                scenario_version=self.scenario_version, build_version=self.build_version,
                campaign_schema=self.campaign_schema, source_map_id=source_map_id,
                destination_map_id=destination_map_id, transition=transition,
                transaction_id=transaction_id, sequence=self.sequence + 1,
                state=authority, visited_maps=next_visited)
            # Atomic storage promotion is the commit point.  No destination runtime
            # is activated before the outgoing authority is durable.
            self.storage.commit_transactional(payload)
            self.activate(destination_map_id, authority, reconstructed)
            self.sequence += 1
            self.visited_maps = next_visited
            return TransferResult(transaction_id, self.sequence, source_map_id, destination_map_id,
                                  tuple(reconstructed))
        finally:
            self.in_progress = False
            if self.save_manager is not None and getattr(self.save_manager, "has_deferred_save", False):
                self.save_manager.retry_deferred()

    def resume(self) -> tuple[dict[str, Any], str] | None:
        """Validate the last checkpoint for a load/bootstrap without activation."""
        raw = self.storage.read_committed()
        if raw is None: return None
        document = load_transfer(raw, scenario_id=self.scenario_id,
            scenario_version=self.scenario_version, build_version=self.build_version,
            campaign_schema=self.campaign_schema, registry=self.registry)
        destination = document["destinationMapId"]
        assignment = self.manifest.assignment(destination)
        visit = document["visitedMaps"].get(destination)
        if not isinstance(visit, dict) or visit.get("assignmentFingerprint") != assignment.fingerprint:
            raise DestinationContentError(f"stale committed assignment for {destination}")
        self.sequence = document["transaction"]["sequence"]
        self.visited_maps = copy.deepcopy(document["visitedMaps"])
        return copy.deepcopy(document["state"]), destination


# The campaign save schema registry is intentionally the shared authority for
# world-save evolution; importing its type here documents that integration.
CampaignSaveMigrationRegistry = MigrationRegistry
