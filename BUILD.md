# Kodex Build Guide

## Overview

Kodex can be packaged as a **portable Windows application** with an embedded Python runtime. No system Python installation is required on the target machine.

## Distribution Structure

```
kodex/
├── python/               ← Embedded Python 3.11 runtime
│   ├── python.exe        ← Console Python
│   ├── pythonw.exe       ← No-console Python (for GUI)
│   ├── python311.dll
│   ├── Lib/site-packages/ ← All dependencies
│   └── python311._pth    ← Patched to include ../app
├── app/                  ← Kodex source code
│   └── kodex_py/
│       ├── __init__.py
│       ├── __main__.py   ← Module entry point
│       ├── cli.py
│       ├── app.py
│       ├── engine/
│       ├── storage/
│       ├── gui/
│       ├── plugins/
│       └── utils/
├── data/                 ← User data (portable)
│   ├── kodex.db          ← SQLite database (created on first run)
│   ├── resources/        ← Icons, sounds
│   └── timeTracker/      ← Time tracker CSV files
├── kodex.bat             ← CLI launcher (console)
├── kodex-run.bat         ← Engine launcher (with console)
└── kodex-gui.vbs         ← Engine launcher (no console window)
```

## Target Python Version

**Python 3.11** is the target version for Kodex embedded builds.

Why 3.11 specifically:
- **Stability** — Well-established release with broad library support
- **Embedded availability** — Clean embeddable packages available for Windows
- **tkinter compatibility** — Fewer DLL issues with embedded tkinter
- **Cross-machine consistency** — Builds reliably on different Windows machines

> **Note:** Python 3.12+ and 3.13+ have shown build inconsistencies across machines. Stick with 3.11 unless you have a specific reason to upgrade.

## Building

### Prerequisites

- **Windows 10** or later
- **Python 3.11** installed on the build machine (used to run the build script)
- **Internet connection** (to download embedded Python and pip packages)

### Quick Build

```cmd
cd kodex-py
build.bat
```

Or manually:

```cmd
python build_embedded.py
```

### What the Build Script Does

1. **Downloads** Python 3.11 embedded runtime (~8 MB zip)
2. **Extracts** to `dist/kodex/python/`
3. **Patches** `python311._pth` to enable pip and add the app directory
4. **Installs pip** via `get-pip.py`
5. **Installs dependencies**: pynput, pystray, Pillow, pyperclip, click
6. **Copies** the Kodex source to `dist/kodex/app/`
7. **Creates** launcher scripts (`.bat` and `.vbs`)

### Build Output

The complete portable distribution is created in `dist/kodex/`.

## Running

### CLI Mode

```cmd
kodex.bat list                    List all hotstrings
kodex.bat add btw "by the way"   Add a hotstring
kodex.bat stats                   Show stats
kodex.bat time-log                Show today's time log
kodex.bat cheatsheet              Generate HTML cheatsheet
```

### Engine + Tray Mode

```cmd
kodex-run.bat                     Start with console window
kodex-gui.vbs                     Start silently (no console)
```

Double-click `kodex-gui.vbs` to start Kodex in the system tray.

### Auto-Start

To run Kodex at Windows startup:

1. Press `Win+R`, type `shell:startup`, press Enter
2. Copy `kodex-gui.vbs` (or create a shortcut to it) into the Startup folder

## Distributing

The entire `dist/kodex/` folder is portable:

1. **Zip** the `kodex/` folder
2. **Share** the zip file
3. Users extract and double-click `kodex-gui.vbs`

No installation required. All data is stored in the `data/` subfolder.

## Development Mode

For development without the embedded runtime:

```bash
# Create a virtual environment
python -m venv .venv
.venv/Scripts/activate    # Windows
# or: source .venv/bin/activate    # Linux/macOS

# Install in dev mode
pip install -e ".[dev]"

# Run
kodex run

# Test
pytest tests/ -v
```

## Upgrading

To upgrade Kodex:

1. Run a new build
2. Replace the `app/` folder in the existing distribution
3. User data in `data/` is preserved

Or: replace the entire distribution — the database in `data/` can be preserved by copying it to the new distribution.
