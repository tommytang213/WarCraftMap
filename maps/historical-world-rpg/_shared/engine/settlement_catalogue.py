"""Reusable validation and deterministic authoring helpers for settlement catalogues."""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections import Counter
from typing import Any, Iterable, Mapping

ID = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")
PORT_TERRAINS = {"coast", "riverbank", "island", "delta", "wetland"}
CONTRADICTORY_ROLES = ({"inland", "major_port"}, {"inland", "anchorage"})

class CatalogueError(ValueError): pass

def stable_id(name: str, occupied: Iterable[str] = ()) -> str:
    """Return a repeatable ASCII ID; resolve collisions from the original name digest."""
    text = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower()
    base = re.sub(r"[^a-z0-9]+", "_", text).strip("_") or "settlement"
    if not base[0].isalpha(): base = "settlement_" + base
    used = set(occupied)
    if base not in used: return base
    suffix = hashlib.sha256(name.encode("utf-8")).hexdigest()[:8]
    candidate = f"{base}_{suffix}"
    serial = 2
    while candidate in used:
        candidate = f"{base}_{suffix}_{serial}"; serial += 1
    return candidate

def project_lon_lat(longitude: float, latitude: float, bounds: Mapping[str, float]) -> dict[str, float]:
    """Equirectangular deterministic projection into declared map bounds."""
    if not (-180 <= longitude <= 180 and -90 <= latitude <= 90): raise CatalogueError("invalid real-world coordinates")
    required = ("minX", "maxX", "minY", "maxY")
    if any(k not in bounds for k in required): raise CatalogueError("projection bounds are incomplete")
    return {"x": round(bounds["minX"] + (longitude + 180) / 360 * (bounds["maxX"]-bounds["minX"]), 6),
            "y": round(bounds["minY"] + (latitude + 90) / 180 * (bounds["maxY"]-bounds["minY"]), 6)}

def normalized(record: Mapping[str, Any]) -> dict[str, Any]:
    return json.loads(json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":")))

def validate_catalogue(records: Iterable[Mapping[str, Any]], refs: Mapping[str, set[str]]) -> list[dict[str, Any]]:
    rows = [normalized(r) for r in records]; seen=set()
    for row in rows:
        sid=row.get("id")
        if not isinstance(sid,str) or not ID.fullmatch(sid): raise CatalogueError(f"invalid settlement ID {sid!r}")
        if sid in seen: raise CatalogueError(f"duplicate settlement ID {sid!r}")
        seen.add(sid)
        for field, refkey in (("regionId","regions"),("polityId","polities"),("provinceId","provinces"),("controllerPolityId","polities")):
            if row.get(field) not in refs.get(refkey,set()): raise CatalogueError(f"{sid}: unknown {field} {row.get(field)!r}")
        owners=refs.get("provinceOwners",{})
        if owners and owners.get(row["provinceId"]) != row["polityId"]: raise CatalogueError(f"{sid}: unsupported ownership/control context")
        rep=row.get("representation")
        if rep not in {"physical","abstract_minor"}: raise CatalogueError(f"{sid}: invalid representation")
        if rep=="physical" and row.get("physicalMapId") not in refs.get("maps",set()): raise CatalogueError(f"{sid}: unknown physical map")
        if rep=="abstract_minor" and not row.get("compressionRationale"): raise CatalogueError(f"{sid}: abstract community requires compression rationale")
        p=row.get("placement",{}); basis=p.get("basis")
        if basis not in {"longitude_latitude","regional_map","regional_centroid"}: raise CatalogueError(f"{sid}: invalid placement basis")
        if basis=="longitude_latitude" and not (-180<=p.get("x",999)<=180 and -90<=p.get("y",999)<=90): raise CatalogueError(f"{sid}: invalid coordinates")
        if basis=="regional_map":
            # Regional sources may use a pre-projection authoring canvas larger
            # than the eventual local terrain bounds. Projection validates the
            # final point; this contract rejects nonsensical source coordinates.
            bounds={"minX":-360,"minY":-180,"maxX":360,"maxY":180}
            if not (bounds["minX"]<=p.get("x",-1)<=bounds["maxX"] and bounds["minY"]<=p.get("y",-1)<=bounds["maxY"]): raise CatalogueError(f"{sid}: invalid coordinates")
        if basis=="regional_centroid" and rep!="abstract_minor": raise CatalogueError(f"{sid}: centroid placement is only valid for abstract communities")
        if p.get("terrainClass") not in refs.get("terrain",set()): raise CatalogueError(f"{sid}: unknown terrain reference")
        if p.get("navigationZoneId") not in refs.get("navigation",set()): raise CatalogueError(f"{sid}: unknown navigation reference")
        roles=set(row.get("roles",[]))
        if any(pair<=roles for pair in CONTRADICTORY_ROLES): raise CatalogueError(f"{sid}: contradictory roles")
        port=row.get("port")
        if port and (p.get("terrainClass") not in PORT_TERRAINS or port.get("navigationZoneId") not in refs.get("navigation",set())): raise CatalogueError(f"{sid}: invalid port")
        if "major_port" in roles and not port: raise CatalogueError(f"{sid}: port role lacks port metadata")
        if any(route not in refs.get("routes",set()) for route in row.get("routeIds",[])): raise CatalogueError(f"{sid}: unknown route reference")
        if not row.get("evidence") or not {e.get("claim") for e in row["evidence"]}>={"identity","ownership","placement","importance"}: raise CatalogueError(f"{sid}: missing evidence")
    return sorted(rows,key=lambda r:r["id"])

def grouped_counts(rows: Iterable[Mapping[str,Any]], field: str) -> dict[str,int]:
    return dict(sorted(Counter(str(r.get(field,"unassigned")) for r in rows).items()))
