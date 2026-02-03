# Kodex — Text Expansion Engine

**Version 3.0** — a full Python rewrite of the original AutoHotkey v2 Kodex.

## What Is Kodex?

Kodex is a blazing-fast text expansion / hotstring engine. Type a short abbreviation, press a trigger key, and it expands into longer text — from a quick "btw" → "by the way" to multi-paragraph email templates.

## Key Features

- **Trie-based matching** — O(k) lookup instead of O(n) substring search
- **Direct keyboard injection** — no clipboard clobbering, buttery smooth even for long expansions
- **SQLite storage** — replaces thousands of tiny hex-encoded files with a single database
- **Bundle system** — organize hotstrings into named categories, enable/disable per-bundle
- **Variable tokens** — `%c` (clipboard), `%t` (time), `%ds`/`%dl` (dates), `%p` (prompt), `%|` (cursor)
- **GUI management** — tkinter-based management window, preferences, and dialogs
- **Freshdesk time tracker** — built-in ticket time tracking with overlay timer
- **Printable cheatsheet** — generate HTML reference of all hotstrings
- **Portable packaging** — runs with embedded Python, no installation required
- **Cross-platform ready** — Windows-first, but architected for macOS/Linux

## Quick Start

### Portable (Windows — no Python required)

1. Download the latest release zip
2. Extract to any folder
3. Double-click `kodex-gui.vbs` to start

### Developer Install

```bash
# Clone and install
git clone https://github.com/SilverSix311/kodex.git
cd kodex
python -m venv .venv
source .venv/bin/activate    # Linux/macOS
# .venv\Scripts\activate     # Windows
pip install -e ".[dev]"

# Run
kodex run

# Test
pytest tests/ -v
```

## CLI Reference

```
kodex run                         Start engine + system tray
kodex list                        List all hotstrings
kodex add NAME REPLACEMENT        Add a hotstring
kodex remove NAME                 Remove a hotstring
kodex bundles                     List bundles
kodex bundle-create NAME          Create a bundle
kodex bundle-toggle NAME          Enable/disable a bundle
kodex bundle-delete NAME          Delete a bundle
kodex migrate LEGACY_DIR          Migrate from AHK Kodex
kodex import-bundle FILE.kodex    Import a .kodex bundle
kodex export-bundle NAME FILE     Export a bundle
kodex stats                       Show expansion stats
kodex cheatsheet [FILE]           Generate HTML cheatsheet
kodex time-log [-d DATE]          Show ticket time log
```

## GUI Features

### System Tray

Right-click the tray icon for:
- **Manage Hotstrings** — full management window
- **Create New Hotstring** — quick-add dialog
- **Preferences** — settings and statistics
- **Ticket Tracker** — start/stop time tracking
- **Disable/Enable** — toggle hotstring matching

### Management Window

- Tab-per-bundle navigation
- Search/filter hotstrings
- Inline editing of name, replacement text, triggers, script mode
- Bundle management (create, rename, delete)
- Import/export bundles (`.kodex` format)
- Generate printable cheatsheet

### Hotkey Defaults

| Hotkey | Function |
|--------|----------|
| `Ctrl+Shift+H` | Create new hotstring |
| `Ctrl+Shift+M` | Open management window |
| `Ctrl+Shift+T` | Start/stop ticket tracker |

## Freshdesk Ticket Time Tracker

Track time spent on support tickets:

1. Copy a Freshdesk ticket URL to clipboard
2. Press `Ctrl+Shift+T` to start tracking
3. A floating overlay shows the ticket number and elapsed time
4. Press `Ctrl+Shift+T` again to stop and log the time

Time entries are stored as CSV files in `data/timeTracker/` with the format:
```
ticket_number,Status,YYYY-MM-DD HH:MM:SS,duration_hours
```

View the log:
```bash
kodex time-log            # Today's entries
kodex time-log -d 2026-02-03  # Specific date
```

## Variable Tokens

Use these in replacement text:

| Token | Replacement | Example |
|-------|-------------|---------|
| `%c` | Clipboard contents | Insert clipboard inline |
| `%t` | Current time | `2:30 PM` |
| `%ds` | Short date | `2/3/2026` |
| `%dl` | Long date | `February 3, 2026` |
| `%tl` | Long time | `14:30:45 PM` |
| `%p` | User prompt | Opens a dialog for input |
| `%\|` | Cursor position | Places cursor after expansion |

## Architecture

```
kodex-py/
├── src/kodex_py/
│   ├── engine/
│   │   ├── matcher.py        ← Trie-based hotstring matching
│   │   ├── input_monitor.py  ← Keyboard hook (pynput)
│   │   ├── executor.py       ← Expansion + variable substitution
│   │   └── sender.py         ← Direct keystroke injection
│   ├── storage/
│   │   ├── database.py       ← SQLite CRUD
│   │   ├── migration.py      ← Legacy AHK data importer
│   │   ├── bundle_io.py      ← .kodex file import/export
│   │   └── models.py         ← Data classes
│   ├── gui/
│   │   ├── manager.py        ← Management window
│   │   ├── editor.py         ← New hotstring dialog
│   │   ├── preferences.py    ← Preferences window
│   │   ├── cheatsheet.py     ← HTML cheatsheet generator
│   │   └── prompt.py         ← %p variable prompt
│   ├── plugins/
│   │   └── ticket_tracker.py ← Freshdesk time tracker
│   ├── utils/
│   │   ├── hex_codec.py      ← Legacy hex encode/decode
│   │   └── variables.py      ← Token substitution
│   ├── app.py                ← Application orchestrator
│   ├── cli.py                ← Click-based CLI
│   ├── config.py             ← Configuration management
│   └── tray.py               ← System tray (pystray + tkinter GUI)
├── tests/                    ← pytest test suite
├── build_embedded.py         ← Embedded Python build script
├── build.bat                 ← Windows build launcher
├── BUILD.md                  ← Build documentation
└── pyproject.toml
```

## Building a Portable Distribution

See [BUILD.md](BUILD.md) for full details.

```cmd
# On Windows with Python 3.11+
build.bat
```

This creates `dist/kodex/` with embedded Python — zip it up and distribute.

## Migration from AHK

The `kodex migrate` command reads the legacy directory structure:
- Hex-encoded `.txt` replacement files
- Double-comma-separated bank files (`enter.csv`, `tab.csv`, etc.)
- `kodex.ini` settings
- Bundle subdirectories

```bash
kodex migrate /path/to/old/kodex-dir
```

Everything is imported into a single `kodex.db` SQLite database.

## License

MIT
