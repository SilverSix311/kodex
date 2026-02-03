"""Tests for the trie-based hotstring matcher."""

import pytest
from kodex_py.engine.matcher import HotstringMatcher, MatchResult
from kodex_py.storage.models import TriggerType


@pytest.fixture
def matcher():
    m = HotstringMatcher()
    m.add("btw", 1, frozenset({TriggerType.SPACE, TriggerType.ENTER}))
    m.add("addr", 2, frozenset({TriggerType.SPACE}))
    m.add("sig", 3, frozenset({TriggerType.INSTANT}))
    m.add("omw", 4, frozenset({TriggerType.TAB}))
    return m


class TestFeed:
    def test_instant_match(self, matcher):
        """Instant hotstrings fire as soon as all chars are typed."""
        assert matcher.feed("s") is None
        assert matcher.feed("i") is None
        result = matcher.feed("g")
        assert result is not None
        assert result.hotstring_id == 3
        assert result.name == "sig"
        assert result.is_instant

    def test_no_instant_for_triggered(self, matcher):
        """Triggered hotstrings should NOT fire from feed() alone."""
        for ch in "btw":
            result = matcher.feed(ch)
        # "btw" is space/enter triggered, not instant
        assert result is None

    def test_buffer_cleared_after_instant(self, matcher):
        """After an instant match, buffer is cleared for next match."""
        for ch in "sig":
            matcher.feed(ch)
        # Buffer should be empty now — feed "sig" again
        for ch in "si":
            assert matcher.feed(ch) is None
        assert matcher.feed("g").hotstring_id == 3


class TestCheckTriggered:
    def test_space_trigger(self, matcher):
        for ch in "btw":
            matcher.feed(ch)
        result = matcher.check_triggered(TriggerType.SPACE)
        assert result is not None
        assert result.hotstring_id == 1

    def test_enter_trigger(self, matcher):
        for ch in "btw":
            matcher.feed(ch)
        result = matcher.check_triggered(TriggerType.ENTER)
        assert result is not None
        assert result.hotstring_id == 1

    def test_wrong_trigger_no_match(self, matcher):
        """'addr' is only triggered by space, not tab."""
        for ch in "addr":
            matcher.feed(ch)
        assert matcher.check_triggered(TriggerType.TAB) is None

    def test_correct_trigger(self, matcher):
        for ch in "addr":
            matcher.feed(ch)
        assert matcher.check_triggered(TriggerType.SPACE).hotstring_id == 2

    def test_no_match_resets_buffer(self, matcher):
        for ch in "xyz":
            matcher.feed(ch)
        assert matcher.check_triggered(TriggerType.SPACE) is None
        # Buffer should be cleared after trigger attempt
        assert matcher.buffer_text == ""

    def test_tab_trigger(self, matcher):
        for ch in "omw":
            matcher.feed(ch)
        result = matcher.check_triggered(TriggerType.TAB)
        assert result is not None
        assert result.hotstring_id == 4


class TestReset:
    def test_reset_clears_buffer(self, matcher):
        for ch in "bt":
            matcher.feed(ch)
        matcher.reset()
        assert matcher.buffer_text == ""

    def test_reset_prevents_match(self, matcher):
        matcher.feed("b")
        matcher.feed("t")
        matcher.reset()
        matcher.feed("w")
        # Should not match "btw" because buffer was reset
        assert matcher.check_triggered(TriggerType.SPACE) is None


class TestRebuild:
    def test_rebuild_replaces_entries(self, matcher):
        matcher.rebuild([
            ("new", 10, frozenset({TriggerType.SPACE})),
        ])
        # Old entries gone
        for ch in "btw":
            matcher.feed(ch)
        assert matcher.check_triggered(TriggerType.SPACE) is None

        # New entry works
        matcher.reset()
        for ch in "new":
            matcher.feed(ch)
        assert matcher.check_triggered(TriggerType.SPACE).hotstring_id == 10


class TestSuffixMatching:
    def test_match_at_end_of_longer_input(self):
        """If user types 'xyzbtw', should still match 'btw'."""
        m = HotstringMatcher()
        m.add("btw", 1, frozenset({TriggerType.SPACE}))
        for ch in "xyzbtw":
            m.feed(ch)
        result = m.check_triggered(TriggerType.SPACE)
        assert result is not None
        assert result.hotstring_id == 1

    def test_longest_match_wins(self):
        """If 'tw' and 'btw' are both registered, 'btw' should win."""
        m = HotstringMatcher()
        m.add("tw", 1, frozenset({TriggerType.SPACE}))
        m.add("btw", 2, frozenset({TriggerType.SPACE}))
        for ch in "btw":
            m.feed(ch)
        result = m.check_triggered(TriggerType.SPACE)
        assert result is not None
        assert result.hotstring_id == 2


class TestCaseSensitivity:
    def test_case_sensitive_no_match(self):
        m = HotstringMatcher(case_sensitive=True)
        m.add("btw", 1, frozenset({TriggerType.SPACE}))
        for ch in "BTW":
            m.feed(ch)
        assert m.check_triggered(TriggerType.SPACE) is None

    def test_case_insensitive_match(self):
        m = HotstringMatcher(case_sensitive=False)
        m.add("btw", 1, frozenset({TriggerType.SPACE}))
        for ch in "BTW":
            m.feed(ch)
        assert m.check_triggered(TriggerType.SPACE).hotstring_id == 1
