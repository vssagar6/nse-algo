"""Conservative entry quota for completed 5-minute bars.

This module does not submit orders or generate trading signals. The caller must
invoke ``reserve_entry`` only for a new opening order after its own signal and
risk checks. Risk-reducing exits do not use this entry quota.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from threading import Lock
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")
SESSION_OPEN = time(9, 15)


@dataclass
class EntryState:
    """Mutable counters for one process; not durable or multi-worker safe."""

    trading_date: date | None = None
    morning_entries: int = 0
    afternoon_entries: int = 0
    last_entry_bar: datetime | None = None


@dataclass(frozen=True)
class EntryDecision:
    allowed: bool
    reason: str


class EntryPolicy:
    """Enforce daily time-window and per-bar limits for new entries.

    ``bar_close_time`` must be a timezone-aware timestamp for a completed
    5-minute bar close. NSE regular-session bars are aligned from 09:15 IST.
    Counts reset automatically when the local calendar date changes. Exchange
    holidays are not checked; callers must supply valid session bars.
    """

    def __init__(
        self,
        *,
        morning_limit: int = 2,
        afternoon_limit: int = 2,
        bar_minutes: int = 5,
        morning_start: time = time(10, 0),
        afternoon_start: time = time(13, 0),
        market_close: time = time(15, 30),
    ) -> None:
        if morning_limit < 0 or afternoon_limit < 0:
            raise ValueError("Entry limits cannot be negative")
        if bar_minutes != 5:
            raise ValueError("This policy is defined for 5-minute bars")
        if not morning_start < afternoon_start < market_close:
            raise ValueError("Expected morning_start < afternoon_start < market_close")
        self.morning_limit = morning_limit
        self.afternoon_limit = afternoon_limit
        self.bar_minutes = bar_minutes
        self.morning_start = morning_start
        self.afternoon_start = afternoon_start
        self.market_close = market_close
        self.state = EntryState()
        self._lock = Lock()

    @staticmethod
    def _to_ist(value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("bar_close_time must be timezone-aware")
        return value.astimezone(IST)

    def _bar_id(self, local_time: datetime) -> datetime | None:
        """Return the start time of the bar ending at local_time, if aligned."""
        session_start = datetime.combine(local_time.date(), SESSION_OPEN, tzinfo=IST)
        elapsed_seconds = (local_time - session_start).total_seconds()
        interval = self.bar_minutes * 60
        if elapsed_seconds <= 0 or elapsed_seconds % interval != 0:
            return None
        return local_time - timedelta(seconds=interval)

    def reserve_entry(self, bar_close_time: datetime) -> EntryDecision:
        """Atomically check and consume quota for one new opening order.

        Reserve immediately before a single order-submission attempt. A
        reservation is not refunded after a failed/uncertain submission; check
        broker order status before considering any retry. Repeated calls for
        the same bar are rejected.
        """
        local = self._to_ist(bar_close_time)
        local_clock = local.time().replace(tzinfo=None)
        bar_id = self._bar_id(local)
        if bar_id is None:
            return EntryDecision(False, "Timestamp is not a completed 5-minute NSE-session bar close")
        if local_clock < self.morning_start:
            return EntryDecision(False, "No new entries before 10:00 IST")
        if local_clock >= self.market_close:
            return EntryDecision(False, "No new entries at or after 15:30 IST")

        with self._lock:
            if self.state.trading_date != local.date():
                self.state = EntryState(trading_date=local.date())

            if self.state.last_entry_bar == bar_id:
                return EntryDecision(False, "One new entry maximum per 5-minute bar")

            if local_clock < self.afternoon_start:
                if self.state.morning_entries >= self.morning_limit:
                    return EntryDecision(False, "Morning entry limit reached")
                self.state.morning_entries += 1
            else:
                if self.state.afternoon_entries >= self.afternoon_limit:
                    return EntryDecision(False, "Afternoon entry limit reached")
                self.state.afternoon_entries += 1

            self.state.last_entry_bar = bar_id
            return EntryDecision(True, "Entry quota reserved")
