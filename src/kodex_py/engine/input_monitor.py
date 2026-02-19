"""Keyboard hook — listens for keystrokes and drives the matcher + executor.

Uses ``pynput.keyboard.Listener`` which runs its own daemon thread.
The monitor bridges the gap between raw key events and the high-level
matcher / executor pipeline.

Design notes
~~~~~~~~~~~~
*   The AHK original used a while-true ``Input()`` loop that captured
    one character at a time.  ``pynput``'s callback model is inherently
    lower-latency because there's no polling.
*   Mouse clicks reset the buffer (same as AHK ``~LButton``/``~RButton``
    handlers).
*   Navigation keys (arrows, Home, End, PgUp, PgDn, Esc, F-keys) reset
    the buffer — they indicate the user moved the cursor away.
"""

from __future__ import annotations

import logging
import threading
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from kodex_py.engine.matcher import HotstringMatcher, MatchResult
    from kodex_py.storage.models import SendMode

log = logging.getLogger(__name__)

# Keys that should reset the typing buffer (same as AHK's EndKeys minus
# the trigger keys which are handled separately).
_RESET_KEYS: set[str] = {
    "esc", "left", "right", "up", "down",
    "home", "end", "page_up", "page_down", "delete",
    "f1", "f2", "f3", "f4", "f5", "f6",
    "f7", "f8", "f9", "f10", "f11", "f12",
}


class InputMonitor:
    """Keyboard hook that feeds characters into a :class:`HotstringMatcher`
    and fires expansions via a callback.

    Parameters
    ----------
    matcher:
        The trie-based hotstring matcher.
    on_match:
        Called with ``(match_result, trigger_type_or_None)`` whenever a
        hotstring is matched.  The callback should call ``executor.execute``
        or equivalent.
    """

    def __init__(
        self,
        matcher: HotstringMatcher,
        on_match: Callable[[MatchResult, str | None], None],
    ) -> None:
        self._matcher = matcher
        self._on_match = on_match
        self._disabled = False
        self._kb_listener = None
        self._mouse_listener = None
        self._lock = threading.Lock()

    # ── lifecycle ───────────────────────────────────────────────────

    def start(self) -> None:
        from pynput import keyboard, mouse

        self._kb_listener = keyboard.Listener(
            on_press=self._on_key_press,
            on_release=self._on_key_release,
        )
        self._mouse_listener = mouse.Listener(on_click=self._on_mouse_click)

        self._kb_listener.start()
        self._mouse_listener.start()
        log.info("Input monitor started")

    def stop(self) -> None:
        if self._kb_listener:
            self._kb_listener.stop()
            try:
                self._kb_listener.join(timeout=0.5)
            except Exception:
                pass
        if self._mouse_listener:
            self._mouse_listener.stop()
            try:
                self._mouse_listener.join(timeout=0.5)
            except Exception:
                pass
        log.info("Input monitor stopped")

    @property
    def disabled(self) -> bool:
        return self._disabled

    @disabled.setter
    def disabled(self, value: bool) -> None:
        self._disabled = value
        if value:
            self._matcher.reset()

    # ── keyboard callbacks ──────────────────────────────────────────

    def _on_key_press(self, key) -> None:
        if self._disabled:
            return

        from pynput.keyboard import Key
        from kodex_py.storage.models import TriggerType

        # Trigger keys
        trigger_map = {
            Key.enter: TriggerType.ENTER,
            Key.tab: TriggerType.TAB,
            Key.space: TriggerType.SPACE,
        }

        if key in trigger_map:
            trigger = trigger_map[key]
            match = self._matcher.check_triggered(trigger)
            if match:
                self._on_match(match, trigger.value)
            return

        # Reset keys
        key_name = self._key_name(key)
        if key_name in _RESET_KEYS:
            self._matcher.reset()
            return

        # Modifier keys — ignore (don't reset, don't feed)
        if key_name in ("shift", "shift_r", "ctrl_l", "ctrl_r",
                        "alt_l", "alt_r", "cmd", "cmd_r"):
            return

        # Backspace — trim buffer
        if key_name == "backspace":
            buf = list(self._matcher.buffer_text)
            if buf:
                buf.pop()
                # Hacky but effective: reset and re-feed
                self._matcher.reset()
                for ch in buf:
                    self._matcher.feed(ch)
            return

        # Printable character
        try:
            char = key.char
        except AttributeError:
            char = None

        if char:
            match = self._matcher.feed(char)
            if match:
                self._on_match(match, None)

    def _on_key_release(self, key) -> None:
        pass  # not needed

    # ── mouse callbacks ─────────────────────────────────────────────

    def _on_mouse_click(self, x, y, button, pressed) -> None:
        """Any mouse click resets the buffer (same as AHK ``~LButton`` etc.)."""
        if pressed:
            self._matcher.reset()

    # ── helpers ─────────────────────────────────────────────────────

    @staticmethod
    def _key_name(key) -> str:
        """Normalise a pynput key to a lowercase name string."""
        try:
            return key.name.lower()
        except AttributeError:
            return str(key).lower()
