"""Trie-based hotstring matcher.

The matcher keeps a rolling buffer of typed characters and checks every
suffix of the buffer against a trie of registered hotstrings.  This gives
O(k) lookup per keystroke where k is the length of the longest hotstring.

Two kinds of match are supported:

*   **Instant** — the hotstring fires as soon as all characters are typed
    (no trigger key needed).
*   **Triggered** — the hotstring fires only when a trigger key (Enter,
    Tab, Space) is pressed after typing.

The AHK original accumulated characters in ``PossibleMatch`` and did
``InStr(pipe_list, "|" + text + "|")`` — O(n) per character.  The trie
is dramatically faster for large dictionaries.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from kodex_py.storage.models import TriggerType


# ── Trie ────────────────────────────────────────────────────────────

class _TrieNode:
    __slots__ = ("children", "match")

    def __init__(self) -> None:
        self.children: dict[str, _TrieNode] = {}
        self.match: MatchResult | None = None


@dataclass(frozen=True)
class MatchResult:
    """Payload stored at a trie leaf — enough to fire the expansion."""

    hotstring_id: int
    name: str
    triggers: frozenset[TriggerType]

    @property
    def is_instant(self) -> bool:
        from kodex_py.storage.models import TriggerType
        return TriggerType.INSTANT in self.triggers


class HotstringMatcher:
    """Feed characters one at a time; get back match results.

    Thread-safety: **not** thread-safe.  Call from the keyboard-hook
    thread only.
    """

    def __init__(self, *, case_sensitive: bool = True) -> None:
        self._root = _TrieNode()
        self._buffer: list[str] = []
        self._case_sensitive = case_sensitive
        # Max hotstring length seen — used to cap the suffix scan.
        self._max_len = 0

    # ── building ────────────────────────────────────────────────────

    def add(self, hotstring: str, hotstring_id: int, triggers: frozenset[TriggerType]) -> None:
        """Register a hotstring in the trie."""
        key = hotstring if self._case_sensitive else hotstring.lower()
        node = self._root
        for ch in key:
            if ch not in node.children:
                node.children[ch] = _TrieNode()
            node = node.children[ch]
        node.match = MatchResult(
            hotstring_id=hotstring_id,
            name=hotstring,
            triggers=triggers,
        )
        if len(key) > self._max_len:
            self._max_len = len(key)

    def remove(self, hotstring: str) -> None:
        """Remove a hotstring from the trie (best-effort, leaves empty branches)."""
        key = hotstring if self._case_sensitive else hotstring.lower()
        node = self._root
        for ch in key:
            if ch not in node.children:
                return
            node = node.children[ch]
        node.match = None

    def rebuild(self, entries: list[tuple[str, int, frozenset[TriggerType]]]) -> None:
        """Clear and re-populate the trie from a list of ``(name, id, triggers)``."""
        self._root = _TrieNode()
        self._max_len = 0
        for name, hid, triggers in entries:
            self.add(name, hid, triggers)

    # ── runtime matching ────────────────────────────────────────────

    def feed(self, char: str) -> MatchResult | None:
        """Append *char* to the buffer and return a match if the buffer
        now ends with an instant hotstring.

        Returns ``None`` if no instant match is found (the buffer is
        still kept for a subsequent ``check_triggered`` call).
        """
        if not self._case_sensitive:
            char = char.lower()
        self._buffer.append(char)

        # Keep buffer bounded
        if len(self._buffer) > self._max_len + 20:
            self._buffer = self._buffer[-(self._max_len + 10) :]

        # Check for instant matches (scan suffixes longest → shortest)
        result = self._suffix_match()
        if result is not None and result.is_instant:
            self._buffer.clear()
            return result
        return None

    def check_triggered(self, trigger: TriggerType) -> MatchResult | None:
        """Called when a trigger key is pressed.  Returns a match if the
        buffer ends with a hotstring that has *trigger* in its trigger set.
        """
        result = self._suffix_match()
        if result is not None and trigger in result.triggers:
            self._buffer.clear()
            return result
        # No match — reset buffer (trigger key acts as word boundary).
        self._buffer.clear()
        return None

    def reset(self) -> None:
        """Clear the typing buffer (e.g. on mouse click or navigation key)."""
        self._buffer.clear()

    @property
    def buffer_text(self) -> str:
        return "".join(self._buffer)

    # ── internals ───────────────────────────────────────────────────

    def _suffix_match(self) -> MatchResult | None:
        """Walk every suffix of the buffer through the trie.

        Returns the **longest** matching hotstring (greedy).  If no suffix
        matches, returns ``None``.
        """
        buf = self._buffer
        best: MatchResult | None = None

        # Start from the longest possible suffix
        start = max(0, len(buf) - self._max_len)
        for i in range(start, len(buf)):
            node = self._root
            matched = True
            for j in range(i, len(buf)):
                ch = buf[j]
                if ch in node.children:
                    node = node.children[ch]
                else:
                    matched = False
                    break
            if matched and node.match is not None:
                # Prefer the longest match
                if best is None or len(node.match.name) > len(best.name):
                    best = node.match

        return best
