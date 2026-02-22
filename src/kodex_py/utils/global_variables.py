"""Global variables management — user-defined variables with type support.

Variables are stored in ~/.kodex/global_variables.json and can be
substituted in hotstrings using %variable_name% syntax.

Priority (highest → lowest):
  1. Source-specific context file (e.g. freshdesk_context.json, csr_context.json, gt3_context.json)
     - Prefixed lookup  ``%freshdesk_ticket_number%`` → freshdesk_context.json
     - Unprefixed lookup ``%ticket_number%``           → most-recently-updated context file
  2. time_tracking.json  (%ticket_time%, %ticket_time_formatted%)
  3. global_variables.json
"""

from __future__ import annotations

import json
import logging
import os
import re
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable

log = logging.getLogger(__name__)

# Supported variable types
VARIABLE_TYPES = ("string", "int", "decimal", "boolean", "array", "dict")

# Pattern to match %variable_name% (non-greedy, alphanumeric + underscore)
VARIABLE_PATTERN = re.compile(r"%([a-zA-Z_][a-zA-Z0-9_]*)%")

# Known context sources (order doesn't matter for logic, but handy to have them listed)
KNOWN_SOURCES = ("freshdesk", "csr", "gt3")


def _parse_updated_at(context: dict) -> datetime | None:
    """Parse ``_updated_at`` from a context dict, returning None on failure."""
    raw = context.get("_updated_at")
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw)
    except (ValueError, TypeError):
        return None


def _seconds_to_hhmmss(total_seconds: float) -> str:
    """Convert a floating-point seconds value to ``HH:MM:SS`` string."""
    total_seconds = max(0, int(total_seconds))
    h = total_seconds // 3600
    m = (total_seconds % 3600) // 60
    s = total_seconds % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


