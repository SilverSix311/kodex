"""Tests for the SQLite storage layer."""

import tempfile
from pathlib import Path

import pytest

from kodex_py.storage.database import Database
from kodex_py.storage.models import Bundle, Hotstring, TriggerType


@pytest.fixture
def db(tmp_path):
    d = Database(tmp_path / "test.db")
    d.open()
    yield d
    d.close()


class TestBundles:
    def test_default_bundle_exists(self, db):
        bundles = db.get_bundles()
        names = [b.name for b in bundles]
        assert "Default" in names

    def test_create_bundle(self, db):
        b = db.create_bundle("Work", enabled=True)
        assert b.id is not None
        assert b.name == "Work"
        assert b.enabled is True

    def test_create_bundle_idempotent(self, db):
        b1 = db.create_bundle("Work")
        b2 = db.create_bundle("Work")
        assert b1.id == b2.id

    def test_toggle_bundle(self, db):
        b = db.create_bundle("Test", enabled=True)
        db.set_bundle_enabled(b.id, False)
        found = db.get_bundle_by_name("Test")
        assert found.enabled is False

    def test_delete_bundle(self, db):
        b = db.create_bundle("Temp")
        db.delete_bundle(b.id)
        assert db.get_bundle_by_name("Temp") is None

    def test_delete_bundle_cascades_hotstrings(self, db):
        b = db.create_bundle("Temp")
        hs = Hotstring(name="test", replacement="expanded", bundle_id=b.id, triggers={TriggerType.SPACE})
        db.save_hotstring(hs)
        db.delete_bundle(b.id)
        # Hotstring should be gone
        assert db.get_hotstring(hs.id) is None


class TestHotstrings:
    def test_save_and_retrieve(self, db):
        b = db.get_bundle_by_name("Default")
        hs = Hotstring(
            name="btw",
            replacement="by the way",
            bundle_id=b.id,
            triggers={TriggerType.SPACE, TriggerType.ENTER},
        )
        saved = db.save_hotstring(hs)
        assert saved.id is not None

        loaded = db.get_hotstring(saved.id)
        assert loaded.name == "btw"
        assert loaded.replacement == "by the way"
        assert TriggerType.SPACE in loaded.triggers
        assert TriggerType.ENTER in loaded.triggers

    def test_update_hotstring(self, db):
        b = db.get_bundle_by_name("Default")
        hs = Hotstring(name="btw", replacement="by the way", bundle_id=b.id, triggers={TriggerType.SPACE})
        saved = db.save_hotstring(hs)

        saved.replacement = "by the way (updated)"
        saved.triggers = {TriggerType.ENTER}
        db.save_hotstring(saved)

        loaded = db.get_hotstring(saved.id)
        assert loaded.replacement == "by the way (updated)"
        assert loaded.triggers == {TriggerType.ENTER}

    def test_delete_hotstring(self, db):
        b = db.get_bundle_by_name("Default")
        hs = Hotstring(name="tmp", replacement="temp", bundle_id=b.id, triggers={TriggerType.SPACE})
        saved = db.save_hotstring(hs)
        db.delete_hotstring(saved.id)
        assert db.get_hotstring(saved.id) is None

    def test_get_by_name(self, db):
        b = db.get_bundle_by_name("Default")
        hs = Hotstring(name="unique", replacement="val", bundle_id=b.id, triggers={TriggerType.TAB})
        db.save_hotstring(hs)
        found = db.get_hotstring_by_name("unique", b.id)
        assert found is not None
        assert found.replacement == "val"

    def test_get_hotstrings_enabled_only(self, db):
        enabled = db.create_bundle("Enabled", enabled=True)
        disabled = db.create_bundle("Disabled", enabled=False)

        db.save_hotstring(Hotstring(name="a", replacement="a", bundle_id=enabled.id, triggers={TriggerType.SPACE}))
        db.save_hotstring(Hotstring(name="b", replacement="b", bundle_id=disabled.id, triggers={TriggerType.SPACE}))

        results = db.get_hotstrings(enabled_only=True)
        names = {hs.name for hs in results}
        assert "a" in names
        assert "b" not in names

    def test_script_mode(self, db):
        b = db.get_bundle_by_name("Default")
        hs = Hotstring(name="run", replacement="print('hi')", is_script=True, bundle_id=b.id, triggers={TriggerType.INSTANT})
        saved = db.save_hotstring(hs)
        loaded = db.get_hotstring(saved.id)
        assert loaded.is_script is True

    def test_multiline_replacement(self, db):
        b = db.get_bundle_by_name("Default")
        text = "Hello,\r\nThis is line 2.\r\nLine 3."
        hs = Hotstring(name="ml", replacement=text, bundle_id=b.id, triggers={TriggerType.SPACE})
        saved = db.save_hotstring(hs)
        loaded = db.get_hotstring(saved.id)
        assert loaded.replacement == text


class TestConfig:
    def test_get_set_config(self, db):
        db.set_config("test_key", "test_value")
        assert db.get_config("test_key") == "test_value"

    def test_config_default(self, db):
        assert db.get_config("nonexistent", "default") == "default"

    def test_config_upsert(self, db):
        db.set_config("key", "v1")
        db.set_config("key", "v2")
        assert db.get_config("key") == "v2"


class TestStats:
    def test_default_stats(self, db):
        assert db.get_stat("expanded") == 0

    def test_increment(self, db):
        db.increment_stat("expanded", 5)
        assert db.get_stat("expanded") == 5
        db.increment_stat("expanded", 3)
        assert db.get_stat("expanded") == 8
