"""SQLite storage layer — replaces the legacy file-per-hotstring architecture.

Schema overview:
    bundles    — named collections (Default, WorkStuff, …)
    hotstrings — individual expansion rules
    triggers   — many-to-many: which trigger types activate each hotstring
    config     — key/value app settings
    stats      — expansion statistics
"""

from __future__ import annotations

import logging
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Iterator

from kodex_py.storage.models import Bundle, Hotstring, TriggerType

log = logging.getLogger(__name__)

_SCHEMA = """\
CREATE TABLE IF NOT EXISTS bundles (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    name     TEXT NOT NULL UNIQUE,
    enabled  INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS hotstrings (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    name         TEXT NOT NULL,
    replacement  TEXT NOT NULL DEFAULT '',
    is_script    INTEGER NOT NULL DEFAULT 0,
    bundle_id    INTEGER NOT NULL REFERENCES bundles(id) ON DELETE CASCADE,
    created_at   TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at   TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(name, bundle_id)
);

CREATE TABLE IF NOT EXISTS triggers (
    hotstring_id  INTEGER NOT NULL REFERENCES hotstrings(id) ON DELETE CASCADE,
    trigger_type  TEXT NOT NULL CHECK(trigger_type IN ('enter','tab','space','instant')),
    PRIMARY KEY (hotstring_id, trigger_type)
);

CREATE TABLE IF NOT EXISTS config (
    key    TEXT PRIMARY KEY,
    value  TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS stats (
    key    TEXT PRIMARY KEY,
    value  INTEGER NOT NULL DEFAULT 0
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_hotstrings_bundle ON hotstrings(bundle_id);
CREATE INDEX IF NOT EXISTS idx_hotstrings_name   ON hotstrings(name);
CREATE INDEX IF NOT EXISTS idx_triggers_hs       ON triggers(hotstring_id);
"""