class GlobalVariables:
    """Manages global variables with file persistence and change watching."""

    def __init__(self, data_dir: Path | None = None) -> None:
        from kodex_py.config import get_data_dir

        self._data_dir = data_dir or get_data_dir()
        self._variables_file = self._data_dir / "global_variables.json"
        self._time_tracking_file = self._data_dir / "time_tracking.json"

        # Per-source context files
        self._context_files: dict[str, Path] = {
            src: self._data_dir / f"{src}_context.json" for src in KNOWN_SOURCES
        }

        # Loaded data
        self._variables: dict[str, dict[str, Any]] = {}
        # { "freshdesk": {...}, "csr": {...}, "gt3": {...} }
        self._contexts: dict[str, dict[str, Any]] = {src: {} for src in KNOWN_SOURCES}
        self._time_tracking: dict[str, Any] = {}

        # File modification times
        self._last_vars_mtime: float = 0
        self._last_context_mtime: dict[str, float] = {src: 0.0 for src in KNOWN_SOURCES}
        self._last_time_tracking_mtime: float = 0.0

        self._watcher_thread: threading.Thread | None = None
        self._stop_watching = threading.Event()
        self._on_change_callbacks: list[Callable[[], None]] = []

        self.load()

    # ── File operations ─────────────────────────────────────────────

    def load(self) -> None:
        """Load variables from all files."""
        self._load_global_variables()
        self._load_all_contexts()
        self._load_time_tracking()

    def _load_global_variables(self) -> None:
        """Load global_variables.json."""
        if self._variables_file.exists():
            try:
                with open(self._variables_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._variables = data.get("variables", {})
                self._last_vars_mtime = os.path.getmtime(self._variables_file)
                log.info("Loaded %d global variables", len(self._variables))
            except (json.JSONDecodeError, OSError) as e:
                log.warning("Failed to load global_variables.json: %s", e)
                self._variables = {}
        else:
            self._variables = {}
            self._save()  # Create default file

    def _load_all_contexts(self) -> None:
        """Load all {source}_context.json files that exist."""
        for src, path in self._context_files.items():
            if path.exists():
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        self._contexts[src] = json.load(f)
                    self._last_context_mtime[src] = os.path.getmtime(path)
                    log.info(
                        "Loaded %s context with %d fields",
                        src, len(self._contexts[src]),
                    )
                except (json.JSONDecodeError, OSError) as e:
                    log.debug("Failed to load %s_context.json: %s", src, e)
                    self._contexts[src] = {}
            else:
                self._contexts[src] = {}

    def _load_time_tracking(self) -> None:
        """Load time_tracking.json if it exists."""
        if self._time_tracking_file.exists():
            try:
                with open(self._time_tracking_file, "r", encoding="utf-8") as f:
                    self._time_tracking = json.load(f)
                self._last_time_tracking_mtime = os.path.getmtime(self._time_tracking_file)
                log.debug("Loaded time tracking data")
            except (json.JSONDecodeError, OSError) as e:
                log.debug("Failed to load time_tracking.json: %s", e)
                self._time_tracking = {}
        else:
            self._time_tracking = {}

    def _save(self) -> None:
        """Save global variables to file."""
        try:
            self._data_dir.mkdir(parents=True, exist_ok=True)
            with open(self._variables_file, "w", encoding="utf-8") as f:
                json.dump({"variables": self._variables}, f, indent=2)
            self._last_vars_mtime = os.path.getmtime(self._variables_file)
            log.debug("Saved %d global variables", len(self._variables))
        except OSError as e:
            log.error("Failed to save global_variables.json: %s", e)

    def save(self) -> None:
        """Public save method."""
        self._save()

    # ── Context helpers ─────────────────────────────────────────────

    def _most_recent_context(self) -> dict[str, Any]:
        """Return the context dict from whichever source was updated most recently."""
        best_src: str | None = None
        best_dt: datetime | None = None

        for src, ctx in self._contexts.items():
            dt = _parse_updated_at(ctx)
            if dt is not None and (best_dt is None or dt > best_dt):
                best_dt = dt
                best_src = src

        if best_src:
            return self._contexts[best_src]
        return {}

    # ── Time tracking helpers ───────────────────────────────────────

    def _get_ticket_time_seconds(self) -> float | None:
        """Return total seconds for the currently active ticket (today only), or None."""
        active = self._time_tracking.get("_active")
        if not active:
            return None
        ticket_number = active.get("ticket_number")
        if not ticket_number:
            return None
        
        # New date-based structure: entries[date][ticket_number]
        today = datetime.now().strftime("%Y-%m-%d")
        entries = self._time_tracking.get("entries", {})
        today_entries = entries.get(today, {})
        ticket_entry = today_entries.get(ticket_number, {})
        
        # Fallback to old structure for backward compatibility
        if not ticket_entry and "tickets" in self._time_tracking:
            ticket_entry = self._time_tracking.get("tickets", {}).get(ticket_number, {})
        
        return float(ticket_entry.get("total_seconds", 0))

    # ── Variable CRUD ───────────────────────────────────────────────

    def get(self, name: str) -> Any:
        """Resolve a variable name following the priority rules.

        Resolution order:
          1. Source-prefixed lookup  (``freshdesk_ticket_number`` → freshdesk context)
          2. Unprefixed lookup       (``ticket_number`` → most-recently-updated context)
          3. Time-tracking specials  (``ticket_time``, ``ticket_time_formatted``)
          4. global_variables.json
        """
        # ── 1. Source-prefixed lookup ──────────────────────────────
        for src in KNOWN_SOURCES:
            prefix = f"{src}_"
            if name.startswith(prefix):
                field = name[len(prefix):]
                ctx = self._contexts.get(src, {})
                if field in ctx:
                    return ctx[field]
                # Prefixed name matched a source but field not found — don't
                # fall through to unprefixed logic for a different source.
                break

        # ── 2. Unprefixed context lookup (most-recent source) ──────
        # Only do this when the name doesn't start with a known source prefix.
        has_source_prefix = any(name.startswith(f"{src}_") for src in KNOWN_SOURCES)
        if not has_source_prefix:
            recent_ctx = self._most_recent_context()
            if name in recent_ctx:
                return recent_ctx[name]

        # ── 3. Time-tracking specials ──────────────────────────────
        if name == "ticket_time":
            secs = self._get_ticket_time_seconds()
            return secs  # May be None → leave placeholder as-is

        if name == "ticket_time_formatted":
            secs = self._get_ticket_time_seconds()
            if secs is None:
                return None
            return _seconds_to_hhmmss(secs)

        # ── 4. Global variables ────────────────────────────────────
        if name in self._variables:
            return self._variables[name].get("value")

        return None

    def get_type(self, name: str) -> str | None:
        """Get the type of a global variable."""
        if name in self._variables:
            return self._variables[name].get("type", "string")
        return None

    def set(self, name: str, value: Any, var_type: str = "string") -> None:
        """Set a global variable."""
        if var_type not in VARIABLE_TYPES:
            raise ValueError(f"Invalid type: {var_type}. Must be one of {VARIABLE_TYPES}")

        self._variables[name] = {"type": var_type, "value": value}
        self._save()

    def delete(self, name: str) -> bool:
        """Delete a global variable. Returns True if deleted."""
        if name in self._variables:
            del self._variables[name]
            self._save()
            return True
        return False

    def list_all(self) -> dict[str, dict[str, Any]]:
        """Return all global variables."""
        return dict(self._variables)

    def get_context(self, source: str) -> dict[str, Any]:
        """Return the loaded context for a specific source."""
        return dict(self._contexts.get(source, {}))

    def get_all_contexts(self) -> dict[str, dict[str, Any]]:
        """Return a copy of all loaded contexts."""
        return {src: dict(ctx) for src, ctx in self._contexts.items()}

    # ── Substitution ────────────────────────────────────────────────

    def substitute(self, text: str) -> str:
        """Replace %variable_name% tokens with their values.

        Priority: context files (source-prefixed > most-recent) > time-tracking > global_variables
        """
        def replace_match(match: re.Match) -> str:
            var_name = match.group(1)
            value = self.get(var_name)

            if value is None:
                # Leave unmatched variables as-is
                return match.group(0)

            # Convert value to string representation
            return self._value_to_string(value)

        return VARIABLE_PATTERN.sub(replace_match, text)

    def _value_to_string(self, value: Any) -> str:
        """Convert a variable value to its string representation."""
        if isinstance(value, bool):
            return "true" if value else "false"
        elif isinstance(value, (list, dict)):
            return json.dumps(value)
        else:
            return str(value)

    # ── File watching ───────────────────────────────────────────────

    def start_watching(self, callback: Callable[[], None] | None = None) -> None:
        """Start watching for file changes."""
        if callback:
            self._on_change_callbacks.append(callback)

        if self._watcher_thread is not None:
            return  # Already watching

        self._stop_watching.clear()
        self._watcher_thread = threading.Thread(
            target=self._watch_loop,
            daemon=True,
            name="GlobalVariablesWatcher",
        )
        self._watcher_thread.start()
        log.info("Started watching for variable file changes")

    def stop_watching(self) -> None:
        """Stop the file watcher."""
        self._stop_watching.set()
        if self._watcher_thread:
            self._watcher_thread.join(timeout=2)
            self._watcher_thread = None
        self._on_change_callbacks.clear()
        log.info("Stopped watching for variable file changes")

    def _watch_loop(self) -> None:
        """Background thread that checks for file changes every 2 seconds."""
        while not self._stop_watching.wait(timeout=2.0):
            changed = False

            # ── global_variables.json ──────────────────────────────
            if self._variables_file.exists():
                try:
                    mtime = os.path.getmtime(self._variables_file)
                    if mtime > self._last_vars_mtime:
                        self._load_global_variables()
                        changed = True
                except OSError:
                    pass

            # ── {source}_context.json files ────────────────────────
            for src, path in self._context_files.items():
                if path.exists():
                    try:
                        mtime = os.path.getmtime(path)
                        if mtime > self._last_context_mtime[src]:
                            # Reload just this source
                            try:
                                with open(path, "r", encoding="utf-8") as f:
                                    self._contexts[src] = json.load(f)
                                self._last_context_mtime[src] = mtime
                                log.debug("Reloaded %s context", src)
                                changed = True
                            except (json.JSONDecodeError, OSError) as e:
                                log.debug("Failed to reload %s_context.json: %s", src, e)
                    except OSError:
                        pass
                elif self._contexts[src]:
                    # File was deleted, clear context
                    self._contexts[src] = {}
                    self._last_context_mtime[src] = 0.0
                    changed = True

            # ── time_tracking.json ─────────────────────────────────
            if self._time_tracking_file.exists():
                try:
                    mtime = os.path.getmtime(self._time_tracking_file)
                    if mtime > self._last_time_tracking_mtime:
                        self._load_time_tracking()
                        changed = True
                except OSError:
                    pass
            elif self._time_tracking:
                self._time_tracking = {}
                changed = True

            if changed:
                for cb in self._on_change_callbacks:
                    try:
                        cb()
                    except Exception as e:
                        log.warning("Variable change callback failed: %s", e)


# ── Singleton instance ──────────────────────────────────────────────

_instance: GlobalVariables | None = None


def get_global_variables(data_dir: Path | None = None) -> GlobalVariables:
    """Get or create the singleton GlobalVariables instance."""
    global _instance
    if _instance is None:
        _instance = GlobalVariables(data_dir)
    return _instance


def substitute_global_variables(text: str) -> str:
    """Convenience function to substitute variables in text."""
    return get_global_variables().substitute(text)
