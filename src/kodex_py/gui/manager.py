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

import dearpygui.dearpygui as dpg

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
        self._window_tag = "management_window"
        self._current_bundle_id: int | None = None
        self._current_hs_id: int | None = None
        self._hotstrings_cache: list["Hotstring"] = []

        # Widget tags (will be set in show())
        self._tags: dict[str, str] = {}

    def show(self) -> None:
        """Create and show the management window."""
        # If window exists, focus it
        if dpg.does_item_exist(self._window_tag):
            dpg.focus_item(self._window_tag)
            return

        # Generate unique tags
        wid = id(self)
        self._tags = {
            "search": f"mgr_search_{wid}",
            "tab_bar": f"mgr_tabs_{wid}",
            "list": f"mgr_list_{wid}",
            "name": f"mgr_name_{wid}",
            "script": f"mgr_script_{wid}",
            "replacement": f"mgr_repl_{wid}",
            "trig_space": f"mgr_trig_space_{wid}",
            "trig_tab": f"mgr_trig_tab_{wid}",
            "trig_enter": f"mgr_trig_enter_{wid}",
            "trig_instant": f"mgr_trig_instant_{wid}",
        }

        def _on_close():
            if dpg.does_item_exist(self._window_tag):
                dpg.delete_item(self._window_tag)

        with dpg.window(
            label="Kodex — Manage Hotstrings",
            tag=self._window_tag,
            width=920,
            height=620,
            pos=[50, 50],
            on_close=_on_close,
        ):
            # ── Menu Bar ──
            with dpg.menu_bar():
                with dpg.menu(label="Tools"):
                    dpg.add_menu_item(label="Preferences...", callback=self._open_preferences)
                    dpg.add_menu_item(
                        label="Printable Cheatsheet", callback=self._generate_cheatsheet
                    )

                with dpg.menu(label="Bundles"):
                    dpg.add_menu_item(label="New Bundle...", callback=self._new_bundle)
                    dpg.add_menu_item(label="Rename Bundle...", callback=self._rename_bundle)
                    dpg.add_menu_item(label="Delete Bundle...", callback=self._delete_bundle)
                    dpg.add_separator()
                    dpg.add_menu_item(label="Export Bundle...", callback=self._export_bundle)
                    dpg.add_menu_item(label="Import Bundle...", callback=self._import_bundle)

            # ── Search Bar ──
            with dpg.group(horizontal=True):
                dpg.add_text("Search:")
                dpg.add_input_text(
                    tag=self._tags["search"],
                    width=300,
                    callback=lambda s, a: self._filter_list(),
                )

            dpg.add_spacer(height=4)

            # ── Bundle Tabs ──
            with dpg.tab_bar(tag=self._tags["tab_bar"], callback=self._on_tab_changed):
                pass  # Tabs added dynamically

            dpg.add_spacer(height=4)

            # ── Main Content (List + Editor) ──
            with dpg.group(horizontal=True):
                # Left: Hotstring list
                with dpg.child_window(width=280, height=-40):
                    dpg.add_listbox(
                        tag=self._tags["list"],
                        items=[],
                        num_items=20,
                        width=-1,
                        callback=self._on_select,
                    )

                dpg.add_spacer(width=8)

                # Right: Editor
                with dpg.child_window(width=-1, height=-40):
                    # Name row
                    with dpg.group(horizontal=True):
                        dpg.add_text("Name:")
                        dpg.add_input_text(tag=self._tags["name"], width=250)
                        dpg.add_spacer(width=20)
                        dpg.add_checkbox(label="Script mode", tag=self._tags["script"])

                    dpg.add_spacer(height=8)

                    # Triggers
                    with dpg.collapsing_header(label="Triggers", default_open=True):
                        with dpg.group(horizontal=True):
                            dpg.add_checkbox(
                                label="Space",
                                tag=self._tags["trig_space"],
                            )
                            dpg.add_checkbox(
                                label="Tab",
                                tag=self._tags["trig_tab"],
                            )
                            dpg.add_checkbox(
                                label="Enter",
                                tag=self._tags["trig_enter"],
                            )
                            dpg.add_checkbox(
                                label="Instant",
                                tag=self._tags["trig_instant"],
                                callback=self._on_instant_toggle,
                            )

                    dpg.add_spacer(height=8)

                    # Replacement text
                    dpg.add_text("Replacement:")
                    dpg.add_input_text(
                        tag=self._tags["replacement"],
                        multiline=True,
                        width=-1,
                        height=280,
                    )

            # ── Bottom Buttons ──
            with dpg.group(horizontal=True):
                dpg.add_button(label="+ New", callback=self._new_hotstring, width=80)
                dpg.add_spacer(width=8)
                dpg.add_button(label="Save", callback=self._save_hotstring, width=80)
                dpg.add_spacer(width=8)
                dpg.add_button(label="Delete", callback=self._delete_hotstring, width=80)

        # Populate tabs
        self._rebuild_tabs()

    def _on_close(self) -> None:
        if dpg.does_item_exist(self._window_tag):
            dpg.delete_item(self._window_tag)

    # ── Tab management ──

    def _rebuild_tabs(self) -> None:
        """Rebuild bundle tabs from database."""
        tab_bar = self._tags["tab_bar"]
        if not dpg.does_item_exist(tab_bar):
            return

        # Clear existing tabs
        children = dpg.get_item_children(tab_bar, 1)
        if children:
            for child in children:
                dpg.delete_item(child)

        # Add tabs for each bundle
        bundles = self.db.get_bundles()
        for b in bundles:
            label = f"{b.name}" + ("" if b.enabled else " (disabled)")
            # Store bundle_id as user_data
            dpg.add_tab(label=label, parent=tab_bar, user_data=b.id)

        if bundles:
            self._current_bundle_id = bundles[0].id
            self._load_hotstrings()

    def _on_tab_changed(self, sender, app_data) -> None:
        """Handle tab selection change."""
        if app_data is None:
            return
        # app_data is the selected tab's tag
        bundle_id = dpg.get_item_user_data(app_data)
        if bundle_id is not None:
            self._current_bundle_id = bundle_id
            self._load_hotstrings()

    # ── Hotstring list ──

    def _load_hotstrings(self) -> None:
        """Load hotstrings for current bundle."""
        if self._current_bundle_id is None:
            return
        self._hotstrings_cache = self.db.get_hotstrings(bundle_id=self._current_bundle_id)
        self._filter_list()

    def _filter_list(self) -> None:
        """Filter and update the hotstring list."""
        if not dpg.does_item_exist(self._tags["list"]):
            return

        query = dpg.get_value(self._tags["search"]).lower() if dpg.does_item_exist(self._tags["search"]) else ""
        items = []
        for hs in self._hotstrings_cache:
            if query and query not in hs.name.lower() and query not in hs.replacement.lower():
                continue
            items.append(hs.name)

        dpg.configure_item(self._tags["list"], items=items)

    def _on_select(self, sender, app_data) -> None:
        """Handle hotstring selection."""
        name = app_data
        if not name:
            return
        for hs in self._hotstrings_cache:
            if hs.name == name:
                self._show_hotstring(hs)
                break

    def _show_hotstring(self, hs: "Hotstring") -> None:
        """Display hotstring in the editor."""
        from kodex_py.storage.models import TriggerType

        self._current_hs_id = hs.id
        dpg.set_value(self._tags["name"], hs.name)
        dpg.set_value(self._tags["script"], hs.is_script)
        dpg.set_value(self._tags["replacement"], hs.replacement)

        dpg.set_value(self._tags["trig_space"], TriggerType.SPACE in hs.triggers)
        dpg.set_value(self._tags["trig_tab"], TriggerType.TAB in hs.triggers)
        dpg.set_value(self._tags["trig_enter"], TriggerType.ENTER in hs.triggers)
        dpg.set_value(self._tags["trig_instant"], TriggerType.INSTANT in hs.triggers)

    # ── Trigger logic ──

    def _on_instant_toggle(self, sender, app_data) -> None:
        """When Instant is checked, uncheck other triggers."""
        if app_data:  # instant checked
            dpg.set_value(self._tags["trig_space"], False)
            dpg.set_value(self._tags["trig_tab"], False)
            dpg.set_value(self._tags["trig_enter"], False)

    # ── CRUD ──

    def _new_hotstring(self) -> None:
        """Open new hotstring dialog."""
        from kodex_py.gui.editor import NewHotstringDialog

        bundles = self.db.get_bundles()
        current_bundle = next(
            (b.name for b in bundles if b.id == self._current_bundle_id), "Default"
        )
        dialog = NewHotstringDialog(self.db, default_bundle=current_bundle)
        dialog.show()
        self._load_hotstrings()
        if self._on_reload:
            self._on_reload()

    def _save_hotstring(self) -> None:
        """Save current hotstring."""
        from kodex_py.storage.models import Hotstring, TriggerType

        name = dpg.get_value(self._tags["name"]).strip()
        if not name:
            self._show_warning("Hotstring name cannot be empty.")
            return

        replacement = dpg.get_value(self._tags["replacement"]).rstrip("\n")
        triggers = set()

        if dpg.get_value(self._tags["trig_space"]):
            triggers.add(TriggerType.SPACE)
        if dpg.get_value(self._tags["trig_tab"]):
            triggers.add(TriggerType.TAB)
        if dpg.get_value(self._tags["trig_enter"]):
            triggers.add(TriggerType.ENTER)
        if dpg.get_value(self._tags["trig_instant"]):
            triggers.add(TriggerType.INSTANT)

        if not triggers:
            self._show_warning("Select at least one trigger type.")
            return

        hs = Hotstring(
            id=self._current_hs_id,
            name=name,
            replacement=replacement,
            is_script=dpg.get_value(self._tags["script"]),
            bundle_id=self._current_bundle_id,
            triggers=triggers,
        )
        self.db.save_hotstring(hs)
        self._load_hotstrings()
        if self._on_reload:
            self._on_reload()

    def _delete_hotstring(self) -> None:
        """Delete current hotstring with confirmation."""
        if self._current_hs_id is None:
            return

        name = dpg.get_value(self._tags["name"])
        self._show_confirm(
            f"Delete hotstring '{name}'?",
            self._do_delete_hotstring,
        )

    def _do_delete_hotstring(self) -> None:
        """Actually delete the hotstring."""
        self.db.delete_hotstring(self._current_hs_id)
        self._current_hs_id = None
        self._load_hotstrings()
        self._clear_editor()
        if self._on_reload:
            self._on_reload()

    def _clear_editor(self) -> None:
        """Clear the editor fields."""
        dpg.set_value(self._tags["name"], "")
        dpg.set_value(self._tags["script"], False)
        dpg.set_value(self._tags["replacement"], "")
        dpg.set_value(self._tags["trig_space"], False)
        dpg.set_value(self._tags["trig_tab"], False)
        dpg.set_value(self._tags["trig_enter"], False)
        dpg.set_value(self._tags["trig_instant"], False)

    # ── Bundle management ──

    def _new_bundle(self) -> None:
        """Show new bundle dialog."""
        self._show_input("Bundle name:", self._do_create_bundle)

    def _do_create_bundle(self, name: str) -> None:
        if name and name.strip():
            self.db.create_bundle(name.strip())
            self._rebuild_tabs()

    def _rename_bundle(self) -> None:
        """Show rename bundle dialog."""
        if self._current_bundle_id is None:
            return

        bundles = self.db.get_bundles()
        current = next((b for b in bundles if b.id == self._current_bundle_id), None)
        if current is None:
            return
        if current.name == "Default":
            self._show_warning("Cannot rename the Default bundle.")
            return

        self._show_input(
            f"New name for '{current.name}':",
            self._do_rename_bundle,
            default=current.name,
        )

    def _do_rename_bundle(self, new_name: str) -> None:
        if new_name and new_name.strip():
            self.db._conn.execute(
                "UPDATE bundles SET name = ? WHERE id = ?",
                (new_name.strip(), self._current_bundle_id),
            )
            self.db._conn.commit()
            self._rebuild_tabs()

    def _delete_bundle(self) -> None:
        """Show delete bundle confirmation."""
        if self._current_bundle_id is None:
            return

        bundles = self.db.get_bundles()
        current = next((b for b in bundles if b.id == self._current_bundle_id), None)
        if current is None:
            return
        if current.name == "Default":
            self._show_warning("Cannot delete the Default bundle.")
            return

        self._show_confirm(
            f"Delete bundle '{current.name}' and all its hotstrings?",
            self._do_delete_bundle,
        )

    def _do_delete_bundle(self) -> None:
        self.db.delete_bundle(self._current_bundle_id)
        self._rebuild_tabs()
        if self._on_reload:
            self._on_reload()

    def _export_bundle(self) -> None:
        """Export current bundle to file."""
        from kodex_py.storage.bundle_io import export_bundle

        if self._current_bundle_id is None:
            return

        bundles = self.db.get_bundles()
        current = next((b for b in bundles if b.id == self._current_bundle_id), None)
        if current is None:
            return

        def _save_callback(sender, app_data):
            if app_data and "file_path_name" in app_data:
                path = app_data["file_path_name"]
                if path:
                    count = export_bundle(self.db, current.name, path)
                    self._show_warning(f"Exported {count} hotstrings to {path}")

        dpg.add_file_dialog(
            label="Export Bundle",
            callback=_save_callback,
            directory_selector=False,
            default_filename=f"{current.name}.kodex",
            modal=True,
            width=500,
            height=400,
        )

    def _import_bundle(self) -> None:
        """Import bundle from file."""
        from kodex_py.storage.bundle_io import import_bundle

        def _open_callback(sender, app_data):
            if app_data and "file_path_name" in app_data:
                path = app_data["file_path_name"]
                if path:
                    count = import_bundle(self.db, path)
                    self._show_warning(f"Imported {count} hotstrings")
                    self._rebuild_tabs()
                    if self._on_reload:
                        self._on_reload()

        dpg.add_file_dialog(
            label="Import Bundle",
            callback=_open_callback,
            directory_selector=False,
            modal=True,
            width=500,
            height=400,
        )

    # ── Tools ──

    def _open_preferences(self) -> None:
        """Open preferences window."""
        from kodex_py.gui.preferences import PreferencesWindow

        prefs = PreferencesWindow(self.db)
        prefs.show()

    def _generate_cheatsheet(self) -> None:
        """Generate cheatsheet to file."""
        from kodex_py.gui.cheatsheet import generate_cheatsheet

        def _save_callback(sender, app_data):
            if app_data and "file_path_name" in app_data:
                path = app_data["file_path_name"]
                if path:
                    generate_cheatsheet(self.db, path)
                    self._show_warning(f"Cheatsheet saved to {path}")

        dpg.add_file_dialog(
            label="Save Cheatsheet",
            callback=_save_callback,
            directory_selector=False,
            default_filename="kodex-cheatsheet.html",
            modal=True,
            width=500,
            height=400,
        )

    # ── Dialog helpers ──

    def _show_warning(self, message: str) -> None:
        """Show a warning/info popup."""
        warn_tag = f"mgr_warn_{id(self)}_{hash(message)}"

        def _close():
            if dpg.does_item_exist(warn_tag):
                dpg.delete_item(warn_tag)

        with dpg.window(
            label="Kodex",
            tag=warn_tag,
            modal=True,
            no_close=True,
            width=350,
            height=100,
            pos=[300, 200],
        ):
            dpg.add_text(message)
            dpg.add_spacer(height=12)
            dpg.add_button(label="OK", callback=_close, width=60)

    def _show_confirm(self, message: str, on_yes: Callable) -> None:
        """Show a yes/no confirmation dialog."""
        confirm_tag = f"mgr_confirm_{id(self)}"

        def _on_yes():
            if dpg.does_item_exist(confirm_tag):
                dpg.delete_item(confirm_tag)
            on_yes()

        def _on_no():
            if dpg.does_item_exist(confirm_tag):
                dpg.delete_item(confirm_tag)

        with dpg.window(
            label="Kodex",
            tag=confirm_tag,
            modal=True,
            no_close=True,
            width=350,
            height=100,
            pos=[300, 200],
        ):
            dpg.add_text(message)
            dpg.add_spacer(height=12)
            with dpg.group(horizontal=True):
                dpg.add_button(label="No", callback=_on_no, width=60)
                dpg.add_spacer(width=8)
                dpg.add_button(label="Yes", callback=_on_yes, width=60)

    def _show_input(
        self, prompt: str, on_submit: Callable[[str], None], default: str = ""
    ) -> None:
        """Show an input dialog."""
        input_tag = f"mgr_input_{id(self)}"
        text_tag = f"mgr_input_text_{id(self)}"

        def _on_ok():
            value = dpg.get_value(text_tag)
            if dpg.does_item_exist(input_tag):
                dpg.delete_item(input_tag)
            on_submit(value)

        def _on_cancel():
            if dpg.does_item_exist(input_tag):
                dpg.delete_item(input_tag)

        with dpg.window(
            label="Kodex",
            tag=input_tag,
            modal=True,
            no_close=True,
            width=350,
            height=120,
            pos=[300, 200],
        ):
            dpg.add_text(prompt)
            dpg.add_input_text(tag=text_tag, default_value=default, width=-1)
            dpg.add_spacer(height=12)
            with dpg.group(horizontal=True):
                dpg.add_button(label="Cancel", callback=_on_cancel, width=60)
                dpg.add_spacer(width=8)
                dpg.add_button(label="OK", callback=_on_ok, width=60)

        dpg.focus_item(text_tag)
