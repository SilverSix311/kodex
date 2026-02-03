"""Migrate legacy Kodex AHK data (hex-encoded files + CSV banks) into SQLite.

Usage (CLI)::

    kodex-migrate /path/to/kodex-ahk-dir

Or from Python::

    from kodex_py.storage.migration import migrate_legacy
    stats = migrate_legacy("/path/to/kodex-ahk-dir", "/path/to/kodex.db")

The legacy directory layout::

    kodex/
    ├── replacements/        ← Default bundle
    ├── bank/
    │   ├── enter.csv
    │   ├── tab.csv
    │   ├── space.csv
    │   └── notrig.csv
    ├── Bundles/
    │   ├── WorkStuff/
    │   │   ├── replacements/
    │   │   └── bank/
    │   └── ...
    ├── kodex.ini
    └── resources/autocorrect.txt
"""

from __future__ import annotations

import configparser
import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path

from kodex_py.storage.database import Database
from kodex_py.storage.models import Bundle, Hotstring, TriggerType
from kodex_py.utils.hex_codec import dehexify

log = logging.getLogger(__name__)


@dataclass
class MigrationStats:
    bundles: int = 0
    hotstrings: int = 0
    autocorrect: int = 0
    errors: list[str] = None  # type: ignore[assignment]

    def __post_init__(self):
        if self.errors is None:
            self.errors = []


def migrate_legacy(legacy_dir: str | Path, db_path: str | Path) -> MigrationStats:
    """Read an entire legacy Kodex installation and populate a SQLite database.

    Returns a :class:`MigrationStats` summary.
    """
    legacy = Path(legacy_dir)
    stats = MigrationStats()

    db = Database(db_path)
    db.open()

    try:
        # ── bundles ─────────────────────────────────────────────────
        # Read enabled/disabled state from kodex.ini
        ini_path = legacy / "kodex.ini"
        bundle_states: dict[str, bool] = {"Default": True}
        if ini_path.exists():
            cp = configparser.ConfigParser()
            cp.read(str(ini_path), encoding="utf-8-sig")
            if cp.has_section("Bundles"):
                for name, val in cp.items("Bundles"):
                    # configparser lowercases keys — we'll fix casing from dir names
                    bundle_states[name.lower()] = val.strip() == "1"

        # Default bundle
        default_bundle = db.create_bundle("Default", bundle_states.get("default", True))
        _import_bundle_dir(db, legacy, default_bundle, stats)
        stats.bundles += 1

        # Named bundles
        bundles_dir = legacy / "Bundles"
        if bundles_dir.is_dir():
            for entry in sorted(bundles_dir.iterdir()):
                if entry.is_dir():
                    enabled = bundle_states.get(entry.name.lower(), True)
                    bundle = db.create_bundle(entry.name, enabled)
                    _import_bundle_dir(db, entry, bundle, stats)
                    stats.bundles += 1

        # ── autocorrect ─────────────────────────────────────────────
        ac_file = legacy / "resources" / "autocorrect.txt"
        if ac_file.exists():
            ac_bundle = db.create_bundle("Autocorrect", enabled=False)
            _import_autocorrect(db, ac_file, ac_bundle, stats)

        # ── migrate config values ───────────────────────────────────
        if ini_path.exists():
            _migrate_config(db, ini_path)

    finally:
        db.close()

    return stats


