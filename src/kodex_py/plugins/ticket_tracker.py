"""Freshdesk Ticket Time Tracker — replicates the AHK ticketTracker.ahk.

Features:
- Extract ticket number from clipboard URL
- Start/stop tracking with Ctrl+Shift+T
- Floating overlay showing elapsed time
- Store time entries as CSV files
- Generate time log output

The overlay uses tkinter for the floating timer window.
"""

from __future__ import annotations

import csv
import getpass
import logging
import os
import re
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Callable

log = logging.getLogger(__name__)

# Regex to extract ticket number from Freshdesk URL
_TICKET_RE = re.compile(r"tickets?/(\d+)", re.IGNORECASE)


class TicketTracker:
    """Freshdesk ticket time tracker with floating overlay."""

    def __init__(self, data_dir: str | Path | None = None) -> None:
        self.data_dir = Path(data_dir) if data_dir else Path.home() / ".kodex" / "timeTracker"
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self._tracking = False
        self._ticket_number: str = ""
        self._start_time: float = 0.0
        self._overlay = None
        self._timer_thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._username = getpass.getuser()

    @property
    def is_tracking(self) -> bool:
        return self._tracking

    @property
    def ticket_number(self) -> str:
        return self._ticket_number

    def toggle(self) -> str:
        """Toggle tracking on/off. Returns a status message."""
        if self._tracking:
            return self.stop()
        else:
            return self.start()

    def start(self, ticket_number: str | None = None) -> str:
        """Start tracking a ticket.

        If no ticket_number is provided, tries to extract one from the clipboard.
        Returns a status message.
        """
        if self._tracking:
            return f"Already tracking ticket #{self._ticket_number}"

        if ticket_number is None:
            ticket_number = self._extract_ticket_from_clipboard()

        if not ticket_number:
            return "No ticket number found. Copy a Freshdesk URL first."

        self._ticket_number = ticket_number
        self._start_time = time.time()
        self._tracking = True
        self._stop_event.clear()

        # Log start entry
        self._log_entry("Started")

        # Start overlay (non-fatal if it fails)
        try:
            self._start_overlay()
        except Exception:
            log.warning("Failed to start overlay", exc_info=True)

        log.info("Started tracking ticket #%s", ticket_number)
        return f"Tracking ticket #{ticket_number}"

    def stop(self) -> str:
        """Stop tracking and log the duration. Returns a status message."""
        if not self._tracking:
            return "Not currently tracking."

        elapsed = time.time() - self._start_time
        hours = elapsed / 3600.0

        # Log finish entry with duration
        self._log_entry("Finished", duration_hours=hours)

        ticket = self._ticket_number
        self._tracking = False
        self._ticket_number = ""
        self._stop_event.set()

        # Destroy overlay
        self._destroy_overlay()

        msg = f"Ticket #{ticket}: {self._format_duration(elapsed)} ({hours:.2f}h)"
        log.info("Stopped tracking: %s", msg)
        return msg

    def get_elapsed(self) -> float:
        """Return elapsed seconds since tracking started."""
        if not self._tracking:
            return 0.0
        return time.time() - self._start_time

    def get_time_log(self, date: datetime | None = None) -> list[dict]:
        """Read today's time log entries. Returns list of dicts."""
        date = date or datetime.now()
        csv_path = self._get_csv_path(date)
        if not csv_path.exists():
            return []

        entries = []
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) >= 3:
                    entry = {
                        "ticket_number": row[0],
                        "status": row[1],
                        "timestamp": row[2],
                        "duration_hours": float(row[3]) if len(row) > 3 and row[3] else None,
                    }
                    entries.append(entry)
        return entries

    # ── Internal ──

    def _extract_ticket_from_clipboard(self) -> str:
        """Try to extract a Freshdesk ticket number from the clipboard."""
        try:
            import pyperclip
            clip = pyperclip.paste() or ""
        except Exception:
            clip = ""

        match = _TICKET_RE.search(clip)
        if match:
            return match.group(1)

        # Also accept bare numbers
        stripped = clip.strip()
        if stripped.isdigit() and len(stripped) <= 10:
            return stripped

        return ""

    def _log_entry(self, status: str, duration_hours: float | None = None) -> None:
        """Append an entry to today's CSV log file."""
        now = datetime.now()
        csv_path = self._get_csv_path(now)

        timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
        row = [self._ticket_number, status, timestamp]
        if duration_hours is not None:
            row.append(f"{duration_hours:.4f}")

        with open(csv_path, "a", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(row)

    def _get_csv_path(self, dt: datetime) -> Path:
        """Return the CSV path for the given date: USERNAME.MMDD.csv"""
        return self.data_dir / f"{self._username}.{dt.strftime('%m%d')}.csv"

    def _start_overlay(self) -> None:
        """Start the floating timer overlay in a background thread."""
        self._timer_thread = threading.Thread(target=self._run_overlay, daemon=True)
        self._timer_thread.start()

    def _run_overlay(self) -> None:
        """Run the tkinter overlay window (must be in its own thread with its own mainloop)."""
        try:
            import tkinter as tk
        except ImportError:
            log.warning("tkinter not available — overlay disabled")
            return

        root = tk.Tk()
        root.overrideredirect(True)  # No title bar
        root.attributes("-topmost", True)
        root.configure(bg="#1e1e1e")

        # Position: left edge, vertically centered
        root.geometry("+0+300")

        # Ticket label
        ticket_label = tk.Label(
            root,
            text=f"Ticket #{self._ticket_number}",
            fg="white",
            bg="#1e1e1e",
            font=("Segoe UI", 10),
            padx=8,
            pady=2,
        )
        ticket_label.pack()

        # Timer label
        timer_label = tk.Label(
            root,
            text="00:00:00",
            fg="#00FF00",
            bg="#1e1e1e",
            font=("Consolas", 14, "bold"),
            padx=8,
            pady=2,
        )
        timer_label.pack()

        self._overlay = root

        def update_timer():
            if self._stop_event.is_set():
                root.destroy()
                return
            elapsed = self.get_elapsed()
            timer_label.config(text=self._format_duration(elapsed))
            root.after(1000, update_timer)

        root.after(1000, update_timer)

        try:
            root.mainloop()
        except Exception:
            pass
        finally:
            self._overlay = None

    def _destroy_overlay(self) -> None:
        """Signal the overlay to close."""
        self._stop_event.set()
        # The overlay's update_timer loop checks _stop_event

    @staticmethod
    def _format_duration(seconds: float) -> str:
        """Format seconds as HH:MM:SS."""
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        return f"{h:02d}:{m:02d}:{s:02d}"
