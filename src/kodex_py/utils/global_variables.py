"""Global variables management — user-defined variables with type support.

Variables are stored in ~/.kodex/global_variables.json and can be
substituted in hotstrings using %variable_name% syntax.

Priority: freshdesk_context.json > global_variables.json
(ticket context overrides globals)
"""

from __future__ import annotations

import json
import logging
import os
import re
import threading
from pathlib import Path
from typing import Any, Callable

log = logging.getLogger(__name__)

# Supported variable types
VARIABLE_TYPES = ("string", "int", "decimal", "boolean", "array", "dict")

# Pattern to match %variable_name% (non-greedy, alphanumeric + underscore)
VARIABLE_PATTERN = re.compile(r"%([a-zA-Z_][a-zA-Z0-9_]*)%")


class GlobalVariables:
    """Manages global variables with file persistence and change watching."""

    def __init__(self, data_dir: Path | None = None) -> None:
        from kodex_py.config import get_data_dir
        
        self._data_dir = data_dir or get_data_dir()
        self._variables_file = self._data_dir / "global_variables.json"
        self._freshdesk_file = self._data_dir / "freshdesk_context.json"
        
        self._variables: dict[str, dict[str, Any]] = {}
        self._freshdesk_context: dict[str, Any] = {}
        
        self._watcher_thread: threading.Thread | None = None
        self._stop_watching = threading.Event()
        self._on_change_callbacks: list[Callable[[], None]] = []
        
        self._last_vars_mtime: float = 0
        self._last_freshdesk_mtime: float = 0
        
        self.load()

    # ── File operations ─────────────────────────────────────────────

    def load(self) -> None:
        """Load variables from both files."""
        self._load_global_variables()
        self._load_freshdesk_context()

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

    def _load_freshdesk_context(self) -> None:
        """Load freshdesk_context.json if it exists."""
        if self._freshdesk_file.exists():
            try:
                with open(self._freshdesk_file, "r", encoding="utf-8") as f:
                    self._freshdesk_context = json.load(f)
                self._last_freshdesk_mtime = os.path.getmtime(self._freshdesk_file)
                log.info("Loaded freshdesk context with %d fields", len(self._freshdesk_context))
            except (json.JSONDecodeError, OSError) as e:
                log.debug("Failed to load freshdesk_context.json: %s", e)
                self._freshdesk_context = {}
        else:
            self._freshdesk_context = {}

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

    # ── Variable CRUD ───────────────────────────────────────────────

    def get(self, name: str) -> Any:
        """Get a variable value (freshdesk_context overrides globals)."""
        # Check freshdesk context first (higher priority)
        if name in self._freshdesk_context:
            return self._freshdesk_context[name]
        
        # Then check global variables
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

    def get_freshdesk_context(self) -> dict[str, Any]:
        """Return current freshdesk context."""
        return dict(self._freshdesk_context)

    # ── Substitution ────────────────────────────────────────────────

    def substitute(self, text: str) -> str:
        """Replace %variable_name% tokens with their values.
        
        Priority: freshdesk_context > global_variables
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
            name="GlobalVariablesWatcher"
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
        """Background thread that checks for file changes."""
        while not self._stop_watching.wait(timeout=2.0):
            changed = False
            
            # Check global_variables.json
            if self._variables_file.exists():
                try:
                    mtime = os.path.getmtime(self._variables_file)
                    if mtime > self._last_vars_mtime:
                        self._load_global_variables()
                        changed = True
                except OSError:
                    pass
            
            # Check freshdesk_context.json
            if self._freshdesk_file.exists():
                try:
                    mtime = os.path.getmtime(self._freshdesk_file)
                    if mtime > self._last_freshdesk_mtime:
                        self._load_freshdesk_context()
                        changed = True
                except OSError:
                    pass
            elif self._freshdesk_context:
                # File was deleted, clear context
                self._freshdesk_context = {}
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
