"""Preferences window — mirrors AHK preferences_GUI.ahk.

Three tabs:
- General: hotkeys, send mode, sound, startup
- Print: cheatsheet generation
- Stats: expansion statistics
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from kodex_py.storage.database import Database

log = logging.getLogger(__name__)


class PreferencesWindow:
    """Preferences dialog with General / Print / Stats tabs."""

    def __init__(self, db: "Database", parent=None) -> None:
        self.db = db
        self._parent = parent
        self._dialog = None

    def show(self) -> None:
        import tkinter as tk
        from tkinter import ttk

        from kodex_py.config import load_config, save_config
        from kodex_py.storage.models import AppConfig, SendMode

        cfg = load_config(self.db)

        self._dialog = tk.Toplevel(self._parent)
        self._dialog.title("Kodex — Preferences")
        self._dialog.geometry("480x400")
        self._dialog.resizable(False, False)
        self._dialog.transient(self._parent)
        self._dialog.grab_set()

        notebook = ttk.Notebook(self._dialog)
        notebook.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        # ── General tab ──
        general = ttk.Frame(notebook, padding=12)
        notebook.add(general, text="General")

        # Hotkeys
        hk_frame = ttk.LabelFrame(general, text="Hotkeys")
        hk_frame.pack(fill=tk.X, pady=(0, 8))

        hotkey_create_var = tk.StringVar(value=cfg.hotkey_create)
        hotkey_manage_var = tk.StringVar(value=cfg.hotkey_manage)
        hotkey_disable_var = tk.StringVar(value=cfg.hotkey_disable)
        hotkey_tracker_var = tk.StringVar(value=cfg.hotkey_tracker)

        for label, var in [
            ("Create hotstring:", hotkey_create_var),
            ("Manage hotstrings:", hotkey_manage_var),
            ("Disable toggle:", hotkey_disable_var),
            ("Ticket tracker:", hotkey_tracker_var),
        ]:
            row = ttk.Frame(hk_frame)
            row.pack(fill=tk.X, pady=2)
            ttk.Label(row, text=label, width=20).pack(side=tk.LEFT)
            ttk.Entry(row, textvariable=var, width=20).pack(side=tk.LEFT, padx=4)

        # Send mode
        mode_frame = ttk.LabelFrame(general, text="Send Mode")
        mode_frame.pack(fill=tk.X, pady=(0, 8))
        mode_var = tk.IntVar(value=cfg.send_mode.value)
        ttk.Radiobutton(mode_frame, text="Direct (keystroke injection)", variable=mode_var, value=0).pack(
            anchor=tk.W, padx=8
        )
        ttk.Radiobutton(mode_frame, text="Clipboard (Ctrl+V paste)", variable=mode_var, value=1).pack(
            anchor=tk.W, padx=8
        )

        # Checkboxes
        sound_var = tk.BooleanVar(value=cfg.play_sound)
        startup_var = tk.BooleanVar(value=cfg.run_at_startup)
        autocorrect_var = tk.BooleanVar(value=cfg.autocorrect_enabled)

        ttk.Checkbutton(general, text="Play sound on expansion", variable=sound_var).pack(anchor=tk.W)
        ttk.Checkbutton(general, text="Run at Windows startup", variable=startup_var).pack(anchor=tk.W)
        ttk.Checkbutton(general, text="Enable autocorrect", variable=autocorrect_var).pack(anchor=tk.W)

        # ── Print tab ──
        print_tab = ttk.Frame(notebook, padding=12)
        notebook.add(print_tab, text="Print")

        ttk.Label(print_tab, text="Generate a printable HTML cheatsheet\nof all your hotstrings.").pack(
            pady=20
        )

        def _do_cheatsheet():
            from tkinter import filedialog, messagebox
            from kodex_py.gui.cheatsheet import generate_cheatsheet

            path = filedialog.asksaveasfilename(
                parent=self._dialog,
                defaultextension=".html",
                filetypes=[("HTML", "*.html")],
                initialfile="kodex-cheatsheet.html",
            )
            if path:
                generate_cheatsheet(self.db, path)
                messagebox.showinfo("Kodex", f"Cheatsheet saved to {path}", parent=self._dialog)

        ttk.Button(print_tab, text="Generate Cheatsheet", command=_do_cheatsheet).pack()

        # ── Stats tab ──
        stats_tab = ttk.Frame(notebook, padding=12)
        notebook.add(stats_tab, text="Stats")

        expanded = self.db.get_stat("expanded")
        chars = self.db.get_stat("chars_saved")
        hours = chars / 24_000 if chars else 0
        total_hs = len(self.db.get_hotstrings())
        total_bundles = len(self.db.get_bundles())

        for label, value in [
            ("Hotstrings:", str(total_hs)),
            ("Bundles:", str(total_bundles)),
            ("Expansions:", f"{expanded:,}"),
            ("Characters saved:", f"{chars:,}"),
            ("Hours saved:", f"{hours:.1f}"),
        ]:
            row = ttk.Frame(stats_tab)
            row.pack(fill=tk.X, pady=2)
            ttk.Label(row, text=label, width=20, anchor=tk.E).pack(side=tk.LEFT)
            ttk.Label(row, text=value, font=("Segoe UI", 11, "bold")).pack(side=tk.LEFT, padx=8)

        # ── Buttons ──
        btn_frame = ttk.Frame(self._dialog)
        btn_frame.pack(fill=tk.X, padx=8, pady=(0, 8))

        def on_save():
            cfg.hotkey_create = hotkey_create_var.get()
            cfg.hotkey_manage = hotkey_manage_var.get()
            cfg.hotkey_disable = hotkey_disable_var.get()
            cfg.hotkey_tracker = hotkey_tracker_var.get()
            cfg.send_mode = SendMode(mode_var.get())
            cfg.play_sound = sound_var.get()
            cfg.run_at_startup = startup_var.get()
            cfg.autocorrect_enabled = autocorrect_var.get()
            save_config(self.db, cfg)
            self._dialog.destroy()

        ttk.Button(btn_frame, text="Save", command=on_save).pack(side=tk.RIGHT, padx=(4, 0))
        ttk.Button(btn_frame, text="Cancel", command=self._dialog.destroy).pack(side=tk.RIGHT)

        self._dialog.wait_window()
