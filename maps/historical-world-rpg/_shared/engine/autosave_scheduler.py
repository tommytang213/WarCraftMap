"""Deterministic rolling autosave scheduling for campaign runtimes."""
from __future__ import annotations
from dataclasses import dataclass
from math import isfinite
from typing import Any, Mapping
from campaign_save import AUTOSAVE_SLOT_COUNT, CampaignSaveManager, SaveError, SaveSlot

SCHEDULER_METADATA_VERSION = 1

@dataclass(frozen=True)
class AutosaveAttempt:
    status: str
    slot_id: str
    diagnostic: str = ""

class RollingAutosaveScheduler:
    """Schedule fifteen rolling slots without owning clocks or Warcraft objects."""
    def __init__(self, manager: CampaignSaveManager, interval: float, *, now: float = 0) -> None:
        if isinstance(interval, bool) or not isinstance(interval, (int, float)) or not isfinite(interval) or interval <= 0:
            raise ValueError("autosave interval must be positive")
        self.manager = manager
        self.interval = float(interval)
        self.next_slot = 1
        self.next_due = float(now) + self.interval
        self._in_progress = False
        self._pending = False
        self._intended_created_at: str | None = None
        self.last_diagnostic = ""

    def tick(self, now: float, created_at: str) -> AutosaveAttempt | None:
        if float(now) < self.next_due and not self._pending and self._intended_created_at is None:
            return None
        return self.request(now, created_at)

    def request(self, now: float, created_at: str) -> AutosaveAttempt:
        slot = SaveSlot("autosave", self.next_slot)
        if self._in_progress:
            self._pending = True
            return AutosaveAttempt("coalesced", slot.stable_id, "autosave already in progress")
        self._in_progress = True
        try:
            if self._intended_created_at is None:
                self._intended_created_at = created_at
            try:
                result = self.manager.save(slot, self._intended_created_at)
            except SaveError as exc:
                self.last_diagnostic = str(exc)
                return AutosaveAttempt("failed", slot.stable_id, self.last_diagnostic)
            if result is None:
                self.last_diagnostic = "deferred autosave disappeared before retry"
                return AutosaveAttempt("failed", slot.stable_id, self.last_diagnostic)
            if not result.succeeded:
                self.last_diagnostic = result.diagnostic
                return AutosaveAttempt(result.status, slot.stable_id, result.diagnostic)
            completed = slot.stable_id
            self.next_slot = self.next_slot % AUTOSAVE_SLOT_COUNT + 1
            self.next_due = float(now) + self.interval
            self._pending = False
            self._intended_created_at = None
            self.last_diagnostic = ""
            return AutosaveAttempt("saved", completed)
        finally:
            self._in_progress = False

    def metadata(self, now: float) -> dict[str, Any]:
        return {"version": SCHEDULER_METADATA_VERSION, "nextSlotIndex": self.next_slot,
                "secondsUntilDue": max(0.0, self.next_due - float(now))}

    def resume_after_load(self, metadata: Mapping[str, Any] | None, *, now: float) -> None:
        """Restore v1 metadata or migrate v0 last-completed-slot representation."""
        next_slot = 1
        remaining = self.interval
        if metadata is not None:
            version = metadata.get("version", 0)
            if isinstance(version, bool) or not isinstance(version, int):
                raise ValueError("invalid autosave scheduler metadata version")
            if version == 0:
                last = metadata.get("lastCompletedSlot", 0)
                if isinstance(last, bool) or not isinstance(last, int) or not 0 <= last <= AUTOSAVE_SLOT_COUNT:
                    raise ValueError("invalid migrated autosave slot metadata")
                next_slot = last % AUTOSAVE_SLOT_COUNT + 1
            elif version == SCHEDULER_METADATA_VERSION:
                next_slot = metadata.get("nextSlotIndex")
                if isinstance(next_slot, bool) or not isinstance(next_slot, int) or not 1 <= next_slot <= AUTOSAVE_SLOT_COUNT:
                    raise ValueError("invalid autosave next-slot metadata")
            else:
                raise ValueError(f"unsupported autosave scheduler metadata version {version}")
            remaining = metadata.get("secondsUntilDue", self.interval)
            if isinstance(remaining, bool) or not isinstance(remaining, (int, float)) or not isfinite(remaining) or remaining < 0:
                raise ValueError("invalid autosave remaining-time metadata")
        self.next_slot = next_slot
        self.next_due = float(now) + float(remaining)
        self._pending = self._in_progress = False
        self._intended_created_at = None
        self.last_diagnostic = ""
