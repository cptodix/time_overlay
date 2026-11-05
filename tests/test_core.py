# SPDX-License-Identifier: GPL-3.0-or-later
"""Unit tests for the Qt-free time-keeping core."""

from __future__ import annotations

import unittest
from datetime import datetime

from time_overlay.core import (
    CountdownTimer,
    Stopwatch,
    format_clock,
    format_countdown,
    format_stopwatch,
)


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


class StopwatchTests(unittest.TestCase):
    def setUp(self) -> None:
        self.clock = FakeClock()
        self.watch = Stopwatch(self.clock)

    def test_starts_at_zero(self) -> None:
        self.assertFalse(self.watch.running)
        self.assertEqual(self.watch.elapsed(), 0.0)

    def test_start_and_elapse(self) -> None:
        self.watch.start()
        self.assertTrue(self.watch.running)
        self.clock.advance(1.5)
        self.assertAlmostEqual(self.watch.elapsed(), 1.5)

    def test_pause_freezes_elapsed(self) -> None:
        self.watch.start()
        self.clock.advance(2.0)
        self.watch.pause()
        self.clock.advance(10.0)
        self.assertFalse(self.watch.running)
        self.assertAlmostEqual(self.watch.elapsed(), 2.0)

    def test_resume_accumulates(self) -> None:
        self.watch.start()
        self.clock.advance(2.0)
        self.watch.pause()
        self.clock.advance(10.0)
        self.watch.start()
        self.clock.advance(3.0)
        self.assertAlmostEqual(self.watch.elapsed(), 5.0)

    def test_toggle(self) -> None:
        self.watch.toggle()
        self.assertTrue(self.watch.running)
        self.watch.toggle()
        self.assertFalse(self.watch.running)

    def test_reset_stops_and_clears(self) -> None:
        self.watch.start()
        self.clock.advance(4.0)
        self.watch.reset()
        self.assertFalse(self.watch.running)
        self.assertEqual(self.watch.elapsed(), 0.0)

    def test_add_seconds_while_running(self) -> None:
        self.watch.start()
        self.clock.advance(1.0)
        self.watch.add_seconds(60)
        self.assertAlmostEqual(self.watch.elapsed(), 61.0)

    def test_set_elapsed_preserves_running_state(self) -> None:
        self.watch.start()
        self.clock.advance(1.0)
        self.watch.set_elapsed(30.0)
        self.assertTrue(self.watch.running)
        self.clock.advance(2.0)
        self.assertAlmostEqual(self.watch.elapsed(), 32.0)


class CountdownTimerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.clock = FakeClock()
        self.timer = CountdownTimer(300.0, self.clock)

    def test_starts_at_duration(self) -> None:
        self.assertEqual(self.timer.remaining(), 300.0)
        self.assertFalse(self.timer.running)

    def test_counts_down(self) -> None:
        self.timer.start()
        self.clock.advance(10.0)
        self.assertAlmostEqual(self.timer.remaining(), 290.0)

    def test_pause_freezes_remaining(self) -> None:
        self.timer.start()
        self.clock.advance(10.0)
        self.timer.pause()
        self.clock.advance(10.0)
        self.assertAlmostEqual(self.timer.remaining(), 290.0)

    def test_tick_finishes_once(self) -> None:
        self.timer.start()
        self.clock.advance(300.0)
        self.assertTrue(self.timer.tick())
        self.assertFalse(self.timer.running)
        self.assertEqual(self.timer.remaining(), 0.0)
        self.assertFalse(self.timer.tick())

    def test_start_after_finish_restarts_duration(self) -> None:
        self.timer.start()
        self.clock.advance(300.0)
        self.assertTrue(self.timer.tick())
        self.timer.start()
        self.assertTrue(self.timer.running)
        self.assertAlmostEqual(self.timer.remaining(), 300.0)

    def test_add_seconds_while_running(self) -> None:
        self.timer.start()
        self.clock.advance(10.0)
        self.timer.add_seconds(60)
        self.assertAlmostEqual(self.timer.remaining(), 350.0)

    def test_add_seconds_while_paused(self) -> None:
        self.timer.add_seconds(60)
        self.assertAlmostEqual(self.timer.remaining(), 360.0)

    def test_reset_restores_duration(self) -> None:
        self.timer.start()
        self.clock.advance(100.0)
        self.timer.reset()
        self.assertFalse(self.timer.running)
        self.assertEqual(self.timer.remaining(), 300.0)

    def test_set_duration_stops_and_resets(self) -> None:
        self.timer.start()
        self.timer.set_duration(600.0)
        self.assertFalse(self.timer.running)
        self.assertEqual(self.timer.remaining(), 600.0)
        self.assertEqual(self.timer.duration, 600.0)


class FormattingTests(unittest.TestCase):
    def test_clock_24_hour(self) -> None:
        value = datetime(2026, 11, 5, 15, 4, 5)
        self.assertEqual(format_clock(value, True), "15:04:05")

    def test_clock_12_hour(self) -> None:
        value = datetime(2026, 11, 5, 15, 4, 5)
        self.assertEqual(format_clock(value, False), "03:04:05 PM")

    def test_clock_12_hour_midnight_and_noon(self) -> None:
        midnight = datetime(2026, 11, 5, 0, 0, 0)
        noon = datetime(2026, 11, 5, 12, 0, 0)
        self.assertEqual(format_clock(midnight, False), "12:00:00 AM")
        self.assertEqual(format_clock(noon, False), "12:00:00 PM")

    def test_stopwatch_format(self) -> None:
        self.assertEqual(format_stopwatch(0), "00:00:00.00")
        self.assertEqual(format_stopwatch(1.23), "00:00:01.23")
        self.assertEqual(format_stopwatch(0.29), "00:00:00.29")
        self.assertEqual(format_stopwatch(3661.239), "01:01:01.23")

    def test_countdown_format_rounds_up(self) -> None:
        self.assertEqual(format_countdown(300.0), "00:05:00")
        self.assertEqual(format_countdown(299.2), "00:05:00")
        self.assertEqual(format_countdown(298.9), "00:04:59")
        self.assertEqual(format_countdown(0.0), "00:00:00")
        self.assertEqual(format_countdown(3600.0), "01:00:00")


if __name__ == "__main__":
    unittest.main()
