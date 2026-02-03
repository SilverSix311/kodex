"""Tests for the hex codec — must match legacy AHK Hexify/DeHexify exactly."""

import pytest
from kodex_py.utils.hex_codec import dehexify, hexify


# ── Known values from the ARCHITECTURE.md documentation ─────────────

KNOWN_PAIRS = [
    ("btw", "627477"),
    ("addr", "61646472"),
    ("::test", "3A3A74657374"),
    ("foo/bar", "666F6F2F626172"),
]


@pytest.mark.parametrize("plain, expected_hex", KNOWN_PAIRS)
def test_hexify_known(plain, expected_hex):
    assert hexify(plain) == expected_hex


@pytest.mark.parametrize("plain, hex_str", KNOWN_PAIRS)
def test_dehexify_known(plain, hex_str):
    assert dehexify(hex_str) == plain


def test_roundtrip_ascii():
    for text in ["hello", "Hello World!", "a.b.c", "foo@bar.com", "test123"]:
        assert dehexify(hexify(text)) == text


def test_roundtrip_special_chars():
    for text in ["::", "//", "C:\\path\\file", "<tag>", "a*b?c"]:
        assert dehexify(hexify(text)) == text


def test_empty_string():
    assert hexify("") == ""
    assert dehexify("") == ""


def test_single_char():
    assert hexify("a") == "61"
    assert dehexify("61") == "a"


def test_uppercase_hex():
    """Legacy format uses uppercase hex digits."""
    result = hexify("A")
    assert result == "41"
    # Ensure all hex digits are uppercase
    result = hexify("{}[]")
    assert result == result.upper()
