"""Variable token substitution for replacement text.

Tokens (evaluated at expansion time):
    %clipboard%   — current clipboard contents
    %time%        — short time   (e.g. "2:30 PM")
    %time_long%   — long time    (e.g. "14:30:45 PM")
    %date_short%  — short date   (e.g. "1/29/2026")
    %date_long%   — long date    (e.g. "January 29, 2026")
    %prompt%      — user prompt  (caller must supply the value)
    %cursor%      — cursor position marker (handled by the executor, not here)
    %name%        — global/ticket variable (see global_variables.py)
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

    ``%prompt%`` is replaced with *prompt_value* when given; if ``%prompt%`` 
    is present and *prompt_value* is ``None``, it is left as-is (the caller 
    should have already prompted the user).

    ``%cursor%`` is **not** stripped here — the executor needs to see it to
    calculate cursor offset.

    Global/ticket variables (``%var_name%``) are also substituted.
    Priority: freshdesk_context > global_variables
    """
    now = now or datetime.now()

    # %clipboard% — clipboard contents
    if "%clipboard%" in text:
        try:
            clip = pyperclip.paste() or ""
        except Exception:
            clip = ""
        text = text.replace("%clipboard%", clip)

    # %time_long% — long time HH:mm:ss
    if "%time_long%" in text:
        text = text.replace("%time_long%", now.strftime("%H:%M:%S %p"))

    # %time% — short time (locale-aware)
    if "%time%" in text:
        text = text.replace("%time%", _format_short_time(now))

    # %date_long% — long date
    if "%date_long%" in text:
        text = text.replace("%date_long%", _format_long_date(now))

    # %date_short% — short date
    if "%date_short%" in text:
        text = text.replace("%date_short%", _format_short_date(now))

    # %prompt% — user-supplied prompt value
    if "%prompt%" in text and prompt_value is not None:
        text = text.replace("%prompt%", prompt_value)

    # Global/ticket variables (%var_name%)
    text = _substitute_global_variables(text)

    return text


def _substitute_global_variables(text: str) -> str:
    """Substitute global and ticket variables in text."""
    try:
        from kodex_py.utils.global_variables import substitute_global_variables
        return substitute_global_variables(text)
    except Exception:
        # If global variables module fails, return text as-is
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
