"""Data models for Kodex."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class TriggerType(Enum):
    """Which key finalises the hotstring match."""

    ENTER = "enter"
    TAB = "tab"
    SPACE = "space"
    INSTANT = "instant"  # fires immediately (no trigger key needed)


class SendMode(Enum):
    """How the replacement text is injected."""

    DIRECT = 0   # Keystroke injection via pynput (Mode 0 — "compatibility")
    CLIPBOARD = 1  # Paste via Ctrl+V (Mode 1 — "clipboard")


@dataclass
class Hotstring:
    """A single text-expansion rule."""

    id: int | None = None
    name: str = ""
    replacement: str = ""
    is_script: bool = False
    bundle_id: int | None = None
    bundle_name: str = ""          # convenience field, not stored directly
    triggers: set[TriggerType] = field(default_factory=set)
    created_at: datetime | None = None
    updated_at: datetime | None = None

    # ── helpers ──────────────────────────────────────────────────────
    @property
    def is_instant(self) -> bool:
        return TriggerType.INSTANT in self.triggers


@dataclass
class Bundle:
    """A named collection of hotstrings (category / folder)."""

    id: int | None = None
    name: str = ""
    enabled: bool = True


@dataclass
class AppConfig:
    """Runtime configuration (mirrors kodex.ini)."""

    send_mode: SendMode = SendMode.DIRECT
    play_sound: bool = True
    autocorrect_enabled: bool = False
    run_at_startup: bool = False
    hotkey_create: str = "ctrl+shift+h"
    hotkey_manage: str = "ctrl+shift+m"
    hotkey_disable: str = ""
    hotkey_tracker: str = "ctrl+shift+t"
    # stats
    expanded: int = 0
    chars_saved: int = 0


@dataclass
class TimeEntry:
    """A Freshdesk ticket time-tracking record."""

    id: int | None = None
    ticket_number: str = ""
    status: str = ""          # "Started" | "Finished"
    timestamp: datetime | None = None
    duration_hours: float | None = None
    username: str = ""
