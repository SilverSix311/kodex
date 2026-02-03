"""Application configuration — loads from SQLite config table + env vars.

This replaces the INI-based configuration from the AHK version.
"""

from __future__ import annotations

import logging
from pathlib import Path

from kodex_py.storage.database import Database
from kodex_py.storage.models import AppConfig, SendMode

log = logging.getLogger(__name__)

# Default paths
DEFAULT_DATA_DIR = Path.home() / ".kodex"
DEFAULT_DB_NAME = "kodex.db"


def get_data_dir() -> Path:
    """Return (and create) the Kodex data directory."""
    d = DEFAULT_DATA_DIR
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_db_path() -> Path:
    return get_data_dir() / DEFAULT_DB_NAME


def load_config(db: Database) -> AppConfig:
    """Read the AppConfig from the database."""
    cfg = AppConfig()
    cfg.send_mode = SendMode(int(db.get_config("send_mode", "0")))
    cfg.play_sound = db.get_config("play_sound", "1") == "1"
    cfg.autocorrect_enabled = db.get_config("autocorrect_enabled", "0") == "1"
    cfg.run_at_startup = db.get_config("run_at_startup", "0") == "1"
    cfg.hotkey_create = db.get_config("hotkey_create", "ctrl+shift+h")
    cfg.hotkey_manage = db.get_config("hotkey_manage", "ctrl+shift+m")
    cfg.hotkey_disable = db.get_config("hotkey_disable", "")
    cfg.hotkey_tracker = db.get_config("hotkey_tracker", "ctrl+shift+t")
    cfg.expanded = db.get_stat("expanded")
    cfg.chars_saved = db.get_stat("chars_saved")
    return cfg


def save_config(db: Database, cfg: AppConfig) -> None:
    """Persist the AppConfig to the database."""
    db.set_config("send_mode", str(cfg.send_mode.value))
    db.set_config("play_sound", "1" if cfg.play_sound else "0")
    db.set_config("autocorrect_enabled", "1" if cfg.autocorrect_enabled else "0")
    db.set_config("run_at_startup", "1" if cfg.run_at_startup else "0")
    db.set_config("hotkey_create", cfg.hotkey_create)
    db.set_config("hotkey_manage", cfg.hotkey_manage)
    db.set_config("hotkey_disable", cfg.hotkey_disable)
    db.set_config("hotkey_tracker", cfg.hotkey_tracker)
