"""New Hotstring dialog — quick-create form.

Mirrors AHK newkey_GUI.ahk:
- Hotstring name input
- Replacement text area
- Text/Script mode toggle
- Bundle selector
- Trigger checkboxes with mutual exclusion logic
"""

from __future__ import annotations

import logging
import tkinter as tk
from tkinter import messagebox
from typing import TYPE_CHECKING

import customtkinter as ctk

if TYPE_CHECKING:
    from kodex_py.storage.database import Database

log = logging.getLogger(__name__)


class NewHotstringDialog:
    """Modal dialog for creating a new hotstring."""

    def __init__(
        self,
        db: "Database",
        *,
        default_bundle: str = "Default",
        parent=None,
    ) -> None:
        self.db = db
        self._default_bundle = default_bundle
        self._parent = parent

    def show(self) -> None:
        """Create and show the dialog (blocks until dismissed)."""
        from kodex_py.storage.models import Hotstring, TriggerType

        bundles = self.db.get_bundles()
        bundle_names = [b.name for b in bundles] or ["Default"]

        default_idx = 0
        for i, name in enumerate(bundle_names):
            if name == self._default_bundle:
                default_idx = i
                break

        win = ctk.CTkToplevel(self._parent)
        win.title("Kodex — New Hotstring")
        win.geometry("540x510")
        win.resizable(True, True)
        win.grab_set()
        win.lift()
        win.focus_force()
        
        # Set window icon
        from kodex_py.gui.manager import _set_window_icon
        _set_window_icon(win, self.db)

        # ── Variables ──
        name_var = tk.StringVar()
        bundle_var = tk.StringVar(value=bundle_names[default_idx])
        script_var = tk.BooleanVar()
        trig_space_var = tk.BooleanVar(value=True)
        trig_tab_var = tk.BooleanVar()
        trig_enter_var = tk.BooleanVar()
        trig_instant_var = tk.BooleanVar()

        def _on_instant_toggle():
            if trig_instant_var.get():
                trig_space_var.set(False)
                trig_tab_var.set(False)
                trig_enter_var.set(False)

        # ── Layout ──
        outer = ctk.CTkFrame(win, fg_color="transparent")
        outer.pack(fill="both", expand=True, padx=16, pady=16)

        # Name
        ctk.CTkLabel(outer, text="Hotstring name:", anchor="w").pack(fill="x", pady=(0, 4))
        name_entry = ctk.CTkEntry(outer, textvariable=name_var)
        name_entry.pack(fill="x", pady=(0, 10))

        # Bundle
        ctk.CTkLabel(outer, text="Bundle:", anchor="w").pack(fill="x", pady=(0, 4))
        bundle_combo = ctk.CTkComboBox(outer, values=bundle_names, variable=bundle_var)
        bundle_combo.pack(fill="x", pady=(0, 10))

        # Triggers
        trig_frame = ctk.CTkFrame(outer, corner_radius=6)
        trig_frame.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(
            trig_frame, text="Triggers", font=ctk.CTkFont(weight="bold"), anchor="w"
        ).pack(anchor="w", padx=12, pady=(8, 4))
        trig_row = ctk.CTkFrame(trig_frame, fg_color="transparent")
        trig_row.pack(fill="x", padx=12, pady=(0, 10))
        ctk.CTkCheckBox(trig_row, text="Space", variable=trig_space_var).pack(
            side="left", padx=(0, 12)
        )
        ctk.CTkCheckBox(trig_row, text="Tab", variable=trig_tab_var).pack(
            side="left", padx=(0, 12)
        )
        ctk.CTkCheckBox(trig_row, text="Enter", variable=trig_enter_var).pack(
            side="left", padx=(0, 12)
        )
        ctk.CTkCheckBox(
            trig_row,
            text="Instant",
            variable=trig_instant_var,
            command=_on_instant_toggle,
        ).pack(side="left")

        # Script mode
        ctk.CTkCheckBox(outer, text="Script mode (::scr::)", variable=script_var).pack(
            anchor="w", pady=(0, 10)
        )

        # Replacement text
        ctk.CTkLabel(outer, text="Replacement text:", anchor="w").pack(fill="x", pady=(0, 4))
        text_box = ctk.CTkTextbox(outer, height=160, wrap="word")
        text_box.pack(fill="both", expand=True, pady=(0, 14))

        # ── Callbacks ──
        def _on_ok(_event=None):
            name = name_var.get().strip()
            if not name:
                messagebox.showwarning("Kodex", "Name cannot be empty.", parent=win)
                return

            replacement = text_box.get("1.0", tk.END).rstrip("\n")
            triggers: set[TriggerType] = set()
            if trig_space_var.get():
                triggers.add(TriggerType.SPACE)
            if trig_tab_var.get():
                triggers.add(TriggerType.TAB)
            if trig_enter_var.get():
                triggers.add(TriggerType.ENTER)
            if trig_instant_var.get():
                triggers.add(TriggerType.INSTANT)

            if not triggers:
                messagebox.showwarning("Kodex", "Select at least one trigger.", parent=win)
                return

            bname = bundle_var.get()
            bundle = self.db.get_bundle_by_name(bname)
            if bundle is None:
                bundle = self.db.create_bundle(bname)

            hs = Hotstring(
                name=name,
                replacement=replacement,
                is_script=script_var.get(),
                bundle_id=bundle.id,
                triggers=triggers,
            )
            try:
                self.db.save_hotstring(hs)
                win.grab_release()
                win.destroy()
            except Exception as e:
                messagebox.showerror("Kodex", f"Error saving hotstring: {e}", parent=win)

        def _on_cancel(_event=None):
            win.grab_release()
            win.destroy()

        win.bind("<Escape>", _on_cancel)

        # Buttons
        btn_row = ctk.CTkFrame(outer, fg_color="transparent")
        btn_row.pack(fill="x")
        ctk.CTkButton(btn_row, text="Cancel", command=_on_cancel, width=80).pack(
            side="left", padx=(0, 8)
        )
        ctk.CTkButton(btn_row, text="OK", command=_on_ok, width=80).pack(side="left")

        name_entry.focus_set()
        win.wait_window()
