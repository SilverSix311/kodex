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


def type_text(
    text: str, 
    *, 
    char_delay: float = 0.008,
    chunk_size: int = 30, 
    inter_chunk_delay: float = 0.02
) -> None:
    """Type *text* character-by-character using pynput.

    For smoothness we send characters with a small delay between them
    and a longer pause between chunks so the target app can keep up.

    ``char_delay`` — seconds between each character (default 8ms)
    ``chunk_size`` — characters before a longer pause (default 30)
    ``inter_chunk_delay`` — pause between chunks (default 20ms)
    """
    ctrl = _get_controller()
    for i, ch in enumerate(text):
        ctrl.type(ch)
        # Small delay after each character
        if char_delay > 0:
            time.sleep(char_delay)
        # Longer pause between chunks
        if (i + 1) % chunk_size == 0 and i + 1 < len(text):
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
