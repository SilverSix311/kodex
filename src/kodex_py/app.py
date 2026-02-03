"""Kodex application — ties together the engine, storage, tray, and plugins.

This is the main orchestrator that:
1.  Opens the database
2.  Loads config + all enabled hotstrings into the matcher
3.  Initialises the ticket tracker plugin
4.  Starts the input monitor
5.  Runs the system-tray icon (with GUI integration)
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from kodex_py import __version__
from kodex_py.config import get_db_path, load_config
from kodex_py.engine.executor import execute as fire_expansion
from kodex_py.engine.matcher import HotstringMatcher
from kodex_py.storage.database import Database
from kodex_py.storage.models import SendMode, TriggerType

log = logging.getLogger(__name__)


class KodexApp:
    """Top-level application object."""

    def __init__(self, db_path: str | Path | None = None) -> None:
        self.db_path = Path(db_path) if db_path else get_db_path()
        self.db: Database | None = None
        self.config = None
        self.matcher = HotstringMatcher(case_sensitive=True)
        self._input_monitor = None
        self.tracker = None  # TicketTracker instance

    # ── lifecycle ───────────────────────────────────────────────────

    def start(self) -> None:
        """Initialise and run the application (blocks on tray icon loop)."""
        log.info("Kodex %s starting — db=%s", __version__, self.db_path)

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

        # Input monitor
        from kodex_py.engine.input_monitor import InputMonitor
        self._input_monitor = InputMonitor(self.matcher, self._on_match)
        self._input_monitor.start()

        # System tray (blocks)
        try:
            from kodex_py.tray import run_tray
            run_tray(self)
        except ImportError:
            log.warning("pystray not available — running headless")
            self._input_monitor._kb_listener.join()

    def stop(self) -> None:
        if self.tracker and self.tracker.is_tracking:
            self.tracker.stop()
        if self._input_monitor:
            self._input_monitor.stop()
        if self.db:
            self.db.close()
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
        if "%p" in hs.replacement:
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

    # ── toggle ──────────────────────────────────────────────────────

    @property
    def disabled(self) -> bool:
        return self._input_monitor.disabled if self._input_monitor else False

    @disabled.setter
    def disabled(self, value: bool) -> None:
        if self._input_monitor:
            self._input_monitor.disabled = value
