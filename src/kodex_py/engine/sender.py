"""Text injection — sends replacement text to the active window.

Two modes, matching the original AHK behaviour:

*   **DIRECT** (Mode 0) — types each character via ``pynput``'s
    ``keyboard.Controller``.  No clipboard involvement.  For large
    multi-paragraph replacements we chunk the text and yield briefly
    between chunks to keep the event queue responsive.

*   **CLIPBOARD** (Mode 1) — saves current clipboard, sets replacement
    text, sends Ctrl+V, restores clipboard.

The DIRECT mode is the *preferred* path.  It avoids clobbering the
user's clipboard and works in more contexts (editors that intercept
paste, remote desktops, etc.).
"""

from __future__ import annotations

import logging
import platform
import time
from enum import Enum

log = logging.getLogger(__name__)

# Lazy-import pynput so tests that don't need a real keyboard can still
# import this module.
_controller = None


def _get_controller():
    global _controller
    if _controller is None:
        from pynput.keyboard import Controller
        _controller = Controller()
    return _controller


# ── public API ──────────────────────────────────────────────────────

def send_backspaces(count: int) -> None:
    """Erase *count* characters by sending Backspace."""
    if count <= 0:
        return
    from pynput.keyboard import Key
    ctrl = _get_controller()
    for _ in range(count):
        ctrl.press(Key.backspace)
        ctrl.release(Key.backspace)


def type_text(text: str, *, chunk_size: int = 50, inter_chunk_delay: float = 0.005) -> None:
    """Type *text* character-by-character using pynput.

    For smoothness we send characters in small chunks with a tiny sleep
    between them so the OS input queue doesn't stall.

    ``chunk_size`` and ``inter_chunk_delay`` are tuned for Windows;
    adjust for other platforms if needed.
    """
    ctrl = _get_controller()
    for i in range(0, len(text), chunk_size):
        chunk = text[i : i + chunk_size]
        for ch in chunk:
            ctrl.type(ch)
        if i + chunk_size < len(text):
            time.sleep(inter_chunk_delay)


def paste_text(text: str) -> None:
    """Paste *text* via the clipboard (Mode 1).

    Saves and restores the user's clipboard.
    """
    import pyperclip
    from pynput.keyboard import Controller, Key

    ctrl = _get_controller()

    # Save
    try:
        old_clip = pyperclip.paste()
    except Exception:
        old_clip = ""

    # Set + paste
    pyperclip.copy(text)
    time.sleep(0.02)
    with ctrl.pressed(Key.ctrl):
        ctrl.press("v")
        ctrl.release("v")
    time.sleep(0.15)

    # Restore
    try:
        pyperclip.copy(old_clip)
    except Exception:
        pass


def move_cursor_left(count: int) -> None:
    """Send *count* Left-arrow presses (for ``%|`` cursor positioning)."""
    if count <= 0:
        return
    from pynput.keyboard import Key
    ctrl = _get_controller()
    for _ in range(count):
        ctrl.press(Key.left)
        ctrl.release(Key.left)
