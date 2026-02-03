"""Variable token substitution for replacement text.

Tokens (evaluated at expansion time):
    %c   — current clipboard contents
    %t   — short time   (e.g. "2:30 PM")
    %ds  — short date   (e.g. "1/29/2026")
    %dl  — long date    (e.g. "January 29, 2026")
    %tl  — long time    (e.g. "14:30:45 PM")
    %p   — user prompt  (caller must supply the value)
    %|   — cursor position marker (handled by the executor, not here)
"""

from __future__ import annotations

import platform
from datetime import datetime

import pyperclip


def substitute(
    text: str,
    *,
    prompt_value: str | None = None,
    now: datetime | None = None,
) -> str:
    """Replace all variable tokens in *text*.

    ``%p`` is replaced with *prompt_value* when given; if ``%p`` is present
    and *prompt_value* is ``None``, it is left as-is (the caller should
    have already prompted the user).

    ``%|`` is **not** stripped here — the executor needs to see it to
    calculate cursor offset.
    """
    now = now or datetime.now()

    # %c — clipboard
    if "%c" in text:
        try:
            clip = pyperclip.paste() or ""
        except Exception:
            clip = ""
        text = text.replace("%c", clip)

    # %tl — long time HH:mm:ss (must come before %t to avoid substring collision)
    if "%tl" in text:
        text = text.replace("%tl", now.strftime("%H:%M:%S %p"))

    # %t — short time (locale-aware)
    if "%t" in text:
        text = text.replace("%t", _format_short_time(now))

    # %dl — long date (must come before %ds to avoid substring collision)
    if "%dl" in text:
        text = text.replace("%dl", _format_long_date(now))

    # %ds — short date
    if "%ds" in text:
        text = text.replace("%ds", _format_short_date(now))

    # %p — user-supplied prompt value
    if "%p" in text and prompt_value is not None:
        text = text.replace("%p", prompt_value)

    return text


# ── platform-aware formatters ───────────────────────────────────────

def _format_short_time(dt: datetime) -> str:
    """e.g. '2:30 PM'."""
    return dt.strftime("%-I:%M %p") if platform.system() != "Windows" else dt.strftime("%#I:%M %p")


def _format_short_date(dt: datetime) -> str:
    """e.g. '1/29/2026'."""
    if platform.system() == "Windows":
        return dt.strftime("%#m/%#d/%Y")
    return dt.strftime("%-m/%-d/%Y")


def _format_long_date(dt: datetime) -> str:
    """e.g. 'January 29, 2026'."""
    return dt.strftime("%B %d, %Y").replace(" 0", " ")
