"""Build script -- packages Kodex with embedded Python for Windows.

This script downloads an embedded Python runtime and creates a portable
distribution structure:

    kodex/
    +---- python/           <- Embedded Python runtime
    |   +---- python.exe
    |   +---- python311.dll
    |   +---- Lib/
    |   +---- ...
    +---- app/              <- Kodex source code
    |   +---- kodex_py/
    +---- data/             <- User data (created on first run)
    |   +---- kodex.db
    +---- kodex.bat         <- Launcher script
    +---- kodex-gui.vbs     <- No-console launcher

Run on a Windows machine:
    python build_embedded.py

Requirements:
    - Windows 10+ (or any Windows with Python 3.11+)
    - Internet connection (to download embedded Python)
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

# -- Configuration ---------------------------------------------------

PYTHON_VERSION = "3.13.12"
PYTHON_EMBED_URL = f"https://www.python.org/ftp/python/{PYTHON_VERSION}/python-{PYTHON_VERSION}-embed-amd64.zip"
PIP_URL = "https://bootstrap.pypa.io/get-pip.py"

BUILD_DIR = Path("build")
DIST_DIR = Path("dist/kodex")

# Dependencies to install into the embedded runtime
DEPENDENCIES = [
    "pynput>=1.7.6",
    "pystray>=0.19.5",
    "Pillow>=10.0.0",
    "pyperclip>=1.8.2",
    "click>=8.1.0",
]


def _copy_missing_extensions(python_dir: Path) -> None:
    """Copy C extension DLLs that the embedded Python zip doesn't include
    but that common packages (click, ctypes, sqlite3, etc.) require.
    """
    import sysconfig

    platstdlib = Path(sysconfig.get_path("platstdlib"))
    stdlib = Path(sysconfig.get_path("stdlib"))
    dlls_dir = platstdlib / "DLLs" if (platstdlib / "DLLs").exists() else stdlib.parent / "DLLs"

    embed_dlls = python_dir / "DLLs"
    embed_dlls.mkdir(exist_ok=True)

    # Extensions that embedded Python typically lacks
    needed_extensions = [
        "_ctypes*.pyd",
        "_decimal*.pyd",
        "_socket*.pyd",
        "_ssl*.pyd",
        "_sqlite3*.pyd",
        "_hashlib*.pyd",
        "_lzma*.pyd",
        "_bz2*.pyd",
        "_queue*.pyd",
        "_overlapped*.pyd",
        "_asyncio*.pyd",
        "_multiprocessing*.pyd",
        "select*.pyd",
        "unicodedata*.pyd",
    ]

    # Supporting DLLs that extensions depend on
    needed_dlls = [
        "libffi*.dll",
        "libcrypto*.dll",
        "libssl*.dll",
        "sqlite3*.dll",
    ]

    for search_dir in [dlls_dir, platstdlib, stdlib.parent]:
        if not search_dir.exists():
            continue
        for pattern in needed_extensions + needed_dlls:
            for src in search_dir.glob(pattern):
                dst = embed_dlls / src.name
                if not dst.exists():
                    shutil.copy2(src, dst)
                    print(f"  Copied {src.name}")

    # Also check root Python dir for DLLs (some installs put them there)
    python_install_root = stdlib.parent
    for pattern in needed_dlls:
        for src in python_install_root.glob(pattern):
            dst = embed_dlls / src.name
            if not dst.exists():
                shutil.copy2(src, dst)
                print(f"  Copied {src.name} (from root)")


def _copy_tkinter(python_dir: Path) -> None:
    """Copy tkinter and its dependencies from the system Python into the embedded runtime.

    The embedded Python distribution doesn't include tkinter. We need:
      1. The `tkinter` package (Python source) ->> Lib/tkinter/
      2. The `_tkinter` C extension (.pyd) ->> _tkinter.pyd
      3. The Tcl/Tk DLLs (tcl86t.dll, tk86t.dll) ->> DLLs/ or root
      4. The Tcl/Tk library files (scripts, themes) ->> tcl/ or Lib/
    """
    import sysconfig
    import glob

    # Find the system Python's tkinter
    stdlib = Path(sysconfig.get_path("stdlib"))
    platstdlib = Path(sysconfig.get_path("platstdlib"))
    # DLLs dir on Windows
    dlls_dir = platstdlib / "DLLs" if (platstdlib / "DLLs").exists() else stdlib.parent / "DLLs"

    # 1. Copy tkinter package
    tkinter_src = stdlib / "tkinter"
    if not tkinter_src.exists():
        print("  WARNING: tkinter not found in system Python -- GUI will not work!")
        return

    tkinter_dst = python_dir / "Lib" / "tkinter"
    tkinter_dst.parent.mkdir(parents=True, exist_ok=True)
    if tkinter_dst.exists():
        shutil.rmtree(tkinter_dst)
    shutil.copytree(tkinter_src, tkinter_dst)
    print(f"  Copied tkinter package ->> {tkinter_dst}")

    # 2. Copy _tkinter.pyd (C extension)
    embed_dlls = python_dir / "DLLs"
    embed_dlls.mkdir(exist_ok=True)

    for search_dir in [dlls_dir, platstdlib, stdlib.parent]:
        for pyd in search_dir.glob("_tkinter*.pyd"):
            dst = embed_dlls / pyd.name
            shutil.copy2(pyd, dst)
            print(f"  Copied {pyd.name} ->> {dst}")
            break
        else:
            continue
        break

    # 3. Copy Tcl/Tk DLLs
    for search_dir in [dlls_dir, platstdlib, stdlib.parent]:
        for pattern in ["tcl*.dll", "tk*.dll"]:
            for dll in search_dir.glob(pattern):
                dst = embed_dlls / dll.name
                if not dst.exists():
                    shutil.copy2(dll, dst)
                    print(f"  Copied {dll.name} ->> {dst}")

    # 4. Copy Tcl/Tk library directories (needed for themed widgets etc.)
    # These are usually in the Python install root under tcl/
    tcl_root = stdlib.parent / "tcl"
    if tcl_root.exists():
        embed_tcl = python_dir / "tcl"
        if embed_tcl.exists():
            shutil.rmtree(embed_tcl)
        shutil.copytree(tcl_root, embed_tcl)
        print(f"  Copied Tcl/Tk libraries ->> {embed_tcl}")
    else:
        # Try Lib/tcl
        for candidate in [stdlib / "tcl", stdlib.parent / "Lib" / "tcl"]:
            if candidate.exists():
                embed_tcl = python_dir / "tcl"
                shutil.copytree(candidate, embed_tcl)
                print(f"  Copied Tcl/Tk libraries ->> {embed_tcl}")
                break

    # 5. Patch _pth file to include Lib and DLLs directories
    for pth in python_dir.glob("python*._pth"):
        content = pth.read_text()
        additions = []
        if "Lib" not in content:
            additions.append("Lib")
        if "DLLs" not in content:
            additions.append("DLLs")
        if additions:
            content = content.rstrip("\n") + "\n" + "\n".join(additions) + "\n"
            pth.write_text(content)
            print(f"  Patched {pth.name} with: {', '.join(additions)}")


def _preflight_check():
    """Verify the build system has everything we need before starting."""
    print("\n->> Preflight check...")
    errors = []

    # Check Python version
    if sys.version_info < (3, 11):
        errors.append(f"Python 3.11+ required, got {sys.version}")

    # Check tkinter is available on the BUILD system
    try:
        import tkinter
        print(f"  [OK] tkinter available (Tcl/Tk {tkinter.TclVersion})")
    except ImportError:
        errors.append(
            "tkinter not found on build system!\n"
            "    Install it:\n"
            "      - Windows: re-run Python installer ->> check 'tcl/tk and IDLE'\n"
            "      - Linux: apt install python3-tk\n"
            "      - macOS: brew install python-tk"
        )

    # Check Pillow can be imported (needed for tray icon)
    try:
        from PIL import Image
        print("  [OK] Pillow available")
    except ImportError:
        print("  [WARN] Pillow not on build system (will install into embedded)")

    if errors:
        print("\n[FAIL] PREFLIGHT FAILED:")
        for e in errors:
            print(f"  [FAIL] {e}")
        print("\nFix the above issues and re-run the build.")
        sys.exit(1)

    print("  [OK] All preflight checks passed\n")


def _verify_build(python_exe: Path):
    """Verify the built runtime has all required modules."""
    print("\n->> Verifying build...")
    all_ok = True

    checks = {
        "pystray": "System tray icon",
        "PIL": "Image processing (Pillow)",
        "pynput": "Keyboard input monitoring",
        "pyperclip": "Clipboard access",
        "click": "CLI framework",
        "tkinter": "GUI windows",
    }

    # Set up env for tkinter verification
    env = os.environ.copy()
    tcl_dir = python_exe.parent / "tcl"
    if (tcl_dir / "tcl8.6").exists():
        env["TCL_LIBRARY"] = str(tcl_dir / "tcl8.6")
    if (tcl_dir / "tk8.6").exists():
        env["TK_LIBRARY"] = str(tcl_dir / "tk8.6")

    for mod, desc in checks.items():
        # For tkinter, also add DLL directory
        if mod == "tkinter":
            test_code = (
                "import os, sys;"
                f"os.add_dll_directory(r'{python_exe.parent / 'DLLs'}');"
                f"os.add_dll_directory(r'{python_exe.parent}');"
                f"import {mod}"
            )
        else:
            test_code = f"import {mod}"

        result = subprocess.run(
            [str(python_exe), "-c", test_code],
            capture_output=True, text=True, env=env,
        )
        if result.returncode == 0:
            print(f"  [OK] {mod} -- {desc}")
        else:
            print(f"  [FAIL] {mod} -- {desc} -- MISSING!")
            print(f"    Error: {result.stderr.strip().split(chr(10))[-1]}")
            all_ok = False

    if not all_ok:
        print("\n[WARN] BUILD HAS MISSING DEPENDENCIES -- some features may not work!")
        print("  Fix the issues above and rebuild.\n")
    else:
        print("  [OK] All dependencies verified!\n")

    return all_ok


def main():
    print("=" * 60)
    print("  Kodex Embedded Python Build")
    print("=" * 60)

    _preflight_check()

    # Clean
    if DIST_DIR.exists():
        print(f"\n->> Cleaning {DIST_DIR}...")
        shutil.rmtree(DIST_DIR)
    DIST_DIR.mkdir(parents=True)

    BUILD_DIR.mkdir(exist_ok=True)

    # 1. Download embedded Python
    embed_zip = BUILD_DIR / f"python-{PYTHON_VERSION}-embed-amd64.zip"
    if not embed_zip.exists():
        print(f"\n->> Downloading Python {PYTHON_VERSION} embedded...")
        urllib.request.urlretrieve(PYTHON_EMBED_URL, embed_zip)
    else:
        print(f"\n->> Using cached Python embed: {embed_zip}")

    # 2. Extract embedded Python
    python_dir = DIST_DIR / "python"
    print(f"\n->> Extracting to {python_dir}...")
    with zipfile.ZipFile(embed_zip, "r") as zf:
        zf.extractall(python_dir)

    # 3. Enable pip in embedded Python
    # The embedded Python has a python3XX._pth file that restricts imports.
    # We need to uncomment the "import site" line.
    pth_files = list(python_dir.glob("python*._pth"))
    for pth in pth_files:
        content = pth.read_text()
        content = content.replace("#import site", "import site")
        # Also add our app directory
        content += "\n../app\n"
        pth.write_text(content)
        print(f"  Patched {pth.name}")

    # 4. Install pip
    get_pip = BUILD_DIR / "get-pip.py"
    if not get_pip.exists():
        print("\n->> Downloading get-pip.py...")
        urllib.request.urlretrieve(PIP_URL, get_pip)

    python_exe = python_dir / "python.exe"
    print("\n->> Installing pip...")
    subprocess.run(
        [str(python_exe), str(get_pip), "--no-warn-script-location"],
        check=True,
    )

    # 5. Install dependencies
    print("\n->> Installing dependencies...")
    for dep in DEPENDENCIES:
        print(f"  Installing {dep}...")
        subprocess.run(
            [str(python_exe), "-m", "pip", "install", dep, "--no-warn-script-location"],
            check=True,
        )

    # 5b. Copy essential C extensions missing from embedded Python
    print("\n->> Copying missing C extensions from system Python...")
    _copy_missing_extensions(python_dir)

    # 5c. Copy tkinter from system Python into embedded runtime
    # The embedded Python zip doesn't include tkinter, but Kodex needs it for GUI.
    print("\n->> Copying tkinter from system Python...")
    _copy_tkinter(python_dir)

    # 5d. Create sitecustomize.py to add DLL search paths for tkinter
    # Embedded Python on Windows needs explicit DLL directory registration
    site_custom = python_dir / "sitecustomize.py"
    site_custom.write_text(
        '"""Auto-configure DLL search paths for embedded Python."""\n'
        'import os, sys\n'
        'base = os.path.dirname(sys.executable)\n'
        'dlls = os.path.join(base, "DLLs")\n'
        'if os.path.isdir(dlls):\n'
        '    try:\n'
        '        os.add_dll_directory(dlls)\n'
        '        os.add_dll_directory(base)\n'
        '    except (OSError, AttributeError):\n'
        '        pass\n'
        'tcl_lib = os.path.join(base, "tcl", "tcl8.6")\n'
        'tk_lib = os.path.join(base, "tcl", "tk8.6")\n'
        'if os.path.isdir(tcl_lib):\n'
        '    os.environ.setdefault("TCL_LIBRARY", tcl_lib)\n'
        'if os.path.isdir(tk_lib):\n'
        '    os.environ.setdefault("TK_LIBRARY", tk_lib)\n',
        encoding="utf-8",
    )
    print("  Created sitecustomize.py for DLL paths")

    # Also copy tk/tcl DLLs next to python.exe as fallback
    dlls_dir = python_dir / "DLLs"
    for dll_name in ["tcl86t.dll", "tk86t.dll", "_tkinter.pyd"]:
        src = dlls_dir / dll_name
        dst = python_dir / dll_name
        if src.exists() and not dst.exists():
            shutil.copy2(src, dst)
            print(f"  Copied {dll_name} to python root (fallback)")

    # 6. Copy app source
    app_dir = DIST_DIR / "app"
    src_dir = Path("src/kodex_py")
    print(f"\n->> Copying source to {app_dir}...")
    shutil.copytree(src_dir, app_dir / "kodex_py")

    # Also copy resources if they exist
    resources_src = Path("resources")
    if resources_src.exists():
        shutil.copytree(resources_src, DIST_DIR / "data" / "resources")

    # 7. Create data directory
    data_dir = DIST_DIR / "data"
    data_dir.mkdir(exist_ok=True)
    (data_dir / "timeTracker").mkdir(exist_ok=True)

    # 8. Create launcher scripts
    print("\n->> Creating launcher scripts...")

    # kodex.bat -- console launcher
    bat_content = '''@echo off
setlocal
set "KODEX_DIR=%~dp0"
set "PYTHONPATH=%KODEX_DIR%app"
set "KODEX_DB=%KODEX_DIR%data\\kodex.db"
set "TCL_LIBRARY=%KODEX_DIR%python\\tcl\\tcl8.6"
set "TK_LIBRARY=%KODEX_DIR%python\\tcl\\tk8.6"

REM Run Kodex
"%KODEX_DIR%python\\python.exe" -m kodex_py.cli --db "%KODEX_DB%" %*
'''
    (DIST_DIR / "kodex.bat").write_text(bat_content, encoding="utf-8")

    # kodex-run.bat -- run the engine (GUI mode)
    run_bat = '''@echo off
setlocal
set "KODEX_DIR=%~dp0"
set "PYTHONPATH=%KODEX_DIR%app"
set "KODEX_DB=%KODEX_DIR%data\\kodex.db"
set "TCL_LIBRARY=%KODEX_DIR%python\\tcl\\tcl8.6"
set "TK_LIBRARY=%KODEX_DIR%python\\tcl\\tk8.6"

REM Run Kodex engine with tray icon
"%KODEX_DIR%python\\pythonw.exe" -m kodex_py.cli --db "%KODEX_DB%" run
'''
    (DIST_DIR / "kodex-run.bat").write_text(run_bat, encoding="utf-8")

    # kodex-gui.vbs -- no-console launcher (hides the terminal window)
    vbs_content = '''Set WshShell = CreateObject("WScript.Shell")
kodexDir = Replace(WScript.ScriptFullName, WScript.ScriptName, "")
WshShell.Run Chr(34) & kodexDir & "python\\pythonw.exe" & Chr(34) & _
    " -m kodex_py.cli --db " & Chr(34) & kodexDir & "data\\kodex.db" & Chr(34) & " run", 0, False
'''
    (DIST_DIR / "kodex-gui.vbs").write_text(vbs_content, encoding="utf-8")

    # 9. Create __main__.py for module execution
    main_py = '''"""Entry point for python -m kodex_py.cli"""
from kodex_py.cli import cli
cli()
'''
    (app_dir / "kodex_py" / "__main__.py").write_text(main_py, encoding="utf-8")

    # 10. Verify everything works
    _verify_build(python_exe)

    # 11. Summary
    total_size = sum(f.stat().st_size for f in DIST_DIR.rglob("*") if f.is_file())
    print("\n" + "=" * 60)
    print("  Build complete!")
    print(f"  Output: {DIST_DIR.resolve()}")
    print(f"  Size:   {total_size / 1024 / 1024:.1f} MB")
    print()
    print("  To run:")
    print(f"    {DIST_DIR / 'kodex.bat'} list        (CLI)")
    print(f"    {DIST_DIR / 'kodex-run.bat'}          (Engine + tray)")
    print(f"    {DIST_DIR / 'kodex-gui.vbs'}          (Silent launch)")
    print("=" * 60)


if __name__ == "__main__":
    main()
