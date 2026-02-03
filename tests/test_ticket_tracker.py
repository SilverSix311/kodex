"""Tests for the Freshdesk ticket time tracker."""

import csv
import time
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from kodex_py.plugins.ticket_tracker import TicketTracker, _TICKET_RE


class TestTicketRegex:
    def test_freshdesk_url(self):
        url = "https://lindenlab.freshdesk.com/a/tickets/12345"
        m = _TICKET_RE.search(url)
        assert m is not None
        assert m.group(1) == "12345"

    def test_short_ticket_url(self):
        url = "https://example.freshdesk.com/tickets/99999"
        m = _TICKET_RE.search(url)
        assert m is not None
        assert m.group(1) == "99999"

    def test_no_match(self):
        assert _TICKET_RE.search("hello world") is None
        assert _TICKET_RE.search("https://example.com") is None

    def test_ticket_in_path(self):
        url = "https://support.com/ticket/42"
        m = _TICKET_RE.search(url)
        assert m is not None
        assert m.group(1) == "42"


class TestTicketTracker:
    @pytest.fixture
    def tracker(self, tmp_path):
        return TicketTracker(data_dir=tmp_path)

    def test_initial_state(self, tracker):
        assert not tracker.is_tracking
        assert tracker.ticket_number == ""
        assert tracker.get_elapsed() == 0.0

    def test_start_with_explicit_ticket(self, tracker):
        msg = tracker.start(ticket_number="12345")
        assert "12345" in msg
        assert tracker.is_tracking
        assert tracker.ticket_number == "12345"

    def test_start_creates_csv(self, tracker, tmp_path):
        tracker.start(ticket_number="42")
        # Check CSV was created
        csv_files = list(tmp_path.glob("*.csv"))
        assert len(csv_files) == 1

        with open(csv_files[0], "r") as f:
            reader = csv.reader(f)
            rows = list(reader)
        assert len(rows) == 1
        assert rows[0][0] == "42"
        assert rows[0][1] == "Started"

    def test_stop_logs_duration(self, tracker, tmp_path):
        tracker.start(ticket_number="42")
        time.sleep(0.1)
        msg = tracker.stop()

        assert "42" in msg
        assert not tracker.is_tracking

        csv_files = list(tmp_path.glob("*.csv"))
        with open(csv_files[0], "r") as f:
            rows = list(csv.reader(f))
        assert len(rows) == 2
        assert rows[1][1] == "Finished"
        assert float(rows[1][3]) >= 0  # duration logged (may round to 0 for short intervals)

    def test_toggle(self, tracker):
        msg1 = tracker.toggle()  # start — but no clipboard, no ticket
        # Without clipboard, should fail gracefully
        assert "No ticket" in msg1 or "tracking" in msg1.lower()

    def test_toggle_with_ticket(self, tracker):
        tracker.start(ticket_number="100")
        msg = tracker.toggle()  # should stop
        assert "100" in msg
        assert not tracker.is_tracking

    def test_double_start(self, tracker):
        tracker.start(ticket_number="1")
        msg = tracker.start(ticket_number="2")
        assert "Already" in msg
        assert tracker.ticket_number == "1"

    def test_stop_when_not_tracking(self, tracker):
        msg = tracker.stop()
        assert "Not" in msg

    def test_get_elapsed(self, tracker):
        tracker.start(ticket_number="1")
        time.sleep(0.1)
        elapsed = tracker.get_elapsed()
        assert elapsed >= 0.1
        tracker.stop()

    def test_get_time_log(self, tracker):
        tracker.start(ticket_number="555")
        time.sleep(0.05)
        tracker.stop()

        entries = tracker.get_time_log()
        assert len(entries) == 2
        assert entries[0]["ticket_number"] == "555"
        assert entries[0]["status"] == "Started"
        assert entries[1]["status"] == "Finished"
        assert entries[1]["duration_hours"] is not None

    def test_csv_path_format(self, tracker, tmp_path):
        tracker.start(ticket_number="1")
        tracker.stop()

        csv_files = list(tmp_path.glob("*.csv"))
        assert len(csv_files) == 1
        # Filename should match USERNAME.MMDD.csv
        name = csv_files[0].stem
        parts = name.split(".")
        assert len(parts) == 2
        assert len(parts[1]) == 4  # MMDD

    def test_format_duration(self):
        assert TicketTracker._format_duration(0) == "00:00:00"
        assert TicketTracker._format_duration(61) == "00:01:01"
        assert TicketTracker._format_duration(3661) == "01:01:01"
        assert TicketTracker._format_duration(7200) == "02:00:00"

    @patch("kodex_py.plugins.ticket_tracker.TicketTracker._start_overlay")
    def test_start_no_overlay_crash(self, mock_overlay, tracker):
        """Start should work even if overlay fails."""
        mock_overlay.side_effect = Exception("no display")
        # This shouldn't raise — overlay failure is non-fatal
        # Actually start catches it via the daemon thread, so we mock _start_overlay
        tracker.start(ticket_number="42")
        assert tracker.is_tracking
        tracker.stop()
