"""Time Tracking Scheduler — automatic daily export and weekly archive.

Features:
- Auto-export CSV at 5:50 PM system time daily
- Archive time_tracking.json every Monday and start fresh for new week
"""

from __future__ import annotations

import csv
import json
import logging
import os
import shutil
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path

log = logging.getLogger(__name__)


def _get_data_dir() -> Path:
    """Get the Kodex data directory."""
    kodex_root = os.environ.get("KODEX_ROOT")
    if kodex_root:
        portable_data = Path(kodex_root) / "data"
        home_data = Path.home() / ".kodex"
        if portable_data.exists() or not home_data.exists():
            return portable_data
    return Path.home() / ".kodex"


class TimeTrackingScheduler:
    """Background scheduler for time tracking maintenance tasks."""

    # Time to export CSV (24-hour format)
    EXPORT_HOUR = 17  # 5 PM
    EXPORT_MINUTE = 50  # 5:50 PM
    
    def __init__(self, data_dir: Path | None = None) -> None:
        self._data_dir = data_dir or _get_data_dir()
        self._time_tracking_file = self._data_dir / "time_tracking.json"
        self._archive_dir = self._data_dir / "time_tracking_archive"
        
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        
        # Track what we've done today to avoid duplicates
        self._last_export_date: str | None = None
        self._last_archive_date: str | None = None

    def start(self) -> None:
        """Start the scheduler background thread."""
        if self._thread is not None and self._thread.is_alive():
            return  # Already running
        
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run_loop,
            daemon=True,
            name="TimeTrackingScheduler",
        )
        self._thread.start()
        log.info("Time tracking scheduler started")

    def stop(self) -> None:
        """Stop the scheduler."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2)
            self._thread = None
        log.info("Time tracking scheduler stopped")

    def _run_loop(self) -> None:
        """Main scheduler loop — checks every minute."""
        while not self._stop_event.wait(timeout=60):  # Check every minute
            try:
                self._check_and_run_tasks()
            except Exception as e:
                log.error("Scheduler error: %s", e, exc_info=True)

    def _check_and_run_tasks(self) -> None:
        """Check if any scheduled tasks should run."""
        now = datetime.now()
        today = now.strftime("%Y-%m-%d")
        
        # ── Monday archive check ──
        # Run at start of Monday (any time, but only once)
        if now.weekday() == 0:  # Monday
            if self._last_archive_date != today:
                log.info("Monday detected — running weekly archive")
                self._archive_and_reset()
                self._last_archive_date = today
        
        # ── Daily export at 5:50 PM ──
        if (now.hour == self.EXPORT_HOUR and 
            now.minute == self.EXPORT_MINUTE and
            self._last_export_date != today):
            log.info("5:50 PM — running daily export")
            self._export_csv()
            self._last_export_date = today

    def _load_time_tracking(self) -> dict:
        """Load time_tracking.json."""
        if not self._time_tracking_file.exists():
            return {"entries": {}, "_active": None}
        
        try:
            with open(self._time_tracking_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            log.warning("Could not read time_tracking.json: %s", e)
            return {"entries": {}, "_active": None}

    def _save_time_tracking(self, data: dict) -> None:
        """Save time_tracking.json atomically."""
        tmp = self._time_tracking_file.with_suffix(".json.tmp")
        try:
            tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
            tmp.replace(self._time_tracking_file)
        except OSError as e:
            log.error("Failed to write time_tracking.json: %s", e)

    def _export_csv(self) -> None:
        """Export current time tracking data to CSV."""
        data = self._load_time_tracking()
        entries = data.get("entries", {})
        
        if not entries:
            log.info("No time tracking data to export")
            return
        
        # Export to ~/Documents/MM.DD.YYYY.TimeTracking.csv
        documents_dir = Path.home() / "Documents"
        documents_dir.mkdir(parents=True, exist_ok=True)
        
        date_str = datetime.now().strftime("%m.%d.%Y")
        export_path = documents_dir / f"{date_str}.TimeTracking.csv"
        
        try:
            row_count = 0
            with open(export_path, "w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                
                for date in sorted(entries.keys()):
                    date_entries = entries[date]
                    # Format date as MM.DD.YYYY for CSV
                    try:
                        dt = datetime.strptime(date, "%Y-%m-%d")
                        csv_date = dt.strftime("%m.%d.%Y")
                    except ValueError:
                        csv_date = date
                    
                    for ticket_num in sorted(date_entries.keys()):
                        info = date_entries[ticket_num]
                        total_seconds = info.get("total_seconds", 0)
                        writer.writerow([csv_date, ticket_num, f"{total_seconds:.6f}"])
                        row_count += 1
            
            log.info("Auto-exported time tracking to %s (%d rows)", export_path, row_count)
        
        except OSError as e:
            log.error("Failed to auto-export CSV: %s", e)

    def _archive_and_reset(self) -> None:
        """Archive current time_tracking.json and create fresh one for new week."""
        if not self._time_tracking_file.exists():
            log.info("No time_tracking.json to archive")
            return
        
        # Create archive directory
        self._archive_dir.mkdir(parents=True, exist_ok=True)
        
        # Archive filename: time_tracking_YYYY-MM-DD.json (using previous week's end date)
        # The "previous week" ended yesterday (Sunday)
        yesterday = datetime.now() - timedelta(days=1)
        archive_name = f"time_tracking_{yesterday.strftime('%Y-%m-%d')}.json"
        archive_path = self._archive_dir / archive_name
        
        try:
            # Copy current file to archive
            shutil.copy2(self._time_tracking_file, archive_path)
            log.info("Archived time_tracking.json to %s", archive_path)
            
            # Also export a CSV of the archived week
            self._export_csv()
            
            # Create fresh time_tracking.json
            fresh_data = {"entries": {}, "_active": None}
            self._save_time_tracking(fresh_data)
            log.info("Created fresh time_tracking.json for new week")
            
        except OSError as e:
            log.error("Failed to archive time_tracking.json: %s", e)

    def force_export(self) -> Path | None:
        """Manually trigger an export. Returns the export path on success."""
        try:
            self._export_csv()
            date_str = datetime.now().strftime("%m.%d.%Y")
            return Path.home() / "Documents" / f"{date_str}.TimeTracking.csv"
        except Exception as e:
            log.error("Force export failed: %s", e)
            return None

    def force_archive(self) -> bool:
        """Manually trigger an archive. Returns True on success."""
        try:
            self._archive_and_reset()
            return True
        except Exception as e:
            log.error("Force archive failed: %s", e)
            return False
