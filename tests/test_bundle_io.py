"""Tests for .kodex bundle import/export."""

import pytest

from kodex_py.storage.bundle_io import export_bundle, import_bundle
from kodex_py.storage.database import Database
from kodex_py.storage.models import Hotstring, TriggerType


@pytest.fixture
def db(tmp_path):
    d = Database(tmp_path / "test.db")
    d.open()
    yield d
    d.close()


class TestExportImport:
    def test_roundtrip(self, db, tmp_path):
        # Create some hotstrings
        bundle = db.create_bundle("TestBundle")
        db.save_hotstring(Hotstring(
            name="btw", replacement="by the way",
            bundle_id=bundle.id, triggers={TriggerType.SPACE, TriggerType.ENTER},
        ))
        db.save_hotstring(Hotstring(
            name="addr", replacement="123 Main St\r\nAnytown, USA",
            bundle_id=bundle.id, triggers={TriggerType.SPACE},
        ))
        db.save_hotstring(Hotstring(
            name="scr", replacement="print('hi')", is_script=True,
            bundle_id=bundle.id, triggers={TriggerType.INSTANT},
        ))

        # Export
        out_file = tmp_path / "test.kodex"
        count = export_bundle(db, "TestBundle", out_file)
        assert count == 3
        assert out_file.exists()

        # Import into a fresh db
        db2 = Database(tmp_path / "test2.db")
        db2.open()
        try:
            imported = import_bundle(db2, out_file)
            assert imported == 3

            b = db2.get_bundle_by_name("TestBundle")
            assert b is not None

            btw = db2.get_hotstring_by_name("btw", b.id)
            assert btw.replacement == "by the way"
            assert TriggerType.SPACE in btw.triggers

            addr = db2.get_hotstring_by_name("addr", b.id)
            assert "123 Main St" in addr.replacement

            scr = db2.get_hotstring_by_name("scr", b.id)
            assert scr.is_script is True
        finally:
            db2.close()

    def test_import_custom_name(self, db, tmp_path):
        bundle = db.create_bundle("Original")
        db.save_hotstring(Hotstring(
            name="x", replacement="y", bundle_id=bundle.id, triggers={TriggerType.SPACE},
        ))
        out_file = tmp_path / "out.kodex"
        export_bundle(db, "Original", out_file)

        db2 = Database(tmp_path / "test2.db")
        db2.open()
        try:
            import_bundle(db2, out_file, bundle_name="Renamed")
            assert db2.get_bundle_by_name("Renamed") is not None
            assert db2.get_bundle_by_name("Original") is None
        finally:
            db2.close()
