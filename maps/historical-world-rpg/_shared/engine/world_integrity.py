"""Transactional integrity scans and reconstruction for persistent campaigns.

The scanner is deliberately data driven.  A scenario declares its authoritative
collections and references; only indexes and Warcraft-facing representations are
repairable.  Consequently an object-loss callback can never silently invent a
political, economic, quest, or military fact.
"""
from __future__ import annotations

import copy
import hashlib
import json
import re
import time
from dataclasses import dataclass
from typing import Any, Mapping, Protocol, Sequence

FORMAT = "warcraftmap_world_integrity_v1"
REPORT_FORMAT = "warcraftmap_world_recovery_report_v1"
STATE_SCHEMA_VERSION = 1
_ID = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")


class IntegrityError(ValueError):
    """An authoritative fact is corrupt and recovery was not attempted."""


class ReconstructionError(RuntimeError):
    """A runtime adapter failed; the input state remains unchanged."""


@dataclass(frozen=True)
class Reference:
    source: str
    field: str
    target: str
    optional: bool = False
    many: bool = False


@dataclass(frozen=True)
class FieldMatch:
    """Require a source field to match the same field on its referenced parent."""
    source: str
    reference_field: str
    target: str
    field: str


@dataclass(frozen=True)
class IntegrityPolicy:
    domains: tuple[str, ...]
    references: tuple[Reference, ...] = ()
    field_matches: tuple[FieldMatch, ...] = ()
    representation_domains: tuple[str, ...] = ()
    maximum_diagnostics: int = 32
    maximum_active_objects: int = 1024
    maximum_scan_ms: float = 1000.0


class ReconstructionAdapter(Protocol):
    def stage(self, stable_id: str, specification: Mapping[str, Any]) -> Any: ...
    def commit(self, staged: Sequence[Any]) -> Any: ...
    def rollback(self, staged: Sequence[Any]) -> None: ...


class RecordingReconstructionAdapter:
    """Headless all-or-nothing stand-in for map-local Warcraft objects."""
    def __init__(self):
        self.operations: list[tuple[Any, ...]] = []
        self.current: dict[str, Any] = {}
        self.fail_after: int | None = None

    def stage(self, stable_id, specification):
        if self.fail_after is not None and len([x for x in self.operations if x[0] == "stage"]) >= self.fail_after:
            raise ReconstructionError("injected interrupted reconstruction")
        value = {"stableId": stable_id, "specification": copy.deepcopy(dict(specification))}
        self.operations.append(("stage", stable_id))
        return value

    def commit(self, staged):
        replacement = {x["stableId"]: copy.deepcopy(x) for x in staged}
        self.current = replacement
        self.operations.append(("commit", tuple(sorted(replacement))))
        return replacement

    def rollback(self, staged):
        self.operations.append(("rollback", tuple(x["stableId"] for x in staged)))


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def state_hash(state: Mapping[str, Any], *, authoritative_only=False) -> str:
    value = state.get("authoritative") if authoritative_only else state
    return hashlib.sha256(canonical(value)).hexdigest()


def _diagnostic(kind, domain, stable_id, message):
    return {"kind": kind, "domain": domain, "stableId": stable_id, "message": message}


def _authoritative_indexes(state, policy):
    authority = state.get("authoritative")
    if not isinstance(authority, Mapping):
        raise IntegrityError("authoritative: expected object")
    indexes, diagnostics = {}, []
    for domain in policy.domains:
        values = authority.get(domain)
        if not isinstance(values, list):
            diagnostics.append(_diagnostic("invalid_collection", domain, domain, "expected array")); continue
        index = {}
        for value in values:
            ident = value.get("id") if isinstance(value, Mapping) else None
            if not isinstance(ident, str) or not _ID.fullmatch(ident):
                diagnostics.append(_diagnostic("invalid_stable_id", domain, str(ident), "invalid stable ID")); continue
            if ident in index:
                diagnostics.append(_diagnostic("duplicate", domain, ident, "duplicate authoritative ID")); continue
            index[ident] = value
        indexes[domain] = index
    for ref in policy.references:
        for ident, value in indexes.get(ref.source, {}).items():
            raw = value.get(ref.field)
            values = raw if ref.many and isinstance(raw, list) else [raw]
            if ref.many and not isinstance(raw, list):
                diagnostics.append(_diagnostic("invalid_reference", ref.source, ident, f"{ref.field} must be an array")); continue
            seen = set()
            for target in values:
                if target is None and ref.optional: continue
                if target in seen:
                    diagnostics.append(_diagnostic("duplicate_reference", ref.source, ident, f"duplicate {ref.field} {target!r}")); continue
                seen.add(target)
                if target not in indexes.get(ref.target, {}):
                    diagnostics.append(_diagnostic("orphan", ref.source, ident, f"{ref.field} references {target!r}"))
    for rule in policy.field_matches:
        for ident, value in indexes.get(rule.source, {}).items():
            target_id = value.get(rule.reference_field)
            target = indexes.get(rule.target, {}).get(target_id)
            if target is not None and value.get(rule.field) != target.get(rule.field):
                diagnostics.append(_diagnostic("contradictory_control", rule.source, ident,
                    f"{rule.field} contradicts {rule.target} {target_id!r}"))
    transactions = state.get("transactions", [])
    if not isinstance(transactions, list):
        diagnostics.append(_diagnostic("partial_transaction", "transactions", "transactions", "expected array"))
    else:
        txids = set()
        for tx in transactions:
            ident = tx.get("id") if isinstance(tx, Mapping) else None
            if ident in txids or not isinstance(ident, str) or tx.get("status") not in {"committed", "rolled_back"}:
                diagnostics.append(_diagnostic("partial_transaction", "transactions", str(ident), "transaction is duplicate or incomplete"))
            txids.add(ident)
    return indexes, sorted(diagnostics, key=lambda x: (x["domain"], x["stableId"], x["kind"]))


