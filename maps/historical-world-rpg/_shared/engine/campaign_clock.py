"""Authoritative, scenario-neutral campaign clock.

The clock owns calendar/schedule state. Platform timers are deliberately only
wake-up sources: destroying one cannot change or erase campaign time.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass
from datetime import timedelta
from typing import Callable, Mapping, Protocol

import timeline

CLOCK_STATE_VERSION = 1
SYSTEM_ORDER = ("technology", "economy", "diplomacy", "quests", "events")

class ClockError(ValueError): pass

class TimerAdapter(Protocol):
    def start(self, interval_seconds: float, callback: Callable[[float], None]) -> None: ...
    def stop(self) -> None: ...

@dataclass(frozen=True)
class CampaignTime:
    iso_date: str
    year: int
    month: int
    day: int
    era_id: str | None

EventListener = Callable[[timeline.EventOccurrence], None]

class CampaignClock:
    """Deterministic calendar scheduler shared by all campaign systems."""
    def __init__(self, definition: Mapping, *, days_per_second: float = 1.0):
        self._definition = timeline.validate_definition(definition)
        if isinstance(days_per_second, bool) or not isinstance(days_per_second, (int, float)) or days_per_second <= 0:
            raise ClockError("days_per_second must be positive")
        self._days_per_second = float(days_per_second)
        self._speed = 1.0
        self._elapsed_days = 0.0
        self._state = timeline.initial_state(self._definition)
        self._paused = False
        self._listeners = {name: [] for name in SYSTEM_ORDER}
        self._timer: TimerAdapter | None = None
        self._advancing = False
        self._last_diagnostic = ""

    @property
    def diagnostic(self) -> str: return self._last_diagnostic

    def time(self) -> CampaignTime:
        value = timeline.parse_date(self._state["currentDate"])
        return CampaignTime(value.isoformat(), value.year, value.month, value.day,
                            timeline.active_era(self._definition, value.isoformat()))

    def state(self) -> dict:
        return {"clockStateVersion": CLOCK_STATE_VERSION, "timeline": copy.deepcopy(self._state),
                "elapsedDays": self._elapsed_days, "speed": self._speed}

    def restore(self, candidate: Mapping) -> None:
        """Validate completely before atomically replacing authoritative state."""
        if not isinstance(candidate, Mapping) or candidate.get("clockStateVersion") != CLOCK_STATE_VERSION:
            raise ClockError(f"clock state must use version {CLOCK_STATE_VERSION}")
        new_state = copy.deepcopy(candidate.get("timeline"))
        timeline.validate_state(self._definition, new_state)
        elapsed, speed = candidate.get("elapsedDays"), candidate.get("speed")
        if isinstance(elapsed, bool) or not isinstance(elapsed, (int, float)) or not 0 <= elapsed < 1:
            raise ClockError("elapsedDays must be between zero (inclusive) and one (exclusive)")
        if isinstance(speed, bool) or not isinstance(speed, (int, float)) or speed <= 0:
            raise ClockError("speed must be positive")
        self._state, self._elapsed_days, self._speed = new_state, float(elapsed), float(speed)
        self._last_diagnostic = ""

    def subscribe(self, system: str, listener: EventListener) -> None:
        if system not in self._listeners: raise ClockError(f"unknown campaign system {system!r}")
        self._listeners[system].append(listener)

    def set_paused(self, paused: bool) -> None: self._paused = bool(paused)
    def is_paused(self) -> bool: return self._paused

    def set_speed(self, multiplier: float) -> bool:
        if isinstance(multiplier, bool) or not isinstance(multiplier, (int, float)) or multiplier <= 0:
            self._last_diagnostic = "campaign speed must be positive"; return False
        self._speed = float(multiplier); self._last_diagnostic = ""; return True

    def advance_elapsed(self, elapsed_seconds: float) -> tuple[timeline.EventOccurrence, ...]:
        if isinstance(elapsed_seconds, bool) or not isinstance(elapsed_seconds, (int, float)) or elapsed_seconds < 0:
            self._last_diagnostic = "elapsed seconds must be non-negative"; return ()
        if self._paused or elapsed_seconds == 0: return ()
        total = self._elapsed_days + float(elapsed_seconds) * self._days_per_second * self._speed
        whole_days = int(total)
        if whole_days == 0: self._elapsed_days = total; return ()
        target = timeline.parse_date(self._state["currentDate"]) + timedelta(days=whole_days)
        end = timeline.parse_date(self._definition["endDate"])
        if target > end: target = end
        events = self.advance_to(target.isoformat())
        self._elapsed_days = 0.0 if timeline.parse_date(self._state["currentDate"]) == end else total - whole_days
        return events

    def advance_to(self, target_date: str) -> tuple[timeline.EventOccurrence, ...]:
        """Advance atomically and deliver all due events in canonical order."""
        if self._advancing:
            self._last_diagnostic = "campaign clock advancement is already in progress"; return ()
        try: new_state, events = timeline.advance(self._definition, self._state, target_date)
        except (timeline.TimelineError, TypeError) as error:
            self._last_diagnostic = str(error); return ()
        self._advancing = True
        try:
            self._state = new_state
            for event in events:
                for system in SYSTEM_ORDER:
                    for listener in tuple(self._listeners[system]): listener(event)
        finally: self._advancing = False
        self._last_diagnostic = ""; return events

    def attach_timer(self, adapter: TimerAdapter, interval_seconds: float = 1.0) -> None:
        if interval_seconds <= 0: raise ClockError("timer interval must be positive")
        self.detach_timer(); self._timer = adapter; adapter.start(interval_seconds, self.advance_elapsed)

    def detach_timer(self) -> None:
        if self._timer is not None: self._timer.stop(); self._timer = None
