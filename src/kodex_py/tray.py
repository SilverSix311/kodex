"""System tray icon and menu — powered by pystray.

Fully connected to the GUI and ticket tracker:
    • Manage hotstrings  → opens ManagementWindow
    • Create new hotstring  → opens NewHotstringDialog
    • Preferences  → opens PreferencesWindow
    • Start/Stop Ticket Tracker
    • Disable / Enable
    • About
    • Exit
"""

from __future__ import annotations

import logging
import sys
import threading
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from kodex_py.app import KodexApp

log = logging.getLogger(__name__)

# We need a tkinter root for the GUI windows.
# pystray runs its own event loop, so we create a hidden Tk root
# and run GUI operations on its mainloop thread.
_tk_root = None
_tk_thread = None


def _ensure_tk_root():
    """Create a hidden tkinter root running in a background thread."""
    global _tk_root, _tk_thread

    if _tk_root is not None:
        return

    ready = threading.Event()

    def _run():
        global _tk_root
        try:
            import tkinter as tk
            _tk_root = tk.Tk()
            _tk_root.withdraw()  # hide the root window
            ready.set()
            _tk_root.mainloop()
        except ImportError:
            log.warning("tkinter not available — GUI features disabled")
            ready.set()
        except Exception:
            log.warning("Failed to start tkinter", exc_info=True)
            ready.set()

    _tk_thread = threading.Thread(target=_run, daemon=True, name="tkinter-main")
    _tk_thread.start()
    ready.wait(timeout=5)


def _run_on_tk(fn):
    """Schedule a function to run on the tkinter main thread."""
    if _tk_root is not None:
        _tk_root.after(0, fn)
    else:
        log.warning("No tkinter root — cannot show GUI")


def _create_icon():
    """Create a simple fallback icon (64×64 green square) if no .ico is available."""
    from PIL import Image
    return Image.new("RGB", (64, 64), color=(34, 139, 34))


def run_tray(app: "KodexApp") -> None:
    """Build and run the system-tray icon.  Blocks until the user exits."""
    import pystray

    # Ensure tkinter is ready for GUI windows
    _ensure_tk_root()

    # GUI window instances (lazy-created)
    _management_window = [None]

    def on_manage(icon, item):
        def _do():
            from kodex_py.gui.manager import ManagementWindow
            if _management_window[0] is None:
                _management_window[0] = ManagementWindow(
                    app.db, on_reload=app.reload_hotstrings
                )
            _management_window[0].show()
        _run_on_tk(_do)

    def on_new_hotstring(icon, item):
        def _do():
            from kodex_py.gui.editor import NewHotstringDialog
            dialog = NewHotstringDialog(app.db, parent=_tk_root)
            dialog.show()
            app.reload_hotstrings()
        _run_on_tk(_do)

    def on_preferences(icon, item):
        def _do():
            from kodex_py.gui.preferences import PreferencesWindow
            prefs = PreferencesWindow(app.db, parent=_tk_root)
            prefs.show()
        _run_on_tk(_do)

    def on_tracker(icon, item):
        if hasattr(app, 'tracker') and app.tracker is not None:
            msg = app.tracker.toggle()
            log.info("Tracker: %s", msg)

    def on_disable(icon, item):
        app.disabled = not app.disabled
        log.info("Kodex %s", "disabled" if app.disabled else "enabled")

    def on_exit(icon, item):
        if hasattr(app, 'tracker') and app.tracker is not None and app.tracker.is_tracking:
            app.tracker.stop()
        app.stop()
        if _tk_root is not None:
            _tk_root.after(0, _tk_root.destroy)
        icon.stop()

    def _disable_text(item):
        return "Enable" if app.disabled else "Disable"

    def _tracker_text(item):
        if hasattr(app, 'tracker') and app.tracker is not None and app.tracker.is_tracking:
            return f"Stop Tracker (#{app.tracker.ticket_number})"
        return "Start Ticket Tracker"

    icon_image = _create_icon()

    # Try to load a real icon
    try:
        from PIL import Image
        ico_path = app.db_path.parent / "resources" / "kodex.ico"
        if ico_path.exists():
            icon_image = Image.open(str(ico_path))
    except Exception:
        pass

    menu = pystray.Menu(
        pystray.MenuItem("Kodex v3.0", None, enabled=False),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Manage Hotstrings", on_manage),
        pystray.MenuItem("Create New Hotstring", on_new_hotstring),
        pystray.MenuItem("Preferences...", on_preferences),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem(_tracker_text, on_tracker),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem(_disable_text, on_disable),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Exit", on_exit),
    )

    icon = pystray.Icon("kodex", icon_image, "Kodex", menu)
    icon.run()
