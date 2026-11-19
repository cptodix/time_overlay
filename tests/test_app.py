# SPDX-License-Identifier: GPL-3.0-or-later
"""Tests for application bootstrap helpers."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from time_overlay.app import _acquire_lock


class SingleInstanceTests(unittest.TestCase):
    def test_second_lock_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "time-overlay.lock"
            first = _acquire_lock(path)
            self.assertIsNotNone(first)
            assert first is not None
            try:
                self.assertIsNone(_acquire_lock(path))
            finally:
                first.unlock()


if __name__ == "__main__":
    unittest.main()