class Database:
    """Thin wrapper around an SQLite database for Kodex data."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: sqlite3.Connection | None = None

    # ── connection management ───────────────────────────────────────

    def open(self) -> None:
        self._conn = sqlite3.connect(str(self.path), check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._conn.executescript(_SCHEMA)
        self._conn.commit()
        self._ensure_defaults()

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    @contextmanager
    def _tx(self) -> Iterator[sqlite3.Cursor]:
        assert self._conn is not None, "Database not open"
        cur = self._conn.cursor()
        try:
            yield cur
            self._conn.commit()
        except Exception:
            self._conn.rollback()
            raise

    # ── bundles ─────────────────────────────────────────────────────

    def create_bundle(self, name: str, enabled: bool = True) -> Bundle:
        with self._tx() as cur:
            cur.execute(
                "INSERT OR IGNORE INTO bundles (name, enabled) VALUES (?, ?)",
                (name, int(enabled)),
            )
            cur.execute("SELECT id, name, enabled FROM bundles WHERE name = ?", (name,))
            row = cur.fetchone()
        return Bundle(id=row[0], name=row[1], enabled=bool(row[2]))

    def get_bundles(self) -> list[Bundle]:
        assert self._conn
        cur = self._conn.execute("SELECT id, name, enabled FROM bundles ORDER BY name")
        return [Bundle(id=r[0], name=r[1], enabled=bool(r[2])) for r in cur.fetchall()]

    def set_bundle_enabled(self, bundle_id: int, enabled: bool) -> None:
        with self._tx() as cur:
            cur.execute("UPDATE bundles SET enabled = ? WHERE id = ?", (int(enabled), bundle_id))

    def delete_bundle(self, bundle_id: int) -> None:
        with self._tx() as cur:
            cur.execute("DELETE FROM bundles WHERE id = ?", (bundle_id,))

    def get_bundle_by_name(self, name: str) -> Bundle | None:
        assert self._conn
        cur = self._conn.execute("SELECT id, name, enabled FROM bundles WHERE name = ?", (name,))
        row = cur.fetchone()
        if row is None:
            return None
        return Bundle(id=row[0], name=row[1], enabled=bool(row[2]))

    # ── hotstrings ──────────────────────────────────────────────────

    def save_hotstring(self, hs: Hotstring) -> Hotstring:
        """Insert or update a hotstring.  Triggers are replaced wholesale."""
        with self._tx() as cur:
            if hs.id is not None:
                cur.execute(
                    "UPDATE hotstrings SET name=?, replacement=?, is_script=?, "
                    "bundle_id=?, updated_at=datetime('now') WHERE id=?",
                    (hs.name, hs.replacement, int(hs.is_script), hs.bundle_id, hs.id),
                )
                hid = hs.id
            else:
                cur.execute(
                    "INSERT INTO hotstrings (name, replacement, is_script, bundle_id) "
                    "VALUES (?, ?, ?, ?)",
                    (hs.name, hs.replacement, int(hs.is_script), hs.bundle_id),
                )
                hid = cur.lastrowid

            # Replace triggers
            cur.execute("DELETE FROM triggers WHERE hotstring_id = ?", (hid,))
            for t in hs.triggers:
                cur.execute(
                    "INSERT INTO triggers (hotstring_id, trigger_type) VALUES (?, ?)",
                    (hid, t.value),
                )
        hs.id = hid
        return hs

    def delete_hotstring(self, hotstring_id: int) -> None:
        with self._tx() as cur:
            cur.execute("DELETE FROM hotstrings WHERE id = ?", (hotstring_id,))

    def get_hotstring(self, hotstring_id: int) -> Hotstring | None:
        assert self._conn
        cur = self._conn.execute(
            "SELECT h.id, h.name, h.replacement, h.is_script, h.bundle_id, "
            "b.name, h.created_at, h.updated_at "
            "FROM hotstrings h JOIN bundles b ON h.bundle_id = b.id "
            "WHERE h.id = ?",
            (hotstring_id,),
        )
        row = cur.fetchone()
        if row is None:
            return None
        return self._row_to_hotstring(row)

    def get_hotstring_by_name(self, name: str, bundle_id: int) -> Hotstring | None:
        assert self._conn
        cur = self._conn.execute(
            "SELECT h.id, h.name, h.replacement, h.is_script, h.bundle_id, "
            "b.name, h.created_at, h.updated_at "
            "FROM hotstrings h JOIN bundles b ON h.bundle_id = b.id "
            "WHERE h.name = ? AND h.bundle_id = ?",
            (name, bundle_id),
        )
        row = cur.fetchone()
        if row is None:
            return None
        return self._row_to_hotstring(row)

    def get_hotstrings(self, *, bundle_id: int | None = None, enabled_only: bool = False) -> list[Hotstring]:
        """Return hotstrings, optionally filtered by bundle or enabled bundles."""
        assert self._conn
        query = (
            "SELECT h.id, h.name, h.replacement, h.is_script, h.bundle_id, "
            "b.name, h.created_at, h.updated_at "
            "FROM hotstrings h JOIN bundles b ON h.bundle_id = b.id"
        )
        params: list = []
        clauses: list[str] = []
        if bundle_id is not None:
            clauses.append("h.bundle_id = ?")
            params.append(bundle_id)
        if enabled_only:
            clauses.append("b.enabled = 1")
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY h.name"

        results: list[Hotstring] = []
        for row in self._conn.execute(query, params).fetchall():
            results.append(self._row_to_hotstring(row))
        return results

    def _row_to_hotstring(self, row) -> Hotstring:
        hid = row[0]
        triggers = self._get_triggers(hid)
        return Hotstring(
            id=hid,
            name=row[1],
            replacement=row[2],
            is_script=bool(row[3]),
            bundle_id=row[4],
            bundle_name=row[5],
            triggers=triggers,
            created_at=_parse_dt(row[6]),
            updated_at=_parse_dt(row[7]),
        )

    def _get_triggers(self, hotstring_id: int) -> set[TriggerType]:
        assert self._conn
        cur = self._conn.execute(
            "SELECT trigger_type FROM triggers WHERE hotstring_id = ?",
            (hotstring_id,),
        )
        return {TriggerType(r[0]) for r in cur.fetchall()}

    # ── config ──────────────────────────────────────────────────────

    def get_config(self, key: str, default: str = "") -> str:
        assert self._conn
        cur = self._conn.execute("SELECT value FROM config WHERE key = ?", (key,))
        row = cur.fetchone()
        return row[0] if row else default

    def set_config(self, key: str, value: str) -> None:
        with self._tx() as cur:
            cur.execute(
                "INSERT INTO config (key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, value),
            )

    # ── stats ───────────────────────────────────────────────────────

    def get_stat(self, key: str) -> int:
        assert self._conn
        cur = self._conn.execute("SELECT value FROM stats WHERE key = ?", (key,))
        row = cur.fetchone()
        return row[0] if row else 0

    def increment_stat(self, key: str, amount: int = 1) -> None:
        with self._tx() as cur:
            cur.execute(
                "INSERT INTO stats (key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = value + ?",
                (key, amount, amount),
            )

    # ── internal ────────────────────────────────────────────────────

    def _ensure_defaults(self) -> None:
        """Seed stats rows and the Default bundle if they don't exist."""
        with self._tx() as cur:
            cur.execute(
                "INSERT OR IGNORE INTO bundles (name, enabled) VALUES ('Default', 1)"
            )
            for stat_key in ("expanded", "chars_saved"):
                cur.execute(
                    "INSERT OR IGNORE INTO stats (key, value) VALUES (?, 0)",
                    (stat_key,),
                )


def _parse_dt(s: str | None) -> datetime | None:
    if s is None:
        return None
    try:
        return datetime.fromisoformat(s)
    except (ValueError, TypeError):
        return None
