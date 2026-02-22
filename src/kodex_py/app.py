"""Kodex application — ties together the engine, storage, tray, and plugins.

This is the main orchestrator that:
1.  Opens the database
2.  Loads config + all enabled hotstrings into the matcher
3.  Initialises the ticket tracker plugin
4.  Starts the input monitor
5.  Runs the system-tray icon (with GUI integration)
"""

from __future__ import annotations

import atexit
import logging
import os
import sys
from pathlib import Path

from kodex_py import __version__
from kodex_py.config import get_db_path, load_config
from kodex_py.engine.executor import execute as fire_expansion
from kodex_py.engine.matcher import HotstringMatcher
from kodex_py.storage.database import Database
from kodex_py.storage.models import SendMode, TriggerType

log = logging.getLogger(__name__)

# Global PID file path (set on startup)
_pid_file: Path | None = None


def _write_pid_file(path: Path) -> None:
    """Write current PID to file."""
    global _pid_file
    _pid_file = path
    try:
        path.write_text(str(os.getpid()))
        log.debug("PID file written: %s", path)
    except OSError as e:
        log.warning("Failed to write PID file: %s", e)


def _remove_pid_file() -> None:
    """Remove PID file on exit."""
    global _pid_file
    if _pid_file and _pid_file.exists():
        try:
            _pid_file.unlink()
            log.debug("PID file removed: %s", _pid_file)
        except OSError as e:
            log.warning("Failed to remove PID file: %s", e)
    _pid_file = None