def _import_bundle_dir(db: Database, bundle_dir: Path, bundle: Bundle, stats: MigrationStats) -> None:
    """Import a single bundle from its legacy directory."""
    replacements_dir = bundle_dir / "replacements"
    bank_dir = bundle_dir / "bank"

    if not replacements_dir.is_dir():
        return

    # Parse bank files to learn trigger types per hex name
    triggers_map: dict[str, set[TriggerType]] = {}
    trigger_file_map = {
        "enter.csv": TriggerType.ENTER,
        "tab.csv": TriggerType.TAB,
        "space.csv": TriggerType.SPACE,
        "notrig.csv": TriggerType.INSTANT,
    }

    if bank_dir.is_dir():
        for filename, ttype in trigger_file_map.items():
            bank_file = bank_dir / filename
            if bank_file.exists():
                content = bank_file.read_text(encoding="utf-8", errors="replace")
                # Bank format: hex names separated by ",,"
                hex_names = [h.strip() for h in content.split(",,") if h.strip()]
                for hex_name in hex_names:
                    triggers_map.setdefault(hex_name, set()).add(ttype)

    # Read replacement files
    for txt_file in sorted(replacements_dir.glob("*.txt")):
        hex_name = txt_file.stem
        try:
            plain_name = dehexify(hex_name)
        except (ValueError, IndexError) as e:
            stats.errors.append(f"Bad hex filename {txt_file.name}: {e}")
            continue

        try:
            replacement = txt_file.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            stats.errors.append(f"Cannot read {txt_file}: {e}")
            continue

        is_script = replacement.startswith("::scr::")
        if is_script:
            replacement = replacement[7:]

        hs = Hotstring(
            name=plain_name,
            replacement=replacement,
            is_script=is_script,
            bundle_id=bundle.id,
            triggers=triggers_map.get(hex_name, set()),
        )
        try:
            db.save_hotstring(hs)
            stats.hotstrings += 1
        except Exception as e:
            stats.errors.append(f"Failed to save '{plain_name}': {e}")


def _import_autocorrect(db: Database, ac_file: Path, bundle: Bundle, stats: MigrationStats) -> None:
    """Import the ``autocorrect.txt`` dictionary.

    Format: ``::misspelling::correction`` (AHK v1 hotstring syntax).
    Lines starting with ``;`` or ``#`` are comments.
    """
    for line in ac_file.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith(";") or line.startswith("#"):
            continue
        m = re.match(r"^::([^:]+)::(.+)$", line)
        if not m:
            continue
        misspelling, correction = m.group(1), m.group(2)
        hs = Hotstring(
            name=misspelling,
            replacement=correction,
            is_script=False,
            bundle_id=bundle.id,
            triggers={TriggerType.SPACE, TriggerType.ENTER, TriggerType.TAB},
        )
        try:
            db.save_hotstring(hs)
            stats.autocorrect += 1
        except Exception as e:
            stats.errors.append(f"Autocorrect '{misspelling}': {e}")


def _migrate_config(db: Database, ini_path: Path) -> None:
    """Copy relevant kodex.ini settings to the config table."""
    cp = configparser.ConfigParser()
    cp.read(str(ini_path), encoding="utf-8-sig")

    key_map = {
        ("Settings", "Mode"): "send_mode",
        ("Preferences", "ExSound"): "play_sound",
        ("Preferences", "AutoCorrect"): "autocorrect_enabled",
        ("Settings", "Startup"): "run_at_startup",
        ("Hotkey", "OntheFly"): "hotkey_create",
        ("Hotkey", "Management"): "hotkey_manage",
        ("Hotkey", "Disable"): "hotkey_disable",
    }

    for (section, key), config_key in key_map.items():
        if cp.has_option(section, key):
            db.set_config(config_key, cp.get(section, key))

    # Migrate stats
    if cp.has_option("Stats", "Expanded"):
        try:
            db.increment_stat("expanded", int(cp.get("Stats", "Expanded")))
        except ValueError:
            pass
    if cp.has_option("Stats", "Characters"):
        try:
            db.increment_stat("chars_saved", int(cp.get("Stats", "Characters")))
        except ValueError:
            pass


# ── CLI entry point ─────────────────────────────────────────────────

def main() -> None:
    import sys

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    if len(sys.argv) < 2:
        print("Usage: kodex-migrate <legacy-kodex-directory> [output.db]")
        sys.exit(1)

    legacy_dir = sys.argv[1]
    db_path = sys.argv[2] if len(sys.argv) > 2 else "kodex.db"

    log.info("Migrating from %s → %s", legacy_dir, db_path)
    result = migrate_legacy(legacy_dir, db_path)
    log.info("Done! %d bundles, %d hotstrings, %d autocorrect entries",
             result.bundles, result.hotstrings, result.autocorrect)
    if result.errors:
        log.warning("%d errors:", len(result.errors))
        for e in result.errors[:20]:
            log.warning("  • %s", e)


if __name__ == "__main__":
    main()
