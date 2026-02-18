"""System tray icon and menu — powered by pystray with Dear PyGui GUI.

Fully connected to the GUI and ticket tracker:
    • Manage hotstrings  → opens ManagementWindow
    • Create new hotstring  → opens NewHotstringDialog
    • Preferences  → opens PreferencesWindow
    • Start/Stop Ticket Tracker
    • Disable / Enable
    • About
    • Exit

Threading model:
  - Main thread: Dear PyGui render loop (required for responsive GUI)
  - Background thread: pystray icon
"""

from __future__ import annotations

import logging
import threading
from typing import TYPE_CHECKING

import dearpygui.dearpygui as dpg

if TYPE_CHECKING:
    from kodex_py.app import KodexApp

log = logging.getLogger(__name__)

# Global flag for shutdown coordination
_shutdown_requested = False


def _create_icon():
    """Create a simple fallback icon (64×64 green square) if no .ico is available."""
    from PIL import Image

    return Image.new("RGB", (64, 64), color=(34, 139, 34))


def run_tray(app: "KodexApp") -> None:
    """Build and run the system-tray icon with Dear PyGui GUI support.

    Threading model:
      - Main thread: Dear PyGui render loop (required for responsive GUI on Windows)
      - Background thread: pystray icon
    """
    import pystray

    global _shutdown_requested
    _shutdown_requested = False

    # ── Initialize Dear PyGui ──
    dpg.create_context()
    dpg.create_viewport(title="Kodex", width=900, height=600, min_width=600, min_height=400)

    dpg.setup_dearpygui()
    dpg.show_viewport()

    # Start minimized - we're tray-only by default
    dpg.minimize_viewport()

    # GUI window instances (lazy-created)
    _management_window = [None]

    # Thread-safe queue for GUI actions
    _gui_actions = []
    _gui_lock = threading.Lock()

    def _schedule(fn):
        """Schedule a function to run on the Dear PyGui main thread."""
        with _gui_lock:
            _gui_actions.append(fn)

    def _process_scheduled():
        """Process any scheduled GUI actions (called from main loop)."""
        with _gui_lock:
            actions = _gui_actions.copy()
            _gui_actions.clear()
        for fn in actions:
            try:
                fn()
            except Exception as e:
                log.error("Error in scheduled GUI action: %s", e)

    def on_manage(icon, item):
        def _do():
            from kodex_py.gui.manager import ManagementWindow

            if _management_window[0] is None:
                _management_window[0] = ManagementWindow(
                    app.db, on_reload=app.reload_hotstrings
                )
            _management_window[0].show()

        _schedule(_do)

    def on_new_hotstring(icon, item):
        def _do():
            from kodex_py.gui.editor import NewHotstringDialog

            dialog = NewHotstringDialog(app.db)
            dialog.show()
            app.reload_hotstrings()

        _schedule(_do)

    def on_preferences(icon, item):
        def _do():
            from kodex_py.gui.preferences import PreferencesWindow

            prefs = PreferencesWindow(app.db)
            prefs.show()

        _schedule(_do)

    def on_tracker(icon, item):
        if hasattr(app, "tracker") and app.tracker is not None:
            msg = app.tracker.toggle()
            log.info("Tracker: %s", msg)

    def on_disable(icon, item):
        app.disabled = not app.disabled
        log.info("Kodex %s", "disabled" if app.disabled else "enabled")

    def on_exit(icon, item):
        global _shutdown_requested
        if hasattr(app, "tracker") and app.tracker is not None and app.tracker.is_tracking:
            app.tracker.stop()
        app.stop()
        icon.stop()
        _shutdown_requested = True

    def _disable_text(item):
        return "Enable" if app.disabled else "Disable"

    def _tracker_text(item):
        if hasattr(app, "tracker") and app.tracker is not None and app.tracker.is_tracking:
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

    # Run pystray in a background thread
    tray_thread = threading.Thread(target=icon.run, daemon=True, name="pystray")
    tray_thread.start()

    # ── Main Dear PyGui render loop ──
    while dpg.is_dearpygui_running() and not _shutdown_requested:
        # Process scheduled GUI actions from other threads
        _process_scheduled()
        dpg.render_dearpygui_frame()

    # Cleanup
    dpg.destroy_context()