class KodexApp:
    """Top-level application object."""

    def __init__(self, db_path: str | Path | None = None) -> None:
        self.db_path = Path(db_path) if db_path else get_db_path()
        self.db: Database | None = None
        self.config = None
        self.matcher = HotstringMatcher(case_sensitive=True)
        self._input_monitor = None
        self.tracker = None  # TicketTracker instance
        self.global_vars = None  # GlobalVariables instance
        self.time_scheduler = None  # TimeTrackingScheduler instance

    # ── lifecycle ───────────────────────────────────────────────────

    def start(self) -> None:
        """Initialise and run the application (blocks on tray icon loop)."""
        import signal

        def _shutdown(sig, frame):
            log.info("Received signal %s — shutting down", sig)
            self.stop()
            sys.exit(0)

        signal.signal(signal.SIGINT, _shutdown)
        signal.signal(signal.SIGTERM, _shutdown)
        if sys.platform == "win32":
            try:
                signal.signal(signal.SIGBREAK, _shutdown)
            except (AttributeError, OSError):
                pass

        log.info("Kodex %s starting — db=%s", __version__, self.db_path)

        # Write PID file so native messaging host knows we're running
        pid_file = self.db_path.parent / "kodex.pid"
        _write_pid_file(pid_file)
        atexit.register(_remove_pid_file)

        # Database
        self.db = Database(self.db_path)
        self.db.open()

        # Config
        self.config = load_config(self.db)

        # Build matcher
        self.reload_hotstrings()

        # Ticket tracker plugin
        try:
            from kodex_py.plugins.ticket_tracker import TicketTracker
            tracker_dir = self.db_path.parent / "timeTracker"
            self.tracker = TicketTracker(data_dir=tracker_dir)
            log.info("Ticket tracker initialised — data dir: %s", tracker_dir)
        except Exception:
            log.warning("Failed to initialise ticket tracker", exc_info=True)

        # Global variables
        try:
            from kodex_py.utils.global_variables import get_global_variables
            self.global_vars = get_global_variables(self.db_path.parent)
            self.global_vars.start_watching(self._on_variables_changed)
            log.info("Global variables initialised — %d variables loaded", 
                     len(self.global_vars.list_all()))
        except Exception:
            log.warning("Failed to initialise global variables", exc_info=True)

        # Time tracking scheduler (daily export at 5:50 PM, Monday archive)
        try:
            from kodex_py.plugins.time_scheduler import TimeTrackingScheduler
            self.time_scheduler = TimeTrackingScheduler(data_dir=self.db_path.parent)
            self.time_scheduler.start()
            log.info("Time tracking scheduler initialised")
        except Exception:
            log.warning("Failed to initialise time tracking scheduler", exc_info=True)

        # Input monitor
        from kodex_py.engine.input_monitor import InputMonitor
        self._input_monitor = InputMonitor(self.matcher, self._on_match)
        self._input_monitor.start()

        # System tray (blocks)
        try:
            from kodex_py.tray import run_tray
            run_tray(self)
        except ImportError as e:
            log.warning("Tray unavailable (%s) — running headless", e)
            self._input_monitor._kb_listener.join()
        except Exception as e:
            log.error("Tray failed: %s — running headless", e)
            self._input_monitor._kb_listener.join()

    def stop(self) -> None:
        if self.time_scheduler:
            self.time_scheduler.stop()
        if self.global_vars:
            self.global_vars.stop_watching()
        if self.tracker and self.tracker.is_tracking:
            self.tracker.stop()
        if self._input_monitor:
            self._input_monitor.stop()
        if self.db:
            self.db.close()
        _remove_pid_file()
        log.info("Kodex stopped")

    # ── hotstring loading ───────────────────────────────────────────

    def reload_hotstrings(self) -> None:
        """Rebuild the matcher from all enabled bundles in the database."""
        assert self.db is not None
        hotstrings = self.db.get_hotstrings(enabled_only=True)
        entries = [
            (hs.name, hs.id, frozenset(hs.triggers))
            for hs in hotstrings
            if hs.id is not None
        ]
        self.matcher.rebuild(entries)
        log.info("Loaded %d hotstrings into matcher", len(entries))

    # ── match callback ──────────────────────────────────────────────

    def _on_match(self, match, trigger: str | None) -> None:
        """Called from the input monitor thread when a hotstring matches."""
        assert self.db is not None
        hs = self.db.get_hotstring(match.hotstring_id)
        if hs is None:
            log.warning("Matched hotstring id=%d but not found in DB", match.hotstring_id)
            return

        sound_path = None
        if self.config and self.config.play_sound:
            sound_path = str(self.db_path.parent / "resources" / "kodex.wav")

        # Prompt callback — uses tkinter dialog if available
        prompt_fn = None
        if "%prompt%" in hs.replacement:
            prompt_fn = self._prompt_user

        # trigger is non-None for space/tab/enter (character already typed)
        # trigger is None for instant matches (no trailing char to erase)
        success = fire_expansion(
            hs.name,
            hs.replacement,
            is_script=hs.is_script,
            send_mode=self.config.send_mode if self.config else SendMode.DIRECT,
            play_sound=self.config.play_sound if self.config else False,
            sound_path=sound_path,
            prompt_fn=prompt_fn,
            stats_fn=self._update_stats,
            trigger_char=trigger is not None,
        )

        if success:
            log.debug("Expanded '%s' (%d chars)", hs.name, len(hs.replacement))

    def _prompt_user(self, template: str) -> str | None:
        """Show a tkinter prompt dialog for %p variables."""
        try:
            from kodex_py.gui.prompt import show_prompt
            return show_prompt(template)
        except ImportError:
            return ""

    def _update_stats(self, chars: int) -> None:
        assert self.db is not None
        self.db.increment_stat("expanded", 1)
        self.db.increment_stat("chars_saved", chars)

    def _on_variables_changed(self) -> None:
        """Called when global_variables.json or freshdesk_context.json changes."""
        log.debug("Global variables or freshdesk context updated")
        # Variables are loaded automatically by the watcher, no need to reload matcher

    # ── toggle ──────────────────────────────────────────────────────

    @property
    def disabled(self) -> bool:
        return self._input_monitor.disabled if self._input_monitor else False

    @disabled.setter
    def disabled(self, value: bool) -> None:
        if self._input_monitor:
            self._input_monitor.disabled = value
