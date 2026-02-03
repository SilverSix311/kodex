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
from typing import TYPE_CHECKING

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
        self._dialog = None

    def show(self) -> None:
        """Create and show the dialog (blocks until dismissed)."""
        import tkinter as tk
        from tkinter import ttk, messagebox
        from kodex_py.storage.models import Hotstring, TriggerType

        self._dialog = tk.Toplevel(self._parent)
        self._dialog.title("Kodex — New Hotstring")
        self._dialog.geometry("500x450")
        self._dialog.resizable(False, False)
        self._dialog.transient(self._parent)
        self._dialog.grab_set()

        frame = ttk.Frame(self._dialog, padding=12)
        frame.pack(fill=tk.BOTH, expand=True)

        # ── Name ──
        ttk.Label(frame, text="Hotstring name:").pack(anchor=tk.W)
        name_var = tk.StringVar()
        ttk.Entry(frame, textvariable=name_var, width=40).pack(fill=tk.X, pady=(0, 8))

        # ── Bundle ──
        ttk.Label(frame, text="Bundle:").pack(anchor=tk.W)
        bundles = self.db.get_bundles()
        bundle_names = [b.name for b in bundles]
        bundle_var = tk.StringVar(value=self._default_bundle)
        bundle_combo = ttk.Combobox(
            frame, textvariable=bundle_var, values=bundle_names, state="readonly"
        )
        bundle_combo.pack(fill=tk.X, pady=(0, 8))

        # ── Triggers ──
        trigger_frame = ttk.LabelFrame(frame, text="Triggers")
        trigger_frame.pack(fill=tk.X, pady=(0, 8))

        trigger_vars: dict[str, tk.BooleanVar] = {}
        for ttype in ("space", "tab", "enter", "instant"):
            var = tk.BooleanVar(value=(ttype == "space"))
            trigger_vars[ttype] = var
            ttk.Checkbutton(trigger_frame, text=ttype.capitalize(), variable=var).pack(
                side=tk.LEFT, padx=8, pady=4
            )

        def on_instant_toggle(*_):
            if trigger_vars["instant"].get():
                for k in ("space", "tab", "enter"):
                    trigger_vars[k].set(False)

        trigger_vars["instant"].trace_add("write", on_instant_toggle)

        # ── Script mode ──
        script_var = tk.BooleanVar()
        ttk.Checkbutton(frame, text="Script mode (::scr::)", variable=script_var).pack(
            anchor=tk.W, pady=(0, 4)
        )

        # ── Replacement text ──
        ttk.Label(frame, text="Replacement text:").pack(anchor=tk.W)
        text_widget = tk.Text(frame, wrap=tk.WORD, font=("Consolas", 10), height=10)
        text_widget.pack(fill=tk.BOTH, expand=True, pady=(0, 8))

        # ── Buttons ──
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X)

        def on_ok():
            name = name_var.get().strip()
            if not name:
                messagebox.showwarning("Kodex", "Name cannot be empty.", parent=self._dialog)
                return

            replacement = text_widget.get("1.0", tk.END).rstrip("\n")
            triggers = set()
            for ttype_key, var in trigger_vars.items():
                if var.get():
                    triggers.add(TriggerType(ttype_key))
            if not triggers:
                messagebox.showwarning(
                    "Kodex", "Select at least one trigger.", parent=self._dialog
                )
                return

            # Find bundle
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
                self._dialog.destroy()
            except Exception as e:
                messagebox.showerror("Kodex", f"Error: {e}", parent=self._dialog)

        def on_cancel():
            self._dialog.destroy()

        ttk.Button(btn_frame, text="OK", command=on_ok).pack(side=tk.RIGHT, padx=(4, 0))
        ttk.Button(btn_frame, text="Cancel", command=on_cancel).pack(side=tk.RIGHT)

        self._dialog.wait_window()
