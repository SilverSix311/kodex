"""Management window — main hub for hotstring management.

Mirrors the AHK management_GUI.ahk:
- Tab control with one tab per bundle
- Hotstring list with search/filter
- Edit area for replacement text
- Trigger checkboxes
- Text/Script mode toggle
- Bundle management menu
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from kodex_py.storage.database import Database
    from kodex_py.storage.models import Bundle, Hotstring

log = logging.getLogger(__name__)


class ManagementWindow:
    """Main hotstring management window."""

    def __init__(
        self,
        db: "Database",
        on_reload: Callable[[], None] | None = None,
    ) -> None:
        self.db = db
        self._on_reload = on_reload
        self._root = None
        self._current_bundle_id: int | None = None
        self._current_hs_id: int | None = None
        self._search_var = None
        self._hotstring_listbox = None
        self._replacement_text = None
        self._name_var = None
        self._trigger_vars: dict[str, object] = {}
        self._script_var = None
        self._bundle_tabs = None
        self._hotstrings_cache: list["Hotstring"] = []

    def show(self) -> None:
        """Create and show the management window."""
        import tkinter as tk
        from tkinter import ttk, messagebox

        if self._root is not None:
            self._root.lift()
            self._root.focus_force()
            return

        self._root = tk.Toplevel()
        self._root.title("Kodex — Manage Hotstrings")
        self._root.geometry("900x600")
        self._root.minsize(700, 450)
        self._root.protocol("WM_DELETE_WINDOW", self._on_close)

        # ── Menu bar ──
        menubar = tk.Menu(self._root)
        self._root.config(menu=menubar)

        tools_menu = tk.Menu(menubar, tearoff=0)
        tools_menu.add_command(label="Preferences...", command=self._open_preferences)
        tools_menu.add_command(label="Printable Cheatsheet", command=self._generate_cheatsheet)
        menubar.add_cascade(label="Tools", menu=tools_menu)

        bundles_menu = tk.Menu(menubar, tearoff=0)
        bundles_menu.add_command(label="New Bundle...", command=self._new_bundle)
        bundles_menu.add_command(label="Rename Bundle...", command=self._rename_bundle)
        bundles_menu.add_command(label="Delete Bundle...", command=self._delete_bundle)
        bundles_menu.add_separator()
        bundles_menu.add_command(label="Export Bundle...", command=self._export_bundle)
        bundles_menu.add_command(label="Import Bundle...", command=self._import_bundle)
        menubar.add_cascade(label="Bundles", menu=bundles_menu)

        # ── Search bar ──
        search_frame = ttk.Frame(self._root)
        search_frame.pack(fill=tk.X, padx=8, pady=(8, 0))

        ttk.Label(search_frame, text="Search:").pack(side=tk.LEFT, padx=(0, 4))
        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", lambda *_: self._filter_list())
        search_entry = ttk.Entry(search_frame, textvariable=self._search_var, width=30)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # ── Bundle tabs ──
        self._bundle_tabs = ttk.Notebook(self._root)
        self._bundle_tabs.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)
        self._bundle_tabs.bind("<<NotebookTabChanged>>", self._on_tab_changed)

        # ── Main content pane (inside each tab) ──
        self._content_frame = ttk.Frame(self._root)
        # We'll build the shared content area below the tabs
        content = ttk.Frame(self._root)
        content.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))

        # Left: hotstring list
        left = ttk.Frame(content)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=False)

        self._hotstring_listbox = tk.Listbox(left, width=30, font=("Consolas", 10))
        self._hotstring_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._hotstring_listbox.bind("<<ListboxSelect>>", self._on_select)

        scrollbar = ttk.Scrollbar(left, orient=tk.VERTICAL, command=self._hotstring_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self._hotstring_listbox.config(yscrollcommand=scrollbar.set)

        # Right: editor
        right = ttk.Frame(content)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(8, 0))

        # Name
        name_frame = ttk.Frame(right)
        name_frame.pack(fill=tk.X, pady=(0, 4))
        ttk.Label(name_frame, text="Name:").pack(side=tk.LEFT)
        self._name_var = tk.StringVar()
        ttk.Entry(name_frame, textvariable=self._name_var, width=30).pack(side=tk.LEFT, padx=(4, 0))

        # Script mode
        self._script_var = tk.BooleanVar()
        ttk.Checkbutton(name_frame, text="Script mode", variable=self._script_var).pack(side=tk.RIGHT)

        # Triggers
        trigger_frame = ttk.LabelFrame(right, text="Triggers")
        trigger_frame.pack(fill=tk.X, pady=(0, 4))
        for ttype in ("space", "tab", "enter", "instant"):
            var = tk.BooleanVar()
            self._trigger_vars[ttype] = var
            cb = ttk.Checkbutton(trigger_frame, text=ttype.capitalize(), variable=var)
            cb.pack(side=tk.LEFT, padx=8)
            if ttype == "instant":
                var.trace_add("write", lambda *_, v=var: self._on_instant_toggle(v))

        # Replacement text
        ttk.Label(right, text="Replacement:").pack(anchor=tk.W)
        self._replacement_text = tk.Text(right, wrap=tk.WORD, font=("Consolas", 10), height=12)
        self._replacement_text.pack(fill=tk.BOTH, expand=True)

        # Buttons
        btn_frame = ttk.Frame(right)
        btn_frame.pack(fill=tk.X, pady=(4, 0))
        ttk.Button(btn_frame, text="+ New", command=self._new_hotstring).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(btn_frame, text="Save", command=self._save_hotstring).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(btn_frame, text="Delete", command=self._delete_hotstring).pack(side=tk.LEFT)

        # Populate
        self._rebuild_tabs()

    def _on_close(self) -> None:
        if self._root:
            self._root.destroy()
            self._root = None

    # ── Tab management ──

    def _rebuild_tabs(self) -> None:
        import tkinter as tk
        from tkinter import ttk

        if self._bundle_tabs is None:
            return
        # Clear existing tabs
        for tab_id in self._bundle_tabs.tabs():
            self._bundle_tabs.forget(tab_id)

        bundles = self.db.get_bundles()
        for b in bundles:
            frame = ttk.Frame(self._bundle_tabs)
            # Store bundle id as widget name
            frame._bundle_id = b.id  # type: ignore[attr-defined]
            label = f"{b.name}" + ("" if b.enabled else " (disabled)")
            self._bundle_tabs.add(frame, text=label)

        if bundles:
            self._current_bundle_id = bundles[0].id
            self._load_hotstrings()

    def _on_tab_changed(self, event) -> None:
        if self._bundle_tabs is None:
            return
        sel = self._bundle_tabs.select()
        if sel:
            tab_widget = self._bundle_tabs.nametowidget(sel)
            bid = getattr(tab_widget, "_bundle_id", None)
            if bid is not None:
                self._current_bundle_id = bid
                self._load_hotstrings()

    # ── Hotstring list ──

    def _load_hotstrings(self) -> None:
        if self._current_bundle_id is None:
            return
        self._hotstrings_cache = self.db.get_hotstrings(bundle_id=self._current_bundle_id)
        self._filter_list()

    def _filter_list(self) -> None:
        import tkinter as tk

        if self._hotstring_listbox is None:
            return
        query = (self._search_var.get() if self._search_var else "").lower()
        self._hotstring_listbox.delete(0, tk.END)
        for hs in self._hotstrings_cache:
            if query and query not in hs.name.lower() and query not in hs.replacement.lower():
                continue
            self._hotstring_listbox.insert(tk.END, hs.name)

    def _on_select(self, event) -> None:
        import tkinter as tk

        if self._hotstring_listbox is None:
            return
        sel = self._hotstring_listbox.curselection()
        if not sel:
            return
        name = self._hotstring_listbox.get(sel[0])
        # Find in cache
        for hs in self._hotstrings_cache:
            if hs.name == name:
                self._show_hotstring(hs)
                break

    def _show_hotstring(self, hs: "Hotstring") -> None:
        import tkinter as tk
        from kodex_py.storage.models import TriggerType

        self._current_hs_id = hs.id
        self._name_var.set(hs.name)
        self._script_var.set(hs.is_script)
        self._replacement_text.delete("1.0", tk.END)
        self._replacement_text.insert("1.0", hs.replacement)

        for ttype in ("space", "tab", "enter", "instant"):
            self._trigger_vars[ttype].set(TriggerType(ttype) in hs.triggers)

    # ── Trigger logic ──

    def _on_instant_toggle(self, instant_var) -> None:
        """When Instant is checked, uncheck other triggers (mutually exclusive)."""
        if instant_var.get():
            for key in ("space", "tab", "enter"):
                self._trigger_vars[key].set(False)

    # ── CRUD ──

    def _new_hotstring(self) -> None:
        from kodex_py.gui.editor import NewHotstringDialog
        bundles = self.db.get_bundles()
        current_bundle = next(
            (b.name for b in bundles if b.id == self._current_bundle_id), "Default"
        )
        dialog = NewHotstringDialog(self.db, default_bundle=current_bundle, parent=self._root)
        dialog.show()
        self._load_hotstrings()
        if self._on_reload:
            self._on_reload()

    def _save_hotstring(self) -> None:
        import tkinter as tk
        from tkinter import messagebox
        from kodex_py.storage.models import Hotstring, TriggerType

        name = self._name_var.get().strip()
        if not name:
            messagebox.showwarning("Kodex", "Hotstring name cannot be empty.")
            return

        replacement = self._replacement_text.get("1.0", tk.END).rstrip("\n")
        triggers = set()
        for ttype in ("space", "tab", "enter", "instant"):
            if self._trigger_vars[ttype].get():
                triggers.add(TriggerType(ttype))

        if not triggers:
            messagebox.showwarning("Kodex", "Select at least one trigger type.")
            return

        hs = Hotstring(
            id=self._current_hs_id,
            name=name,
            replacement=replacement,
            is_script=self._script_var.get(),
            bundle_id=self._current_bundle_id,
            triggers=triggers,
        )
        self.db.save_hotstring(hs)
        self._load_hotstrings()
        if self._on_reload:
            self._on_reload()

    def _delete_hotstring(self) -> None:
        from tkinter import messagebox

        if self._current_hs_id is None:
            return
        name = self._name_var.get()
        if messagebox.askyesno("Kodex", f"Delete hotstring '{name}'?"):
            self.db.delete_hotstring(self._current_hs_id)
            self._current_hs_id = None
            self._load_hotstrings()
            self._clear_editor()
            if self._on_reload:
                self._on_reload()

    def _clear_editor(self) -> None:
        import tkinter as tk
        self._name_var.set("")
        self._script_var.set(False)
        self._replacement_text.delete("1.0", tk.END)
        for v in self._trigger_vars.values():
            v.set(False)

    # ── Bundle management ──

    def _new_bundle(self) -> None:
        from tkinter import simpledialog
        name = simpledialog.askstring("New Bundle", "Bundle name:", parent=self._root)
        if name and name.strip():
            self.db.create_bundle(name.strip())
            self._rebuild_tabs()

    def _rename_bundle(self) -> None:
        from tkinter import simpledialog, messagebox

        if self._current_bundle_id is None:
            return
        bundles = self.db.get_bundles()
        current = next((b for b in bundles if b.id == self._current_bundle_id), None)
        if current is None:
            return
        if current.name == "Default":
            messagebox.showinfo("Kodex", "Cannot rename the Default bundle.")
            return
        new_name = simpledialog.askstring(
            "Rename Bundle", f"New name for '{current.name}':", parent=self._root
        )
        if new_name and new_name.strip():
            self.db._conn.execute(
                "UPDATE bundles SET name = ? WHERE id = ?",
                (new_name.strip(), self._current_bundle_id),
            )
            self.db._conn.commit()
            self._rebuild_tabs()

    def _delete_bundle(self) -> None:
        from tkinter import messagebox

        if self._current_bundle_id is None:
            return
        bundles = self.db.get_bundles()
        current = next((b for b in bundles if b.id == self._current_bundle_id), None)
        if current is None:
            return
        if current.name == "Default":
            messagebox.showinfo("Kodex", "Cannot delete the Default bundle.")
            return
        if messagebox.askyesno("Kodex", f"Delete bundle '{current.name}' and all its hotstrings?"):
            self.db.delete_bundle(self._current_bundle_id)
            self._rebuild_tabs()
            if self._on_reload:
                self._on_reload()

    def _export_bundle(self) -> None:
        from tkinter import filedialog, messagebox
        from kodex_py.storage.bundle_io import export_bundle

        if self._current_bundle_id is None:
            return
        bundles = self.db.get_bundles()
        current = next((b for b in bundles if b.id == self._current_bundle_id), None)
        if current is None:
            return
        path = filedialog.asksaveasfilename(
            parent=self._root,
            defaultextension=".kodex",
            filetypes=[("Kodex bundle", "*.kodex"), ("All files", "*.*")],
            initialfile=f"{current.name}.kodex",
        )
        if path:
            count = export_bundle(self.db, current.name, path)
            messagebox.showinfo("Kodex", f"Exported {count} hotstrings to {path}")

    def _import_bundle(self) -> None:
        from tkinter import filedialog, messagebox
        from kodex_py.storage.bundle_io import import_bundle

        path = filedialog.askopenfilename(
            parent=self._root,
            filetypes=[("Kodex bundle", "*.kodex"), ("All files", "*.*")],
        )
        if path:
            count = import_bundle(self.db, path)
            messagebox.showinfo("Kodex", f"Imported {count} hotstrings")
            self._rebuild_tabs()
            if self._on_reload:
                self._on_reload()

    # ── Tools ──

    def _open_preferences(self) -> None:
        from kodex_py.gui.preferences import PreferencesWindow
        prefs = PreferencesWindow(self.db, parent=self._root)
        prefs.show()

    def _generate_cheatsheet(self) -> None:
        from tkinter import filedialog, messagebox
        from kodex_py.gui.cheatsheet import generate_cheatsheet

        path = filedialog.asksaveasfilename(
            parent=self._root,
            defaultextension=".html",
            filetypes=[("HTML", "*.html"), ("All files", "*.*")],
            initialfile="kodex-cheatsheet.html",
        )
        if path:
            generate_cheatsheet(self.db, path)
            messagebox.showinfo("Kodex", f"Cheatsheet saved to {path}")
