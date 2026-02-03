"""Tests for legacy data migration."""

import os
from pathlib import Path

import pytest

from kodex_py.storage.database import Database
from kodex_py.storage.migration import migrate_legacy
from kodex_py.storage.models import TriggerType
from kodex_py.utils.hex_codec import hexify


@pytest.fixture
def legacy_dir(tmp_path):
    """Create a minimal legacy Kodex directory structure."""
    # Default bundle
    (tmp_path / "replacements").mkdir()
    (tmp_path / "bank").mkdir()

    # Write some hotstrings
    _write_hs(tmp_path, "btw", "by the way")
    _write_hs(tmp_path, "addr", "123 Main Street\r\nAnytown, USA")
    _write_hs(tmp_path, "sig", "Best regards,\r\nKlyde")
    _write_hs(tmp_path, "scr", "::scr::print('hello')")

    # Write bank files
    btw_hex = hexify("btw")
    addr_hex = hexify("addr")
    sig_hex = hexify("sig")
    scr_hex = hexify("scr")

    (tmp_path / "bank" / "space.csv").write_text(f"{btw_hex},,{addr_hex},,")
    (tmp_path / "bank" / "enter.csv").write_text(f"{btw_hex},,")
    (tmp_path / "bank" / "tab.csv").write_text("")
    (tmp_path / "bank" / "notrig.csv").write_text(f"{sig_hex},,")

    # A named bundle
    bundle_dir = tmp_path / "Bundles" / "Work"
    (bundle_dir / "replacements").mkdir(parents=True)
    (bundle_dir / "bank").mkdir()
    _write_hs(bundle_dir, "ty", "Thank you!")
    ty_hex = hexify("ty")
    (bundle_dir / "bank" / "space.csv").write_text(f"{ty_hex},,")
    (bundle_dir / "bank" / "enter.csv").write_text("")
    (bundle_dir / "bank" / "tab.csv").write_text("")
    (bundle_dir / "bank" / "notrig.csv").write_text("")

    # kodex.ini
    (tmp_path / "kodex.ini").write_text(
        "[Bundles]\nDefault=1\nWork=1\n\n"
        "[Settings]\nMode=0\n\n"
        "[Preferences]\nExSound=1\nAutoCorrect=0\n\n"
        "[Stats]\nExpanded=42\nCharacters=1234\n"
    )

    return tmp_path


def _write_hs(base: Path, name: str, replacement: str):
    hex_name = hexify(name)
    (base / "replacements" / f"{hex_name}.txt").write_text(replacement)


class TestMigration:
    def test_basic_migration(self, legacy_dir, tmp_path):
        db_path = tmp_path / "output.db"
        stats = migrate_legacy(legacy_dir, db_path)

        assert stats.bundles == 2  # Default + Work
        assert stats.hotstrings == 5  # btw, addr, sig, scr + ty
        assert len(stats.errors) == 0

    def test_hotstrings_readable(self, legacy_dir, tmp_path):
        db_path = tmp_path / "output.db"
        migrate_legacy(legacy_dir, db_path)

        db = Database(db_path)
        db.open()
        try:
            default = db.get_bundle_by_name("Default")
            hs = db.get_hotstring_by_name("btw", default.id)
            assert hs is not None
            assert hs.replacement == "by the way"
            assert TriggerType.SPACE in hs.triggers
            assert TriggerType.ENTER in hs.triggers
        finally:
            db.close()

    def test_triggers_correct(self, legacy_dir, tmp_path):
        db_path = tmp_path / "output.db"
        migrate_legacy(legacy_dir, db_path)

        db = Database(db_path)
        db.open()
        try:
            default = db.get_bundle_by_name("Default")

            sig = db.get_hotstring_by_name("sig", default.id)
            assert TriggerType.INSTANT in sig.triggers
            assert TriggerType.SPACE not in sig.triggers

            addr = db.get_hotstring_by_name("addr", default.id)
            assert TriggerType.SPACE in addr.triggers
        finally:
            db.close()

    def test_script_mode_detected(self, legacy_dir, tmp_path):
        db_path = tmp_path / "output.db"
        migrate_legacy(legacy_dir, db_path)

        db = Database(db_path)
        db.open()
        try:
            default = db.get_bundle_by_name("Default")
            scr = db.get_hotstring_by_name("scr", default.id)
            assert scr.is_script is True
            assert scr.replacement == "print('hello')"
        finally:
            db.close()

    def test_multiline_preserved(self, legacy_dir, tmp_path):
        db_path = tmp_path / "output.db"
        migrate_legacy(legacy_dir, db_path)

        db = Database(db_path)
        db.open()
        try:
            default = db.get_bundle_by_name("Default")
            addr = db.get_hotstring_by_name("addr", default.id)
            assert "123 Main Street" in addr.replacement
            assert "\r\n" in addr.replacement or "\n" in addr.replacement
        finally:
            db.close()

    def test_named_bundle_migrated(self, legacy_dir, tmp_path):
        db_path = tmp_path / "output.db"
        migrate_legacy(legacy_dir, db_path)

        db = Database(db_path)
        db.open()
        try:
            work = db.get_bundle_by_name("Work")
            assert work is not None
            assert work.enabled is True

            ty = db.get_hotstring_by_name("ty", work.id)
            assert ty is not None
            assert ty.replacement == "Thank you!"
        finally:
            db.close()

    def test_config_migrated(self, legacy_dir, tmp_path):
        db_path = tmp_path / "output.db"
        migrate_legacy(legacy_dir, db_path)

        db = Database(db_path)
        db.open()
        try:
            assert db.get_config("send_mode") == "0"
            assert db.get_config("play_sound") == "1"
            assert db.get_stat("expanded") == 42
            assert db.get_stat("chars_saved") == 1234
        finally:
            db.close()
