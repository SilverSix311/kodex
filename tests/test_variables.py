"""Tests for variable token substitution."""

from datetime import datetime
from unittest.mock import patch

import pytest

from kodex_py.utils.variables import substitute


@pytest.fixture
def fixed_now():
    return datetime(2026, 1, 29, 14, 30, 45)


class TestSubstitute:
    def test_no_tokens(self, fixed_now):
        assert substitute("hello world", now=fixed_now) == "hello world"

    def test_short_time(self, fixed_now):
        result = substitute("Time: %t", now=fixed_now)
        assert "2:30 PM" in result

    def test_short_date(self, fixed_now):
        result = substitute("Date: %ds", now=fixed_now)
        assert "1/29/2026" in result

    def test_long_date(self, fixed_now):
        result = substitute("Date: %dl", now=fixed_now)
        assert "January 29, 2026" in result

    def test_long_time(self, fixed_now):
        result = substitute("Time: %tl", now=fixed_now)
        assert "14:30:45" in result

    def test_clipboard(self, fixed_now):
        with patch("kodex_py.utils.variables.pyperclip.paste", return_value="CLIPBOARD_DATA"):
            result = substitute("Clip: %c", now=fixed_now)
            assert result == "Clip: CLIPBOARD_DATA"

    def test_prompt_replaced(self, fixed_now):
        result = substitute("Hello %p!", prompt_value="World", now=fixed_now)
        assert result == "Hello World!"

    def test_prompt_not_replaced_when_none(self, fixed_now):
        result = substitute("Hello %p!", prompt_value=None, now=fixed_now)
        assert result == "Hello %p!"

    def test_cursor_marker_preserved(self, fixed_now):
        """The %| marker should NOT be removed by substitute."""
        result = substitute("Hello %| World", now=fixed_now)
        assert "%|" in result

    def test_multiple_tokens(self, fixed_now):
        with patch("kodex_py.utils.variables.pyperclip.paste", return_value="clip"):
            result = substitute("%c at %t on %ds", now=fixed_now)
            assert "clip" in result
            assert "2:30 PM" in result
            assert "1/29/2026" in result
