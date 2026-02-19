"""System tray icon and menu — powered by pystray with CustomTkinter GUI.

Fully connected to the GUI and ticket tracker:
    • Manage hotstrings  → opens ManagementWindow
    • Create new hotstring  → opens NewHotstringDialog
    • Preferences  → opens PreferencesWindow
    • Start/Stop Ticket Tracker
    • Disable / Enable
    • About
    • Exit

Threading model:
  - Main thread: tkinter/CTk event loop (required for GUI on Windows)
  - Background thread: pystray icon (must NOT create Tk widgets)
"""

from __future__ import annotations

import logging
import threading
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from kodex_py.app import KodexApp

log = logging.getLogger(__name__)

# Module-level reference to the hidden CTk root (set by run_tray).
# Other GUI modules import this to parent their Toplevel windows.
_tk_root = None


def get_tk_root():
    """Return the hidden root CTk window (created by run_tray)."""
    return _tk_root


def _create_icon():
    """Create a simple fallback icon (64×64 green square) if no .ico is available."""
    from PIL import Image

    return Image.new("RGB", (64, 64), color=(34, 139, 34))


def run_tray(app: "KodexApp") -> None:
    """Build and run the system-tray icon with CustomTkinter GUI support.

    Threading model:
      - Main thread: CTk event loop (blocks here via root.mainloop())
      - Background thread: pystray icon
    """
    import customtkinter as ctk
    import pystray

    global _tk_root

    # ── Configure CustomTkinter ──────────────────────────────────────
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")

    # Hidden root window — all Toplevel windows are children of this.
    root = ctk.CTk()
    root.withdraw()         # Keep hidden; we live in the tray
    root.title("Kodex")
    root.protocol("WM_DELETE_WINDOW", lambda: None)  # Prevent accidental close
    _tk_root = root

    # ── Cached GUI window instances ──────────────────────────────────
    _management_window: list = [None]   # list so lambda can rebind

    # ── Helpers ─────────────────────────────────────────────────────

    def _schedule(fn) -> None:
        """Schedule *fn* to run on the tkinter main thread (safe from any thread)."""
        root.after(0, fn)

    # ── Tray callbacks (run on the pystray thread) ───────────────────

    def on_manage(icon, item) -> None:
        def _do():
            from kodex_py.gui.manager import ManagementWindow

            win = _management_window[0]
            if win is None or not win._window or not win._window.winfo_exists():
                _management_window[0] = ManagementWindow(
                    app.db, on_reload=app.reload_hotstrings, parent=root
                )
            _management_window[0].show()

        _schedule(_do)

    def on_new_hotstring(icon, item) -> None:
        def _do():
            from kodex_py.gui.editor import NewHotstringDialog

            dialog = NewHotstringDialog(app.db, default_bundle="Default", parent=root)
            dialog.show()
            app.reload_hotstrings()

        _schedule(_do)

    def on_preferences(icon, item) -> None:
        def _do():
            from kodex_py.gui.preferences import PreferencesWindow

            PreferencesWindow(app.db, parent=root).show()

        _schedule(_do)

    def on_tracker(icon, item) -> None:
        if hasattr(app, "tracker") and app.tracker is not None:
            msg = app.tracker.toggle()
            log.info("Tracker: %s", msg)

    def on_disable(icon, item) -> None:
        app.disabled = not app.disabled
        log.info("Kodex %s", "disabled" if app.disabled else "enabled")

    def on_exit(icon, item) -> None:
        def _do():
            import os
            import sys
            
            log.info("Exit requested — shutting down")
            
            try:
                if hasattr(app, "tracker") and app.tracker is not None and app.tracker.is_tracking:
                    app.tracker.stop()
                app.stop()
            except Exception as e:
                log.warning("Error during app.stop(): %s", e)
            
            try:
                icon.stop()
            except Exception as e:
                log.warning("Error stopping tray icon: %s", e)
            
            try:
                root.quit()
                root.destroy()
            except Exception as e:
                log.warning("Error destroying root window: %s", e)
            
            # Force exit after a short delay if threads don't stop cleanly
            def _force_exit():
                log.info("Force exiting process")
                os._exit(0)
            
            # Give threads 1 second to clean up, then force exit
            force_timer = threading.Timer(1.0, _force_exit)
            force_timer.daemon = True
            force_timer.start()

        _schedule(_do)

    # Dynamic label callbacks (called by pystray to refresh menu text)
    def _disable_text(item) -> str:
        return "Enable" if app.disabled else "Disable"

    def _tracker_text(item) -> str:
        if hasattr(app, "tracker") and app.tracker is not None and app.tracker.is_tracking:
            return f"Stop Tracker (#{app.tracker.ticket_number})"
        return "Start Ticket Tracker"

    # ── Icon image ───────────────────────────────────────────────────
    icon_image = _create_icon()
    try:
        from PIL import Image

        ico_path = app.db_path.parent / "resources" / "kodex.ico"
        if ico_path.exists():
            icon_image = Image.open(str(ico_path))
    except Exception:
        pass

    # ── pystray menu ────────────────────────────────────────────────
    menu = pystray.Menu(
        pystray.MenuItem("Kodex v3.0", None, enabled=False),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Manage Hotstrings", on_manage),
        pystray.MenuItem("Create New Hotstring", on_new_hotstring),
        pystray.MenuItem("Preferences…", on_preferences),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem(_tracker_text, on_tracker),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem(_disable_text, on_disable),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Exit", on_exit),
    )

    icon = pystray.Icon("kodex", icon_image, "Kodex", menu)

    # ── Launch pystray in background thread ─────────────────────────
    tray_thread = threading.Thread(target=icon.run, daemon=True, name="pystray")
    tray_thread.start()

    # ── Run CTk event loop on main thread (blocks until root.quit()) ─
    log.info("Starting CTk event loop on main thread")
    root.mainloop()
    log.info("CTk event loop exited")
