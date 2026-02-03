"""Tests for the executor — mocks out pynput so we can test logic only."""

from unittest.mock import MagicMock, patch, call

import pytest

from kodex_py.engine.executor import execute
from kodex_py.storage.models import SendMode


@pytest.fixture(autouse=True)
def mock_sender():
    """Mock the sender module so no real keystrokes are sent."""
    with patch("kodex_py.engine.executor.sender") as mock:
        yield mock


class TestExecute:
    def test_basic_expansion(self, mock_sender):
        result = execute("btw", "by the way", send_mode=SendMode.DIRECT)
        assert result is True
        mock_sender.send_backspaces.assert_called_once_with(3)
        mock_sender.type_text.assert_called_once_with("by the way")

    def test_cursor_positioning(self, mock_sender):
        result = execute("sig", "Hello %| World", send_mode=SendMode.DIRECT)
        assert result is True
        mock_sender.type_text.assert_called_once_with("Hello  World")
        mock_sender.move_cursor_left.assert_called_once_with(6)  # len(" World")

    def test_clipboard_mode(self, mock_sender):
        result = execute("btw", "by the way", send_mode=SendMode.CLIPBOARD)
        assert result is True
        mock_sender.paste_text.assert_called_once_with("by the way")

    def test_script_mode(self, mock_sender):
        result = execute("cmd", "print('hi')", is_script=True, send_mode=SendMode.DIRECT)
        assert result is True
        mock_sender.type_text.assert_called_once_with("print('hi')")

    def test_prompt_callback(self, mock_sender):
        prompt_fn = MagicMock(return_value="user input")
        result = execute("x", "Hello %p!", prompt_fn=prompt_fn, send_mode=SendMode.DIRECT)
        assert result is True
        prompt_fn.assert_called_once()
        # Should contain "user input" in the typed text
        typed = mock_sender.type_text.call_args[0][0]
        assert "user input" in typed

    def test_prompt_cancelled(self, mock_sender):
        prompt_fn = MagicMock(return_value=None)
        result = execute("x", "Hello %p!", prompt_fn=prompt_fn, send_mode=SendMode.DIRECT)
        assert result is False
        mock_sender.type_text.assert_not_called()

    def test_stats_callback(self, mock_sender):
        stats_fn = MagicMock()
        execute("btw", "by the way", stats_fn=stats_fn, send_mode=SendMode.DIRECT)
        stats_fn.assert_called_once_with(10)

    def test_crlf_normalized_in_direct_mode(self, mock_sender):
        execute("x", "line1\r\nline2", send_mode=SendMode.DIRECT)
        typed = mock_sender.type_text.call_args[0][0]
        assert "\r\n" not in typed
        assert "\n" in typed

    def test_sound_played(self, mock_sender):
        with patch("kodex_py.engine.executor._play_sound") as mock_sound:
            execute("x", "y", play_sound=True, sound_path="/tmp/test.wav", send_mode=SendMode.DIRECT)
            mock_sound.assert_called_once_with("/tmp/test.wav")
