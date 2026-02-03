"""Tests for new CLI commands added in Phase 2."""

import tempfile
from pathlib import Path

import pytest
from click.testing import CliRunner

from kodex_py.cli import cli
from kodex_py.storage.database import Database
from kodex_py.storage.models import Hotstring, TriggerType


@pytest.fixture
def db_path(tmp_path):
    db = Database(tmp_path / "test.db")
    db.open()
    bundle = db.create_bundle("Default")
    db.save_hotstring(Hotstring(
        name="btw", replacement="by the way",
        bundle_id=bundle.id, triggers={TriggerType.SPACE},
    ))
    db.save_hotstring(Hotstring(
        name="addr", replacement="123 Main St",
        bundle_id=bundle.id, triggers={TriggerType.ENTER},
    ))
    db.close()
    return str(tmp_path / "test.db")


class TestCheatsheetCommand:
    def test_generates_file(self, db_path, tmp_path):
        output = str(tmp_path / "test.html")
        runner = CliRunner()
        result = runner.invoke(cli, ["--db", db_path, "cheatsheet", output])
        assert result.exit_code == 0
        assert "Cheatsheet saved" in result.output
        assert Path(output).exists()

        content = Path(output).read_text(encoding="utf-8")
        assert "btw" in content
        assert "addr" in content

    def test_default_filename(self, db_path):
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(cli, ["--db", db_path, "cheatsheet"])
            assert result.exit_code == 0
            assert Path("kodex-cheatsheet.html").exists()


class TestTimeLogCommand:
    def test_empty_log(self, tmp_path):
        runner = CliRunner()
        result = runner.invoke(cli, ["time-log"])
        assert result.exit_code == 0
        assert "No time entries" in result.output
