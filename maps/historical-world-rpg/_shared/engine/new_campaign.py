"""Authoritative new-campaign player origin selection.

The selector is deliberately presentation-agnostic.  Warcraft UI and headless
tools consume the same sorted, searchable pages and the same validated result.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence


class OriginSelectionError(ValueError):
    """The requested origin cannot safely begin a campaign."""


@dataclass(frozen=True)
class OriginOption:
    polity_id: str
    name: str
    regional_instance_id: str


@dataclass(frozen=True)
class OriginPage:
    query: str
    page: int
    pages: int
    total: int
    options: tuple[OriginOption, ...]


class NewCampaignOrigins:
    """Validated view of the active 1450 polity and physical-map authority."""

    def __init__(self, polities: Iterable[Mapping[str, Any]],
                 settlements: Iterable[Mapping[str, Any]],
                 physical_maps: Mapping[str, Any] | Sequence[Mapping[str, Any]],
                 *, page_size: int = 10) -> None:
        if isinstance(page_size, bool) or not isinstance(page_size, int) or page_size < 1:
            raise OriginSelectionError("origin page size must be a positive integer")
        self.page_size = page_size
        self._polities = self._index(polities, "polity")
        self._settlements = self._index(settlements, "settlement")
        rows = physical_maps.get("physicalMaps") if isinstance(physical_maps, Mapping) else physical_maps
        if not isinstance(rows, Sequence):
            raise OriginSelectionError("physical-map authority must contain physicalMaps")
        self._map_for_instance: dict[str, str] = {}
        for row in rows:
            if not isinstance(row, Mapping) or not isinstance(row.get("id"), str):
                raise OriginSelectionError("physical-map authority contains an invalid map")
            assignments = row.get("assignments", row)
            for instance_id in assignments.get("regionalInstanceIds", ()):
                if instance_id in self._map_for_instance:
                    raise OriginSelectionError(f"regional instance {instance_id!r} has multiple physical maps")
                self._map_for_instance[instance_id] = row["id"]
        self._options = tuple(sorted((self._option(row) for row in self._polities.values()),
                                     key=lambda row: (row.name.casefold(), row.polity_id)))
        # Validate every offered option now; a broken catalogue must not become a
        # clickable country which silently lands somewhere else.
        for option in self._options:
            self.resolve_start(option.polity_id)

    @staticmethod
    def _index(rows: Iterable[Mapping[str, Any]], kind: str) -> dict[str, Mapping[str, Any]]:
        result: dict[str, Mapping[str, Any]] = {}
        for row in rows:
            stable_id = row.get("id") if isinstance(row, Mapping) else None
            if not isinstance(stable_id, str) or not stable_id or stable_id in result:
                raise OriginSelectionError(f"{kind} catalogue has a missing or duplicate stable ID")
            result[stable_id] = row
        return result

    def _option(self, polity: Mapping[str, Any]) -> OriginOption:
        name = polity.get("name")
        owned = sorted((row for row in self._settlements.values()
                        if row.get("legalOwnerPolityId") == polity["id"]), key=lambda row: row["id"])
        capital = next((row for row in owned if row["id"] == polity.get("capitalSettlementId")), None)
        instance = (capital or (owned[0] if owned else {})).get("regionalInstanceId")
        if not isinstance(name, str) or not name or not isinstance(instance, str) or not instance:
            raise OriginSelectionError(f"polity {polity['id']!r} lacks player-facing origin data")
        return OriginOption(polity["id"], name, instance)

    @property
    def options(self) -> tuple[OriginOption, ...]:
        return self._options

    def page(self, query: str = "", page: int = 1) -> OriginPage:
        if isinstance(page, bool) or not isinstance(page, int):
            raise OriginSelectionError("origin page must be an integer")
        normalized = " ".join(query.casefold().split())
        matches = tuple(row for row in self._options if normalized in row.name.casefold()
                        or normalized in row.polity_id.casefold())
        pages = max(1, (len(matches) + self.page_size - 1) // self.page_size)
        if page < 1 or page > pages:
            raise OriginSelectionError(f"origin page must be between 1 and {pages}")
        start = (page - 1) * self.page_size
        return OriginPage(normalized, page, pages, len(matches), matches[start:start + self.page_size])

    def resolve_start(self, polity_id: str) -> dict[str, str]:
        polity = self._polities.get(polity_id)
        if polity is None:
            raise OriginSelectionError(f"inactive or missing 1450 polity ID {polity_id!r}")
        owned = [row for row in self._settlements.values()
                 if row.get("legalOwnerPolityId") == polity_id]
        capital_id = polity.get("capitalSettlementId")
        candidates = [row for row in owned if row["id"] == capital_id]
        if not candidates:
            candidates = sorted(owned, key=lambda row: (row.get("kind") != "capital", row["id"]))
        if not candidates:
            raise OriginSelectionError(f"polity {polity_id!r} has no valid authored starting settlement")
        settlement = candidates[0]
        instance_id = settlement.get("regionalInstanceId") or polity.get("regionalInstanceId")
        map_id = self._map_for_instance.get(instance_id)
        if not map_id:
            raise OriginSelectionError(
                f"polity {polity_id!r} starting instance {instance_id!r} has no physical map")
        return {"physicalMapId": map_id, "regionalInstanceId": instance_id,
                "settlementId": settlement["id"]}

    def begin(self, polity_id: str, player_state: Mapping[str, Any] | None = None) -> dict[str, Any]:
        state = copy.deepcopy(dict(player_state or {}))
        if state.get("originPolityId") not in (None, ""):
            raise OriginSelectionError("player origin is immutable after campaign creation")
        state.update({"originPolityId": polity_id, "currentAllegiancePolityId": polity_id,
                      "startingLocation": self.resolve_start(polity_id),
                      "originSelectionComplete": True})
        return state

    def change_allegiance(self, player_state: Mapping[str, Any], polity_id: str) -> dict[str, Any]:
        if polity_id not in self._polities:
            raise OriginSelectionError(f"inactive or missing 1450 polity ID {polity_id!r}")
        state = copy.deepcopy(dict(player_state))
        origin = state.get("originPolityId")
        if origin not in self._polities:
            raise OriginSelectionError("player state has no valid immutable origin")
        state["currentAllegiancePolityId"] = polity_id
        return state

    def validate_player_state(self, player_state: Mapping[str, Any]) -> None:
        origin, allegiance = (player_state.get("originPolityId"),
                              player_state.get("currentAllegiancePolityId"))
        if origin not in self._polities or allegiance not in self._polities:
            raise OriginSelectionError("player origin or current allegiance is not an active 1450 polity")
        expected = self.resolve_start(origin)
        if player_state.get("startingLocation") != expected:
            raise OriginSelectionError("player starting location does not match authoritative origin data")
