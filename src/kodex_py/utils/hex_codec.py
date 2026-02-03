"""Hex encoding / decoding — backward-compatible with the legacy AHK Hexify/DeHexify.

The legacy format converts each **byte** of the ASCII representation to two
uppercase hex digits.  Multi-byte (non-ASCII) characters are NOT safely
round-tripped in the original AHK code — we replicate that behaviour for
migration fidelity but warn on such characters.
"""

from __future__ import annotations

import logging

log = logging.getLogger(__name__)


def hexify(text: str) -> str:
    """Encode *text* to the legacy hex format (2 uppercase hex digits per char).

    >>> hexify("btw")
    '627477'
    >>> hexify("addr")
    '61646472'
    >>> hexify("::test")
    '3A3A74657374'
    """
    parts: list[str] = []
    for ch in text:
        code = ord(ch)
        if code > 255:
            log.warning("Non-ASCII character U+%04X in '%s' — hex encoding may not round-trip", code, text)
        parts.append(f"{code:02X}")
    return "".join(parts)


def dehexify(hex_str: str) -> str:
    """Decode a legacy hex-encoded string back to plaintext.

    >>> dehexify('627477')
    'btw'
    >>> dehexify('61646472')
    'addr'
    """
    chars: list[str] = []
    for i in range(0, len(hex_str), 2):
        code = int(hex_str[i : i + 2], 16)
        chars.append(chr(code))
    return "".join(chars)