def _derived(indexes):
    return {domain: {ident: offset for offset, ident in enumerate(sorted(index))}
            for domain, index in sorted(indexes.items())}


def _specifications(indexes, policy):
    result = []
    for domain in policy.representation_domains:
        for ident, value in sorted(indexes.get(domain, {}).items()):
            result.append((ident, {"domain": domain, "authoritative": copy.deepcopy(value)}))
    return result


def scan(state: Mapping[str, Any], policy: IntegrityPolicy) -> dict[str, Any]:
    started = time.perf_counter()
    indexes, fatal = _authoritative_indexes(state, policy)
    repairable = []
    expected_indexes = _derived(indexes)
    if state.get("indexes") != expected_indexes:
        repairable.append(_diagnostic("stale_index", "indexes", "persistence_indexes", "rebuild required"))
    specifications = dict(_specifications(indexes, policy))
    expected_ids = set(specifications)
    runtime = state.get("runtimeRepresentations")
    actual_ids = set(runtime) if isinstance(runtime, Mapping) else set()
    for ident in sorted(expected_ids - actual_ids):
        repairable.append(_diagnostic("missing_representation", "runtime", ident, "reconstruction required"))
    for ident in sorted(actual_ids - expected_ids):
        repairable.append(_diagnostic("stale_representation", "runtime", ident, "removal required"))
    if isinstance(runtime, Mapping):
        for ident in sorted(expected_ids & actual_ids):
            value = runtime[ident]
            if not isinstance(value, Mapping) or value.get("stableId") != ident or value.get("specification") != specifications[ident]:
                repairable.append(_diagnostic("damaged_representation", "runtime", ident, "reconstruction required"))
    if len(expected_ids) > policy.maximum_active_objects:
        fatal.append(_diagnostic("active_object_budget", "runtime", "active_objects", f"{len(expected_ids)} exceeds {policy.maximum_active_objects}"))
    elapsed = (time.perf_counter() - started) * 1000
    if elapsed > policy.maximum_scan_ms:
        fatal.append(_diagnostic("scan_budget", "scan", "elapsed_ms", f"{elapsed:.3f} exceeds {policy.maximum_scan_ms:.3f}"))
    all_diagnostics = (fatal + repairable)[:policy.maximum_diagnostics]
    return {"format": REPORT_FORMAT, "authoritativeHash": state_hash(state, authoritative_only=True),
            "fatalCount": len(fatal), "repairableCount": len(repairable),
            "diagnostics": all_diagnostics, "diagnosticsTruncated": len(fatal) + len(repairable) > len(all_diagnostics),
            "scanMilliseconds": round(elapsed, 3), "activeObjectCount": len(expected_ids)}


def recover(state: Mapping[str, Any], policy: IntegrityPolicy, adapter: ReconstructionAdapter):
    """Return a recovered copy.  Authority and caller input are never mutated."""
    before = copy.deepcopy(dict(state))
    indexes, fatal = _authoritative_indexes(before, policy)
    if fatal:
        report = scan(before, policy)
        first = report["diagnostics"][0]
        raise IntegrityError(f"{first['kind']}:{first['domain']}:{first['stableId']}: {first['message']}")
    if len(_specifications(indexes, policy)) > policy.maximum_active_objects:
        raise IntegrityError("active object budget exceeded")
    staged = []
    try:
        for ident, specification in _specifications(indexes, policy):
            staged.append(adapter.stage(ident, specification))
        runtime = adapter.commit(staged)
    except Exception as error:
        adapter.rollback(staged)
        raise ReconstructionError(str(error)) from error
    recovered = copy.deepcopy(before)
    recovered["format"] = FORMAT
    recovered["schemaVersion"] = STATE_SCHEMA_VERSION
    recovered["indexes"] = _derived(indexes)
    recovered["runtimeRepresentations"] = copy.deepcopy(runtime)
    recovered["reconstruction"] = {"status": "complete", "authoritativeHash": state_hash(before, authoritative_only=True)}
    report = scan(recovered, policy)
    if report["fatalCount"] or report["repairableCount"]:
        raise ReconstructionError("post-reconstruction integrity scan failed")
    return recovered, report
