"""Scenario-neutral remote regional command and management.

Campaign state remains authoritative.  This coordinator only changes the set of
transient local representations and the camera/control context; it never moves a
strategic entity.  The selected management view is deliberately not serialized.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Protocol


class RegionManagementError(ValueError):
    pass


class UnknownRegion(RegionManagementError):
    pass


class RegionNotKnown(RegionManagementError):
    pass


class RegionNotAuthorized(RegionManagementError):
    pass


class ActiveObjectBudgetExceeded(RegionManagementError):
    pass


class RegionRuntimeAdapter(Protocol):
    """Warcraft boundary; snapshots must include all transient handles/camera state."""

    def snapshot(self) -> Any: ...
    def restore(self, snapshot: Any) -> None: ...
    def retire_region(self, region_id: str) -> None: ...
    def reconstruct_region(self, region_id: str, entities: Mapping[str, Mapping[str, Any]]) -> None: ...
    def focus_region(self, region_id: str) -> None: ...


class ModalPauseController(Protocol):
    def open_modal_management_screen(self) -> Any: ...


@dataclass(frozen=True)
class RegionSelection:
    physical_region_id: str
    command_region_id: str
    remote: bool
    represented_entity_ids: tuple[str, ...]


def _close(token: Any) -> None:
    if token is not None:
        token.close()


class RegionManagement:
    """Transactional command-region selector over generic authoritative state.

    ``state`` is expected to contain ``physicalRegionId`` and an ``entities``
    mapping.  Entity records use a ``regionId`` and may opt into a local
    representation with ``locallyRelevant``.  Access is supplied by callbacks so
    scenario ownership, delegation, and campaign knowledge remain authoritative.
    """

    def __init__(
        self,
        region_ids: list[str] | tuple[str, ...] | set[str],
        state: Mapping[str, Any],
        runtime: RegionRuntimeAdapter,
        pause: ModalPauseController,
        *,
        knows_region: Callable[[str], bool],
        may_command_region: Callable[[str], bool],
        may_control_entity: Callable[[str, Mapping[str, Any]], bool] | None = None,
        active_object_budget: int = 256,
    ) -> None:
        self._regions = frozenset(region_ids)
        self.state = copy.deepcopy(dict(state))
        self.runtime = runtime
        self.pause = pause
        self.knows_region = knows_region
        self.may_command_region = may_command_region
        self.may_control_entity = may_control_entity or (lambda _id, entity: bool(entity.get("playerControllable")))
        if not self._regions:
            raise RegionManagementError("at least one region is required")
        if isinstance(active_object_budget, bool) or not isinstance(active_object_budget, int) or active_object_budget < 1:
            raise RegionManagementError("active object budget must be a positive integer")
        self.active_object_budget = active_object_budget
        physical = self.state.get("physicalRegionId")
        if physical not in self._regions:
            raise RegionManagementError("physical region is missing")
        if not isinstance(self.state.get("entities"), Mapping):
            raise RegionManagementError("entities must be an object")
        # UI state is reconstructed on load and is intentionally absent from state.
        self._command_region_id = physical
        self._modal_token: Any = None
        self._represented_entity_ids: tuple[str, ...] = ()

    @property
    def physical_region_id(self) -> str:
        return self.state["physicalRegionId"]

    @property
    def command_region_id(self) -> str:
        return self._command_region_id

    @property
    def is_remote(self) -> bool:
        return self.command_region_id != self.physical_region_id

    def _eligible(self, region_id: str) -> dict[str, Mapping[str, Any]]:
        selected: dict[str, Mapping[str, Any]] = {}
        object_count = 0
        for entity_id in sorted(self.state["entities"]):
            entity = self.state["entities"][entity_id]
            if not isinstance(entity, Mapping) or entity.get("regionId") != region_id:
                continue
            if not entity.get("locallyRelevant", True) or not self.may_control_entity(entity_id, entity):
                continue
            count = entity.get("activeObjectCount", 1)
            if isinstance(count, bool) or not isinstance(count, int) or count < 0:
                raise RegionManagementError(f"entity {entity_id}: invalid active object count")
            object_count += count
            selected[entity_id] = copy.deepcopy(dict(entity))
        if object_count > self.active_object_budget:
            raise ActiveObjectBudgetExceeded(
                f"Region {region_id} requires {object_count} active objects; budget is {self.active_object_budget}."
            )
        return selected

    def _check_access(self, region_id: str) -> None:
        if region_id not in self._regions:
            raise UnknownRegion(f"Unknown region: {region_id}.")
        # Knowledge is checked before authorization to avoid leaking ownership or
        # other hidden state for an undiscovered region.
        if not self.knows_region(region_id):
            raise RegionNotKnown(f"Region is not known: {region_id}.")
        if region_id != self.physical_region_id and not self.may_command_region(region_id):
            raise RegionNotAuthorized(f"You are not authorized to manage region: {region_id}.")

    def select(self, region_id: str) -> RegionSelection:
        """Atomically activate an authorized command region without moving entities."""
        self._check_access(region_id)
        if region_id == self.command_region_id:
            return self.selection()
        entities = self._eligible(region_id)
        previous_runtime = self.runtime.snapshot()
        previous_region = self._command_region_id
        previous_ids = self._represented_entity_ids
        new_token = None
        try:
            if self._modal_token is None and region_id != self.physical_region_id:
                new_token = self.pause.open_modal_management_screen()
            self.runtime.retire_region(previous_region)
            self.runtime.reconstruct_region(region_id, entities)
            self.runtime.focus_region(region_id)
            self._command_region_id = region_id
            self._represented_entity_ids = tuple(entities)
            if new_token is not None:
                self._modal_token = new_token
            if region_id == self.physical_region_id and self._modal_token is not None:
                token, self._modal_token = self._modal_token, None
                _close(token)
            return self.selection()
        except Exception:
            self.runtime.restore(previous_runtime)
            self._command_region_id = previous_region
            self._represented_entity_ids = previous_ids
            _close(new_token)
            raise

    def return_to_physical_region(self) -> RegionSelection:
        return self.select(self.physical_region_id)

    def selection(self) -> RegionSelection:
        return RegionSelection(
            self.physical_region_id,
            self.command_region_id,
            self.is_remote,
            self._represented_entity_ids,
        )

    def set_physical_region(self, region_id: str) -> None:
        """Travel integration hook; callers move strategic entities separately."""
        if region_id not in self._regions:
            raise UnknownRegion(f"Unknown region: {region_id}.")
        self.state["physicalRegionId"] = region_id
        if self._modal_token is None:
            self._command_region_id = region_id

    def issue_order(self, entity_id: str, order: Mapping[str, Any]) -> None:
        """Persist an order through generic authoritative entity state."""
        entity = self.state["entities"].get(entity_id)
        if not isinstance(entity, dict) or entity.get("regionId") != self.command_region_id:
            raise RegionManagementError("Entity is not in the active command region.")
        if not self.may_control_entity(entity_id, entity):
            raise RegionNotAuthorized("You are not authorized to command that entity.")
        if not isinstance(order, Mapping) or not order:
            raise RegionManagementError("Order must be a non-empty object.")
        entity["order"] = copy.deepcopy(dict(order))

    def operate_holding(self, entity_id: str, operation: Mapping[str, Any]) -> None:
        self.issue_order(entity_id, operation)

    def simulate_inactive(self, days: int, step: Callable[[dict[str, Any], str, int], None]) -> None:
        if isinstance(days, bool) or not isinstance(days, int) or days < 0:
            raise RegionManagementError("days must be a non-negative integer")
        for region_id in sorted(self._regions):
            if region_id != self.command_region_id:
                step(self.state, region_id, days)

    def export_authoritative_state(self) -> dict[str, Any]:
        """Return save state without the reconstructible command/view selection."""
        return copy.deepcopy(self.state)

    def close(self) -> RegionSelection:
        return self.return_to_physical_region()


def parse_region_command(arguments: str) -> tuple[str, str | None]:
    """Parse ``/region <id>`` and ``/region return`` command arguments."""
    normalized = " ".join(arguments.split())
    if not normalized:
        return "error", "Usage: /region <region-id|return>"
    if " " in normalized:
        return "error", "Usage: /region <region-id|return>"
    if normalized.casefold() in {"return", "physical", "home"}:
        return "return", None
    return "select", normalized.casefold()


def execute_region_command(manager: RegionManagement, arguments: str) -> str:
    action, value = parse_region_command(arguments)
    if action == "error":
        return value or "Usage: /region <region-id|return>"
    try:
        selection = manager.return_to_physical_region() if action == "return" else manager.select(value or "")
    except RegionManagementError as exc:
        return str(exc)
    if selection.remote:
        return f"Managing {selection.command_region_id}. Your party remains in {selection.physical_region_id}."
    return f"Returned command view to {selection.physical_region_id}. No strategic entity was moved."
