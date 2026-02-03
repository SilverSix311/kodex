"""Tests for the HTML cheatsheet generator."""

import tempfile
from pathlib import Path

import pytest

from kodex_py.gui.cheatsheet import generate_cheatsheet
from kodex_py.storage.database import Database
from kodex_py.storage.models import Hotstring, TriggerType


@pytest.fixture
def db(tmp_path):
    d = Database(tmp_path / "test.db")
    d.open()
    yield d
    d.close()


class TestCheatsheet:
    def test_generates_html(self, db, tmp_path):
        bundle = db.create_bundle("TestBundle")
        db.save_hotstring(Hotstring(
            name="btw",
            replacement="by the way",
            bundle_id=bundle.id,
            triggers={TriggerType.SPACE},
        ))
        output = tmp_path / "cheatsheet.html"
        generate_cheatsheet(db, output)

        assert output.exists()
        content = output.read_text(encoding="utf-8")
        assert "<!DOCTYPE html>" in content
        assert "btw" in content
        assert "by the way" in content
        assert "TestBundle" in content

    def test_empty_db(self, db, tmp_path):
        output = tmp_path / "cheatsheet.html"
        generate_cheatsheet(db, output)

        assert output.exists()
        content = output.read_text(encoding="utf-8")
        assert "Total: 0 hotstrings" in content

    def test_multiple_bundles(self, db, tmp_path):
        b1 = db.create_bundle("Work")
        b2 = db.create_bundle("Personal")
        db.save_hotstring(Hotstring(
            name="addr", replacement="123 Main St", bundle_id=b1.id,
            triggers={TriggerType.SPACE},
        ))
        db.save_hotstring(Hotstring(
            name="sig", replacement="Best regards", bundle_id=b2.id,
            triggers={TriggerType.ENTER},
        ))

        output = tmp_path / "cheatsheet.html"
        generate_cheatsheet(db, output)

        content = output.read_text(encoding="utf-8")
        assert "Work" in content
        assert "Personal" in content
        assert "addr" in content
        assert "sig" in content

    def test_html_escaping(self, db, tmp_path):
        bundle = db.create_bundle("Escape")
        db.save_hotstring(Hotstring(
            name="<script>",
            replacement='<img src="x" onerror="alert(1)">',
            bundle_id=bundle.id,
            triggers={TriggerType.SPACE},
        ))

        output = tmp_path / "cheatsheet.html"
        generate_cheatsheet(db, output)

        content = output.read_text(encoding="utf-8")
        # Ensure HTML entities are escaped
        assert "&lt;script&gt;" in content
        assert "<script>" not in content.split("<style>")[1]  # not in body

    def test_script_mode_label(self, db, tmp_path):
        bundle = db.create_bundle("Scripts")
        db.save_hotstring(Hotstring(
            name="test", replacement="print('hello')",
            is_script=True, bundle_id=bundle.id,
            triggers={TriggerType.INSTANT},
        ))

        output = tmp_path / "cheatsheet.html"
        generate_cheatsheet(db, output)

        content = output.read_text(encoding="utf-8")
        assert "Script" in content

    def test_long_replacement_truncated(self, db, tmp_path):
        bundle = db.create_bundle("Long")
        long_text = "x" * 500
        db.save_hotstring(Hotstring(
            name="long", replacement=long_text,
            bundle_id=bundle.id,
            triggers={TriggerType.SPACE},
        ))

        output = tmp_path / "cheatsheet.html"
        generate_cheatsheet(db, output)

        content = output.read_text(encoding="utf-8")
        # Should be truncated with ellipsis
        assert "…" in content
