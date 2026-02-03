# Changelog

All notable changes to Kodex (Python rewrite) will be documented here.

## [3.0.0] - 2026-02-03

### Phase 2 — GUI, Tracker, Packaging

#### Added
- **GUI Management Window** (`gui/manager.py`)
  - Tab-per-bundle navigation
  - Search/filter hotstrings by name or replacement text
  - Inline editing: name, replacement, triggers, script mode
  - Save, delete, and create hotstrings from the GUI
  - Bundle management via menu: create, rename, delete, export, import
  - Printable cheatsheet generation from Tools menu
  - Preferences access from Tools menu

- **New Hotstring Dialog** (`gui/editor.py`)
  - Quick-create form with name, replacement, bundle, triggers, script mode
  - Trigger mutual exclusion: Instant unchecks other triggers
  - Accessible from tray and management window

- **Preferences Window** (`gui/preferences.py`)
  - General tab: hotkeys, send mode, sound, startup, autocorrect toggles
  - Print tab: generate HTML cheatsheet
  - Stats tab: expansions, characters saved, hours saved

- **Text Prompt Dialog** (`gui/prompt.py`)
  - Modal dialog for `%p` variable fill-in
  - Shows template with highlighted `%p` markers
  - Always-on-top, integrates with expansion executor

- **HTML Cheatsheet Generator** (`gui/cheatsheet.py`)
  - Generates styled, printable HTML of all hotstrings grouped by bundle
  - Shows name, replacement (truncated), triggers, and script/text mode
  - HTML-escaped for safety
  - Also available via CLI: `kodex cheatsheet [output.html]`

- **Freshdesk Ticket Time Tracker** (`plugins/ticket_tracker.py`)
  - Extract ticket number from clipboard (Freshdesk URLs or bare numbers)
  - Start/stop tracking via `Ctrl+Shift+T` (or tray menu)
  - Floating overlay showing ticket number and running timer
  - CSV logging: `USERNAME.MMDD.csv` with ticket, status, timestamp, duration
  - View log via CLI: `kodex time-log [-d DATE]`

- **System Tray Integration** — fully connected (`tray.py`)
  - Manage Hotstrings → opens management window
  - Create New Hotstring → opens quick-create dialog
  - Preferences → opens preferences window
  - Start/Stop Ticket Tracker → toggle time tracking
  - Disable/Enable → toggle hotstring matching
  - Exit → clean shutdown
  - tkinter GUI runs in background thread alongside pystray

- **Embedded Python Packaging** (`build_embedded.py`, `build.bat`)
  - Downloads Python 3.11 embedded runtime
  - Installs all dependencies into embedded runtime
  - Creates portable distribution: `dist/kodex/`
  - Launcher scripts: `kodex.bat` (CLI), `kodex-run.bat` (engine), `kodex-gui.vbs` (silent)
  - No system Python required on target machine
  - See `BUILD.md` for full documentation

- **New CLI Commands**
  - `kodex cheatsheet [FILE]` — generate HTML cheatsheet from CLI
  - `kodex time-log [-d DATE]` — view ticket time log

- **Module Entry Point** (`__main__.py`)
  - `python -m kodex_py` now works

- **Tests**
  - `test_cheatsheet.py` — HTML generation, escaping, multi-bundle, truncation
  - `test_ticket_tracker.py` — start/stop, CSV logging, duration format, regex
  - `test_cli_new.py` — new CLI commands (cheatsheet, time-log)

#### Changed
- `app.py` — integrated ticket tracker plugin, `%p` prompt via tkinter dialog
- `tray.py` — complete rewrite with GUI integration (manage, create, preferences, tracker)
- `README.md` — comprehensive documentation for all features
- `pyproject.toml` — no new dependencies (tkinter is stdlib)

### Phase 1 — Core Engine (initial release)

#### Added
- Trie-based hotstring matcher with O(k) lookup
- SQLite storage replacing file-per-hotstring architecture
- Keyboard hook via pynput with mouse click buffer reset
- Direct keystroke injection and clipboard paste modes
- Variable substitution: `%c`, `%t`, `%ds`, `%dl`, `%tl`, `%p`, `%|`
- Bundle system with enable/disable
- Legacy AHK data migration tool
- `.kodex` bundle import/export
- System tray with pystray (basic)
- Click-based CLI with full CRUD
- 75 pytest tests covering all core functionality
