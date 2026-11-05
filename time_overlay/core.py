# SPDX-License-Identifier: GPL-3.0-or-later
"""Time-keeping state machines and display formatting.

The state machines are deliberately free of Qt imports so that they can be
unit-tested with an injected monotonic clock.
"""

from __future__ import annotations

import math
import time
from collections.abc import Callable
from datetime import datetime

Clock = Callable[[], float]


class Stopwatch:
    """A pauseable stopwatch backed by a monotonic clock."""

    def __init__(self, clock: Clock = time.perf_counter) -> None:
        self._clock = clock
        self._accumulated = 0.0
        self._started_at: float | None = None

    @property
    def running(self) -> bool:
        return self._started_at is not None

    def start(self) -> None:
        if self._started_at is None:
            self._started_at = self._clock()

    def pause(self) -> None:
        if self._started_at is not None:
            self._accumulated += max(0.0, self._clock() - self._started_at)
            self._started_at = None

    def toggle(self) -> None:
        if self.running:
            self.pause()
        else:
            self.start()

    def reset(self) -> None:
        self._accumulated = 0.0
        self._started_at = None

    def add_seconds(self, seconds: float) -> None:
        """Add time to the elapsed value without changing the running state."""
        self._accumulated = max(0.0, self._accumulated + seconds)

    def set_elapsed(self, seconds: float) -> None:
        """Set the elapsed value, preserving whether the stopwatch is running."""
        seconds = max(0.0, seconds)
        if self.running:
            self._started_at = self._clock()
        self._accumulated = seconds

    def elapsed(self) -> float:
        if self._started_at is None:
            return self._accumulated
        return self._accumulated + max(0.0, self._clock() - self._started_at)


class CountdownTimer:
    """A pauseable countdown timer backed by a monotonic clock."""

    def __init__(
        self,
        duration: float = 300.0,
        clock: Clock = time.perf_counter,
    ) -> None:
        self._clock = clock
        self._duration = max(0.0, duration)
        self._remaining = self._duration
        self._deadline: float | None = None

    @property
    def running(self) -> bool:
        return self._deadline is not None

    @property
    def duration(self) -> float:
        return self._duration

    def remaining(self) -> float:
        if self._deadline is None:
            return self._remaining
        return max(0.0, self._deadline - self._clock())

    def start(self) -> None:
        if self._deadline is not None:
            return
        # Pressing Start after a finished countdown starts it again.
        if self._remaining <= 0.0:
            self._remaining = self._duration
        if self._remaining > 0.0:
            self._deadline = self._clock() + self._remaining

    def pause(self) -> None:
        if self._deadline is not None:
            self._remaining = max(0.0, self._deadline - self._clock())
            self._deadline = None

    def toggle(self) -> None:
        if self.running:
            self.pause()
        else:
            self.start()

    def reset(self) -> None:
        self._deadline = None
        self._remaining = self._duration

    def set_duration(self, seconds: float) -> None:
        self._duration = max(0.0, seconds)
        self._remaining = self._duration
        self._deadline = None

    def add_seconds(self, seconds: float) -> None:
        """Extend the countdown without changing the running state."""
        seconds = max(0.0, seconds)
        if self._deadline is not None:
            self._deadline += seconds
        else:
            self._remaining = max(0.0, self._remaining + seconds)

    def tick(self) -> bool:
        """Return True exactly once, when a running countdown reaches zero."""
        if self._deadline is not None and self._clock() >= self._deadline:
            self._deadline = None
            self._remaining = 0.0
            return True
        return False


def format_clock(value: datetime, use_24h: bool = True) -> str:
    """Format a local time as HH:MM:SS (24h) or hh:MM:SS AM/PM (12h)."""
    if use_24h:
        return value.strftime("%H:%M:%S")
    hour = value.hour % 12 or 12
    suffix = "AM" if value.hour < 12 else "PM"
    return f"{hour:02d}:{value.minute:02d}:{value.second:02d} {suffix}"


_MAX_HMS_SECONDS = 99 * 3600 + 59 * 60 + 59
_MAX_CENTISECONDS = _MAX_HMS_SECONDS * 100 + 99


def format_stopwatch(seconds: float) -> str:
    """Format elapsed seconds as HH:MM:SS.cc (centiseconds)."""
    # The tiny epsilon stops values such as 0.29 from truncating to 0.28
    # because of binary floating-point representation.
    total_centiseconds = min(
        _MAX_CENTISECONDS,
        max(0, int(max(0.0, seconds) * 100 + 1e-6)),
    )
    hours, remainder = divmod(total_centiseconds, 360_000)
    minutes, remainder = divmod(remainder, 6_000)
    whole_seconds, centiseconds = divmod(remainder, 100)
    return f"{hours:02d}:{minutes:02d}:{whole_seconds:02d}.{centiseconds:02d}"


def format_countdown(seconds: float) -> str:
    """Format remaining seconds as HH:MM:SS, rounding up to the next second."""
    total_seconds = min(
        _MAX_HMS_SECONDS,
        max(0, math.ceil(max(0.0, seconds) - 1e-9)),
    )
    hours, remainder = divmod(total_seconds, 3_600)
    minutes, whole_seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{whole_seconds:02d}"
