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
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
from typing import TYPE_CHECKING, Callable

import customtkinter as ctk

if TYPE_CHECKING:
    from kodex_py.storage.database import Database
    from kodex_py.storage.models import Bundle, Hotstring

log = logging.getLogger(__name__)

# Colours for native Listbox (matches CTk dark theme)
_LIST_BG = "#2b2b2b"
_LIST_FG = "#dce4ee"
_LIST_SELECT_BG = "#1f6aa5"
_LIST_FONT = ("Helvetica", 12)


class ManagementWindow:
    """Main hotstring management window."""

    def __init__(
        self,
        db: "Database",
        on_reload: Callable[[], None] | None = None,
        parent=None,
    ) -> None:
        self.db = db
        self._on_reload = on_reload
        self._parent = parent

        # Window state
        self._window: ctk.CTkToplevel | None = None
        self._tabview: ctk.CTkTabview | None = None

        # Bundle → listbox mapping, rebuilt with tabs
        self._bundle_listboxes: dict[int, tk.Listbox] = {}
        self._tab_names: list[str] = []          # names in order (for deletion)
        self._bundle_name_to_id: dict[str, int] = {}

        # Selected state
        self._current_bundle_id: int | None = None
        self._current_hs_id: int | None = None
        self._hotstrings_cache: list["Hotstring"] = []

        # Editor widget variables (created during _build_window, reused across tab rebuilds)
        self._search_var: tk.StringVar | None = None
        self._name_var: tk.StringVar | None = None
        self._script_var: tk.BooleanVar | None = None
        self._replacement_text: ctk.CTkTextbox | None = None
        self._trig_space_var: tk.BooleanVar | None = None
        self._trig_tab_var: tk.BooleanVar | None = None
        self._trig_enter_var: tk.BooleanVar | None = None
        self._trig_instant_var: tk.BooleanVar | None = None

    # ── Public API ──────────────────────────────────────────────────

    def show(self) -> None:
        """Create and show the management window (or bring to front if already open)."""
        if self._window is not None and self._window.winfo_exists():
            self._window.deiconify()
            self._window.lift()
            self._window.focus_force()
            return
        self._build_window()

    # ── Window construction ──────────────────────────────────────────

    def _build_window(self) -> None:
        win = ctk.CTkToplevel(self._parent)
        self._window = win
        win.title("Kodex — Manage Hotstrings")
        win.geometry("980x700")
        win.minsize(720, 520)

        # ── Variables ──
        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", lambda *_: self._filter_list())
        self._name_var = tk.StringVar()
        self._script_var = tk.BooleanVar()
        self._trig_space_var = tk.BooleanVar(value=True)
        self._trig_tab_var = tk.BooleanVar()
        self._trig_enter_var = tk.BooleanVar()
        self._trig_instant_var = tk.BooleanVar()

        # ── Menu bar ──
        menubar = tk.Menu(win)

        _m_kw = dict(tearoff=0, bg="#2b2b2b", fg="#dce4ee",
                     activebackground="#1f6aa5", activeforeground="white")

        tools_menu = tk.Menu(menubar, **_m_kw)
        tools_menu.add_command(label="Preferences…", command=self._open_preferences)
        tools_menu.add_command(label="Printable Cheatsheet", command=self._generate_cheatsheet)
        menubar.add_cascade(label="Tools", menu=tools_menu)

        bundles_menu = tk.Menu(menubar, **_m_kw)
        bundles_menu.add_command(label="New Bundle…", command=self._new_bundle)
        bundles_menu.add_command(label="Rename Bundle…", command=self._rename_bundle)
        bundles_menu.add_command(label="Delete Bundle…", command=self._delete_bundle)
        bundles_menu.add_separator()
        bundles_menu.add_command(label="Export Bundle…", command=self._export_bundle)
        bundles_menu.add_command(label="Import Bundle…", command=self._import_bundle)
        menubar.add_cascade(label="Bundles", menu=bundles_menu)

        win.config(menu=menubar)

        # ── Outer frame ──
        outer = ctk.CTkFrame(win, fg_color="transparent")
        outer.pack(fill="both", expand=True, padx=10, pady=10)

        # ── Search bar ──
        search_row = ctk.CTkFrame(outer, fg_color="transparent")
        search_row.pack(fill="x", pady=(0, 8))
        ctk.CTkLabel(search_row, text="Search:").pack(side="left", padx=(0, 8))
        ctk.CTkEntry(search_row, textvariable=self._search_var, width=320).pack(side="left")

        # ── Content: tabs (left) + editor (right) ──
        content = ctk.CTkFrame(outer, fg_color="transparent")
        content.pack(fill="both", expand=True, pady=(0, 8))
        content.grid_columnconfigure(0, weight=0, minsize=290)
        content.grid_columnconfigure(1, weight=1)
        content.grid_rowconfigure(0, weight=1)

        # Left: bundle tabs with embedded listboxes
        tabs_container = ctk.CTkFrame(content, fg_color="transparent")
        tabs_container.grid(row=0, column=0, sticky="nsew")

        self._tabview = ctk.CTkTabview(tabs_container, command=self._on_tab_change)
        self._tabview.pack(fill="both", expand=True)

        # Right: editor panel
        editor_frame = ctk.CTkFrame(content)
        editor_frame.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        self._build_editor(editor_frame)

        # ── Bottom buttons ──
        btn_row = ctk.CTkFrame(outer, fg_color="transparent")
        btn_row.pack(fill="x")
        ctk.CTkButton(btn_row, text="+ New", command=self._new_hotstring, width=88).pack(
            side="left", padx=(0, 8)
        )
        ctk.CTkButton(btn_row, text="Save", command=self._save_hotstring, width=88).pack(
            side="left", padx=(0, 8)
        )
        ctk.CTkButton(
            btn_row, text="Delete", command=self._delete_hotstring, width=88,
            fg_color="#8B0000", hover_color="#A50000"
        ).pack(side="left")

        # ── Populate tabs ──
        self._rebuild_tabs()

    def _build_editor(self, parent: ctk.CTkFrame) -> None:
        """Build the editor panel (called once; widgets bound to instance vars)."""
        pad = {"padx": 12, "pady": (0, 8)}

        # Name + script mode
        name_row = ctk.CTkFrame(parent, fg_color="transparent")
        name_row.pack(fill="x", padx=12, pady=(12, 8))
        ctk.CTkLabel(name_row, text="Name:").pack(side="left", padx=(0, 8))
        ctk.CTkEntry(name_row, textvariable=self._name_var, width=200).pack(side="left")
        ctk.CTkCheckBox(
            name_row, text="Script mode", variable=self._script_var
        ).pack(side="left", padx=(16, 0))

        # Triggers
        trig_outer = ctk.CTkFrame(parent, corner_radius=6, fg_color=("gray85", "gray20"))
        trig_outer.pack(fill="x", **pad)
        ctk.CTkLabel(
            trig_outer, text="Triggers", font=ctk.CTkFont(weight="bold"), anchor="w"
        ).pack(anchor="w", padx=12, pady=(8, 4))
        trig_row = ctk.CTkFrame(trig_outer, fg_color="transparent")
        trig_row.pack(fill="x", padx=12, pady=(0, 8))
        ctk.CTkCheckBox(trig_row, text="Space", variable=self._trig_space_var).pack(
            side="left", padx=(0, 12)
        )
        ctk.CTkCheckBox(trig_row, text="Tab", variable=self._trig_tab_var).pack(
            side="left", padx=(0, 12)
        )
        ctk.CTkCheckBox(trig_row, text="Enter", variable=self._trig_enter_var).pack(
            side="left", padx=(0, 12)
        )
        ctk.CTkCheckBox(
            trig_row, text="Instant",
            variable=self._trig_instant_var,
            command=self._on_instant_toggle,
        ).pack(side="left")

        # Replacement text
        ctk.CTkLabel(parent, text="Replacement:", anchor="w").pack(
            anchor="w", padx=12, pady=(0, 4)
        )
        self._replacement_text = ctk.CTkTextbox(parent, wrap="word")
        self._replacement_text.pack(fill="both", expand=True, padx=12, pady=(0, 12))

    # ── Tab management ──────────────────────────────────────────────

    def _rebuild_tabs(self, preserve_bundle: int | None = None) -> None:
        """Rebuild bundle tabs from database. Preserves selection if possible."""
        if self._tabview is None:
            return

        # Remember which bundle we're on (if not given)
        if preserve_bundle is None:
            preserve_bundle = self._current_bundle_id

        # Delete all existing tabs
        for name in list(self._tab_names):
            try:
                self._tabview.delete(name)
            except Exception:
                pass
        self._tab_names.clear()
        self._bundle_listboxes.clear()
        self._bundle_name_to_id.clear()

        bundles = self.db.get_bundles()
        for b in bundles:
            label = b.name + ("" if b.enabled else " (disabled)")
            tab_frame = self._tabview.add(label)
            self._tab_names.append(label)
            self._bundle_name_to_id[label] = b.id

            # Listbox with scrollbar inside the tab frame
            lb_frame = ctk.CTkFrame(tab_frame, fg_color="transparent")
            lb_frame.pack(fill="both", expand=True, padx=4, pady=4)

            scrollbar = tk.Scrollbar(lb_frame)
            scrollbar.pack(side="right", fill="y")

            lb = tk.Listbox(
                lb_frame,
                bg=_LIST_BG,
                fg=_LIST_FG,
                selectbackground=_LIST_SELECT_BG,
                selectforeground="white",
                borderwidth=0,
                highlightthickness=1,
                highlightcolor="#555555",
                highlightbackground="#3a3a3a",
                activestyle="none",
                font=_LIST_FONT,
                yscrollcommand=scrollbar.set,
            )
            lb.pack(side="left", fill="both", expand=True)
            scrollbar.config(command=lb.yview)
            lb.bind("<<ListboxSelect>>", lambda _e, _lb=lb: self._on_select(_lb))

            self._bundle_listboxes[b.id] = lb

        # Restore or pick first bundle
        if bundles:
            target_id = preserve_bundle if preserve_bundle else bundles[0].id
            target = next((b for b in bundles if b.id == target_id), bundles[0])
            target_label = target.name + ("" if target.enabled else " (disabled)")
            self._current_bundle_id = target.id
            try:
                self._tabview.set(target_label)
            except Exception:
                pass
            self._load_hotstrings()

    def _on_tab_change(self) -> None:
        """Called by CTkTabview when the user switches tabs (no args)."""
        if self._tabview is None:
            return
        name = self._tabview.get()
        bundle_id = self._bundle_name_to_id.get(name)
        if bundle_id is not None and bundle_id != self._current_bundle_id:
            self._current_bundle_id = bundle_id
            self._current_hs_id = None
            self._clear_editor()
            self._load_hotstrings()

    # ── Hotstring list ──────────────────────────────────────────────

    def _load_hotstrings(self) -> None:
        if self._current_bundle_id is None:
            return
        self._hotstrings_cache = self.db.get_hotstrings(bundle_id=self._current_bundle_id)
        self._filter_list()

    def _filter_list(self) -> None:
        lb = self._bundle_listboxes.get(self._current_bundle_id)
        if lb is None:
            return
        query = (self._search_var.get().lower() if self._search_var else "")
        lb.delete(0, tk.END)
        for hs in self._hotstrings_cache:
            if query and query not in hs.name.lower() and query not in hs.replacement.lower():
                continue
            lb.insert(tk.END, hs.name)

    def _on_select(self, lb: tk.Listbox) -> None:
        sel = lb.curselection()
        if not sel:
            return
        name = lb.get(sel[0])
        for hs in self._hotstrings_cache:
            if hs.name == name:
                self._show_hotstring(hs)
                break

    def _show_hotstring(self, hs: "Hotstring") -> None:
        from kodex_py.storage.models import TriggerType

        self._current_hs_id = hs.id
        self._name_var.set(hs.name)
        self._script_var.set(hs.is_script)

        self._replacement_text.delete("1.0", tk.END)
        self._replacement_text.insert("1.0", hs.replacement)

        self._trig_space_var.set(TriggerType.SPACE in hs.triggers)
        self._trig_tab_var.set(TriggerType.TAB in hs.triggers)
        self._trig_enter_var.set(TriggerType.ENTER in hs.triggers)
        self._trig_instant_var.set(TriggerType.INSTANT in hs.triggers)

    # ── Trigger logic ───────────────────────────────────────────────

    def _on_instant_toggle(self) -> None:
        if self._trig_instant_var.get():
            self._trig_space_var.set(False)
            self._trig_tab_var.set(False)
            self._trig_enter_var.set(False)

    # ── CRUD ────────────────────────────────────────────────────────

    def _new_hotstring(self) -> None:
        from kodex_py.gui.editor import NewHotstringDialog

        bundles = self.db.get_bundles()
        current_bundle = next(
            (b.name for b in bundles if b.id == self._current_bundle_id), "Default"
        )
        dialog = NewHotstringDialog(
            self.db, default_bundle=current_bundle, parent=self._window
        )
        dialog.show()
        self._load_hotstrings()
        if self._on_reload:
            self._on_reload()

    def _save_hotstring(self) -> None:
        from kodex_py.storage.models import Hotstring, TriggerType

        name = self._name_var.get().strip()
        if not name:
            messagebox.showwarning("Kodex", "Hotstring name cannot be empty.", parent=self._window)
            return

        replacement = self._replacement_text.get("1.0", tk.END).rstrip("\n")
        triggers: set = set()
        if self._trig_space_var.get():
            triggers.add(TriggerType.SPACE)
        if self._trig_tab_var.get():
            triggers.add(TriggerType.TAB)
        if self._trig_enter_var.get():
            triggers.add(TriggerType.ENTER)
        if self._trig_instant_var.get():
            triggers.add(TriggerType.INSTANT)

        if not triggers:
            messagebox.showwarning(
                "Kodex", "Select at least one trigger type.", parent=self._window
            )
            return

        hs = Hotstring(
            id=self._current_hs_id,
            name=name,
            replacement=replacement,
            is_script=self._script_var.get(),
            bundle_id=self._current_bundle_id,
            triggers=triggers,
        )
        try:
            self.db.save_hotstring(hs)
            self._load_hotstrings()
            if self._on_reload:
                self._on_reload()
        except Exception as e:
            messagebox.showerror("Kodex", f"Error saving: {e}", parent=self._window)

    def _delete_hotstring(self) -> None:
        if self._current_hs_id is None:
            messagebox.showwarning("Kodex", "No hotstring selected.", parent=self._window)
            return
        name = self._name_var.get()
        if messagebox.askyesno(
            "Kodex", f"Delete hotstring '{name}'?", parent=self._window
        ):
            self.db.delete_hotstring(self._current_hs_id)
            self._current_hs_id = None
            self._clear_editor()
            self._load_hotstrings()
            if self._on_reload:
                self._on_reload()

    def _clear_editor(self) -> None:
        if self._name_var:
            self._name_var.set("")
        if self._script_var:
            self._script_var.set(False)
        if self._replacement_text:
            self._replacement_text.delete("1.0", tk.END)
        for var in (
            self._trig_space_var,
            self._trig_tab_var,
            self._trig_enter_var,
            self._trig_instant_var,
        ):
            if var:
                var.set(False)

    # ── Bundle management ───────────────────────────────────────────

    def _new_bundle(self) -> None:
        name = simpledialog.askstring("New Bundle", "Bundle name:", parent=self._window)
        if name and name.strip():
            self.db.create_bundle(name.strip())
            self._rebuild_tabs()

    def _rename_bundle(self) -> None:
        if self._current_bundle_id is None:
            return
        bundles = self.db.get_bundles()
        current = next((b for b in bundles if b.id == self._current_bundle_id), None)
        if current is None:
            return
        if current.name == "Default":
            messagebox.showwarning(
                "Kodex", "Cannot rename the Default bundle.", parent=self._window
            )
            return
        new_name = simpledialog.askstring(
            "Rename Bundle",
            f"New name for '{current.name}':",
            initialvalue=current.name,
            parent=self._window,
        )
        if new_name and new_name.strip():
            self.db._conn.execute(
                "UPDATE bundles SET name = ? WHERE id = ?",
                (new_name.strip(), self._current_bundle_id),
            )
            self.db._conn.commit()
            self._rebuild_tabs(preserve_bundle=self._current_bundle_id)

    def _delete_bundle(self) -> None:
        if self._current_bundle_id is None:
            return
        bundles = self.db.get_bundles()
        current = next((b for b in bundles if b.id == self._current_bundle_id), None)
        if current is None:
            return
        if current.name == "Default":
            messagebox.showwarning(
                "Kodex", "Cannot delete the Default bundle.", parent=self._window
            )
            return
        if messagebox.askyesno(
            "Kodex",
            f"Delete bundle '{current.name}' and all its hotstrings?",
            parent=self._window,
        ):
            self.db.delete_bundle(self._current_bundle_id)
            self._current_bundle_id = None
            self._current_hs_id = None
            self._rebuild_tabs()
            if self._on_reload:
                self._on_reload()

    def _export_bundle(self) -> None:
        from kodex_py.storage.bundle_io import export_bundle

        if self._current_bundle_id is None:
            return
        bundles = self.db.get_bundles()
        current = next((b for b in bundles if b.id == self._current_bundle_id), None)
        if current is None:
            return
        path = filedialog.asksaveasfilename(
            parent=self._window,
            title="Export Bundle",
            defaultextension=".kodex",
            initialfile=f"{current.name}.kodex",
            filetypes=[("Kodex bundle", "*.kodex"), ("All files", "*.*")],
        )
        if path:
            count = export_bundle(self.db, current.name, path)
            messagebox.showinfo(
                "Kodex", f"Exported {count} hotstrings to:\n{path}", parent=self._window
            )

    def _import_bundle(self) -> None:
        from kodex_py.storage.bundle_io import import_bundle

        path = filedialog.askopenfilename(
            parent=self._window,
            title="Import Bundle",
            filetypes=[("Kodex bundle", "*.kodex"), ("All files", "*.*")],
        )
        if path:
            count = import_bundle(self.db, path)
            messagebox.showinfo(
                "Kodex", f"Imported {count} hotstrings.", parent=self._window
            )
            self._rebuild_tabs()
            if self._on_reload:
                self._on_reload()

    # ── Tools ───────────────────────────────────────────────────────

    def _open_preferences(self) -> None:
        from kodex_py.gui.preferences import PreferencesWindow

        PreferencesWindow(self.db, parent=self._window).show()

    def _generate_cheatsheet(self) -> None:
        from kodex_py.gui.cheatsheet import generate_cheatsheet

        path = filedialog.asksaveasfilename(
            parent=self._window,
            title="Save Cheatsheet",
            defaultextension=".html",
            initialfile="kodex-cheatsheet.html",
            filetypes=[("HTML files", "*.html"), ("All files", "*.*")],
        )
        if path:
            generate_cheatsheet(self.db, path)
            messagebox.showinfo(
                "Kodex", f"Cheatsheet saved to:\n{path}", parent=self._window
            )
