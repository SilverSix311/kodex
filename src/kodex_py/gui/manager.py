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
        tools_menu.add_separator()
        tools_menu.add_command(label="View Variables…", command=self._view_variables)
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

    def _view_variables(self) -> None:
        ViewVariablesDialog(parent=self._window).show()


# ── View Variables Dialog ────────────────────────────────────────────────────

class ViewVariablesDialog:
    """Read-only dialog that shows all available Kodex variables.

    Sections:
      1. Built-in variables  (%c, %t, %tl, %ds, %dl, %p, %|)
      2. Ticket Context      (freshdesk_context.json)
      3. Global Variables    (global_variables.json)
    """

    _BUILTIN_VARS: list[tuple[str, str]] = [
        ("%c",  "Clipboard contents"),
        ("%t",  "Short time (e.g., 2:30 PM)"),
        ("%tl", "Long time (e.g., 14:30:45 PM)"),
        ("%ds", "Short date (e.g., 1/29/2026)"),
        ("%dl", "Long date (e.g., January 29, 2026)"),
        ("%p",  "Prompt — asks user for input"),
        ("%|",  "Cursor position after expansion"),
    ]

    # Colours reused from parent module
    _ROW_EVEN   = ("gray92", "gray18")
    _ROW_ODD    = ("gray88", "gray22")
    _VAR_COLOR  = ("#1a7ccf", "#4da6ff")
    _DIM_COLOR  = ("gray50", "gray55")

    def __init__(self, parent=None) -> None:
        self._parent = parent
        self._window: ctk.CTkToplevel | None = None
        self._scroll: ctk.CTkScrollableFrame | None = None
        self._status_label: ctk.CTkLabel | None = None
        self._row_index: int = 0          # used to alternate row colours

    # ── Public ───────────────────────────────────────────────────────

    def show(self) -> None:
        if self._window is not None and self._window.winfo_exists():
            self._window.deiconify()
            self._window.lift()
            self._window.focus_force()
            return
        self._build()

    # ── Construction ─────────────────────────────────────────────────

    def _build(self) -> None:
        win = ctk.CTkToplevel(self._parent)
        self._window = win
        win.title("Kodex — View Variables")
        win.geometry("740x580")
        win.minsize(520, 380)

        # ── Top button bar ──
        btn_bar = ctk.CTkFrame(win, fg_color="transparent")
        btn_bar.pack(fill="x", padx=12, pady=(10, 4))

        ctk.CTkButton(
            btn_bar, text="⟳  Refresh", width=100, command=self._refresh
        ).pack(side="left")

        self._status_label = ctk.CTkLabel(
            btn_bar, text="", text_color=self._DIM_COLOR
        )
        self._status_label.pack(side="left", padx=(12, 0))

        hint = ctk.CTkLabel(
            btn_bar,
            text="Right-click or click 📋 to copy a variable name",
            text_color=self._DIM_COLOR,
            font=ctk.CTkFont(size=11),
        )
        hint.pack(side="right")

        # ── Divider ──
        ctk.CTkFrame(win, height=1, fg_color=("gray75", "gray30")).pack(
            fill="x", padx=12, pady=(0, 4)
        )

        # ── Scrollable body ──
        self._scroll = ctk.CTkScrollableFrame(win)
        self._scroll.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        self._populate()

    # ── Content builder ──────────────────────────────────────────────

    def _populate(self) -> None:
        """Clear and rebuild all variable rows."""
        if self._scroll is None:
            return

        for child in self._scroll.winfo_children():
            child.destroy()

        self._row_index = 0

        # 1 ─ Built-in variables
        self._add_section("Built-in Variables")
        for var_name, description in self._BUILTIN_VARS:
            self._add_row(var_name, description, copy_text=var_name)

        # 2 ─ Ticket Context (all sources)
        self._add_spacer()
        self._add_section("Ticket Context  (per-source context files)")

        all_contexts: dict = {}
        try:
            from kodex_py.utils.global_variables import get_global_variables
            all_contexts = get_global_variables().get_all_contexts()
        except Exception as exc:
            log.warning("ViewVariablesDialog: could not load contexts: %s", exc)

        if all_contexts:
            for source, ctx in sorted(all_contexts.items()):
                if not ctx:
                    continue
                # Section header for each source
                ctk.CTkLabel(
                    self._scroll,
                    text=f"  {source.upper()}  ({source}_context.json)",
                    font=ctk.CTkFont(size=11),
                    text_color=("gray50", "gray60"),
                    anchor="w",
                ).pack(fill="x", padx=10, pady=(6, 2))

                self._row_index = 0  # reset alternation for this source
                for key, value in sorted(ctx.items()):
                    if key.startswith("_"):
                        continue  # skip metadata
                    self._add_row(
                        f"%{key}%",
                        self._fmt(value),
                        copy_text=f"%{key}%",
                    )
                    # Also show prefixed version
                    self._add_row(
                        f"%{source}_{key}%",
                        self._fmt(value),
                        copy_text=f"%{source}_{key}%",
                    )
        else:
            self._add_empty("No ticket context loaded  (no context files found)")

        # 3 ─ Global Variables
        self._add_spacer()
        self._add_section("Global Variables  (global_variables.json)")

        gv_vars: dict = {}
        try:
            from kodex_py.utils.global_variables import get_global_variables
            gv_vars = get_global_variables().list_all()
        except Exception as exc:
            log.warning("ViewVariablesDialog: could not load global variables: %s", exc)

        if gv_vars:
            self._row_index = 0
            for name, info in sorted(gv_vars.items()):
                var_type = info.get("type", "string")
                raw_val  = info.get("value", "")
                display  = f"[{var_type}]  {self._fmt(raw_val)}"
                self._add_row(f"%{name}%", display, copy_text=f"%{name}%")
        else:
            self._add_empty("No global variables defined")

    # ── Row helpers ──────────────────────────────────────────────────

    def _add_section(self, title: str) -> None:
        ctk.CTkLabel(
            self._scroll,
            text=title,
            font=ctk.CTkFont(size=13, weight="bold"),
            anchor="w",
        ).pack(fill="x", padx=6, pady=(8, 2))
        ctk.CTkFrame(
            self._scroll, height=1, fg_color=("gray70", "gray38")
        ).pack(fill="x", padx=6, pady=(0, 2))

    def _add_row(self, var_name: str, value: str, copy_text: str) -> None:
        """One variable row: [name] [value …] [📋]"""
        bg = self._ROW_EVEN if self._row_index % 2 == 0 else self._ROW_ODD
        self._row_index += 1

        row = ctk.CTkFrame(self._scroll, fg_color=bg, corner_radius=4)
        row.pack(fill="x", padx=6, pady=2)
        row.columnconfigure(1, weight=1)

        # Variable name (monospace, coloured)
        name_lbl = ctk.CTkLabel(
            row,
            text=var_name,
            font=ctk.CTkFont(family="Courier New", size=12),
            text_color=self._VAR_COLOR,
            anchor="w",
            width=160,
        )
        name_lbl.grid(row=0, column=0, padx=(10, 6), pady=6, sticky="w")

        # Value (truncated if very long)
        truncated = value if len(value) <= 90 else value[:87] + "…"
        val_lbl = ctk.CTkLabel(
            row,
            text=truncated,
            font=ctk.CTkFont(size=12),
            anchor="w",
        )
        val_lbl.grid(row=0, column=1, padx=(0, 6), pady=6, sticky="ew")

        # Copy button
        copy_btn = ctk.CTkButton(
            row,
            text="📋",
            width=34,
            height=26,
            font=ctk.CTkFont(size=12),
            command=lambda t=copy_text: self._copy(t),
        )
        copy_btn.grid(row=0, column=2, padx=(0, 8), pady=4)

        # Right-click → context menu
        def _ctx_menu(event: tk.Event, t: str = copy_text) -> None:
            m = tk.Menu(
                self._scroll, tearoff=0,
                bg="#2b2b2b", fg="#dce4ee",
                activebackground="#1f6aa5", activeforeground="white",
            )
            m.add_command(label=f"Copy  {t}", command=lambda: self._copy(t))
            m.tk_popup(event.x_root, event.y_root)

        for w in (row, name_lbl, val_lbl):
            w.bind("<Button-3>", _ctx_menu)

    def _add_meta_row(self, label: str, value: str) -> None:
        """Small informational sub-row (e.g., active source)."""
        row = ctk.CTkFrame(self._scroll, fg_color="transparent")
        row.pack(fill="x", padx=6, pady=(0, 2))
        ctk.CTkLabel(
            row,
            text=f"  {label}:",
            font=ctk.CTkFont(size=11),
            text_color=self._DIM_COLOR,
            anchor="w",
            width=130,
        ).pack(side="left")
        ctk.CTkLabel(
            row,
            text=value,
            font=ctk.CTkFont(size=11),
            text_color=self._DIM_COLOR,
            anchor="w",
        ).pack(side="left", padx=(4, 0))

    def _add_empty(self, text: str) -> None:
        ctk.CTkLabel(
            self._scroll,
            text=f"  {text}",
            text_color=self._DIM_COLOR,
            font=ctk.CTkFont(size=12, slant="italic"),
            anchor="w",
        ).pack(fill="x", padx=6, pady=6)

    def _add_spacer(self) -> None:
        ctk.CTkFrame(self._scroll, height=8, fg_color="transparent").pack()

    # ── Actions ──────────────────────────────────────────────────────

    def _copy(self, text: str) -> None:
        if self._window and self._window.winfo_exists():
            self._window.clipboard_clear()
            self._window.clipboard_append(text)
            if self._status_label:
                self._status_label.configure(text=f"Copied: {text}")
                self._window.after(
                    2000, lambda: self._status_label.configure(text="")
                )

    def _refresh(self) -> None:
        try:
            from kodex_py.utils.global_variables import get_global_variables
            get_global_variables().load()
        except Exception as exc:
            log.warning("ViewVariablesDialog: refresh load failed: %s", exc)
        self._populate()
        if self._status_label:
            self._status_label.configure(text="Refreshed ✓")
            if self._window:
                self._window.after(
                    2000, lambda: self._status_label.configure(text="")
                )

    # ── Utility ──────────────────────────────────────────────────────

    @staticmethod
    def _fmt(value: object) -> str:
        """Convert any variable value to a display string."""
        import json as _json
        if value is None:
            return "(none)"
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, (dict, list)):
            return _json.dumps(value, ensure_ascii=False)
        return str(value)
