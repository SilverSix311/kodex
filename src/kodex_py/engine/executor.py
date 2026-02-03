"""Expansion executor — handles variable substitution, cursor positioning,
script mode, backspace erasure, and final text injection.

This is the equivalent of the ``Execute()`` function in the original
AHK ``kodex.ahk``.
"""

from __future__ import annotations

import logging
import os
import platform
from typing import Callable

from kodex_py.storage.models import SendMode
from kodex_py.utils.variables import substitute

from . import sender

log = logging.getLogger(__name__)

# Callback type for prompting the user when ``%p`` is encountered.
PromptCallback = Callable[[str], str | None]


def execute(
    hotstring_name: str,
    replacement: str,
    *,
    is_script: bool = False,
    send_mode: SendMode = SendMode.DIRECT,
    play_sound: bool = False,
    sound_path: str | None = None,
    prompt_fn: PromptCallback | None = None,
    stats_fn: Callable[[int], None] | None = None,
    trigger_char: bool = False,
) -> bool:
    """Fire a hotstring expansion.

    1.  Send backspaces to erase the typed hotstring.
    2.  Perform variable substitution.
    3.  Inject the replacement text.
    4.  Position the cursor if ``%|`` was present.
    5.  Update stats.

    Returns ``True`` on success, ``False`` if cancelled (e.g. user
    dismissed the ``%p`` prompt).
    """

    # ── sound ───────────────────────────────────────────────────────
    if play_sound and sound_path:
        _play_sound(sound_path)

    # ── erase the typed hotstring ───────────────────────────────────
    # +1 for the trigger character (space/tab/enter) which was already
    # typed into the active field before the match callback fires.
    erase_count = len(hotstring_name) + (1 if trigger_char else 0)
    sender.send_backspaces(erase_count)

    # ── handle script mode (::scr::) ───────────────────────────────
    if is_script:
        text = replacement
        if "%p" in text and prompt_fn:
            result = prompt_fn(text)
            if result is None:
                return False
            text = text.replace("%p", result)
        # Script mode in AHK just SendInput'd the text raw — we replicate
        sender.type_text(text)
        return True

    # ── variable substitution ───────────────────────────────────────
    text = replacement

    # Normalise line endings for direct mode
    if send_mode == SendMode.DIRECT:
        text = text.replace("\r\n", "\n")

    # Prompt (%p) — must happen before other substitutions so the
    # user sees the raw template.
    prompt_value: str | None = None
    if "%p" in text:
        if prompt_fn:
            prompt_value = prompt_fn(text)
            if prompt_value is None:
                return False  # user cancelled
        else:
            prompt_value = ""

    text = substitute(text, prompt_value=prompt_value)

    # ── cursor positioning (%|) ─────────────────────────────────────
    return_to = 0
    if "%|" in text:
        cursor_pos = text.index("%|")
        text = text.replace("%|", "")
        return_to = len(text) - cursor_pos

    # ── inject ──────────────────────────────────────────────────────
    if send_mode == SendMode.DIRECT:
        sender.type_text(text)
        if return_to > 0:
            sender.move_cursor_left(return_to)
    else:
        sender.paste_text(text)
        if return_to > 0:
            sender.move_cursor_left(return_to)

    # ── stats callback ──────────────────────────────────────────────
    if stats_fn:
        stats_fn(len(text))

    return True


# ── helpers ─────────────────────────────────────────────────────────

def _play_sound(path: str) -> None:
    """Play expansion feedback sound (fire-and-forget)."""
    try:
        if platform.system() == "Windows":
            import winsound
            winsound.PlaySound(path, winsound.SND_FILENAME | winsound.SND_ASYNC)
        else:
            # Best-effort on other platforms
            os.system(f'aplay "{path}" &>/dev/null &')
    except Exception:
        log.debug("Failed to play sound %s", path, exc_info=True)
