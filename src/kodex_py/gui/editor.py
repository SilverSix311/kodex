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

import dearpygui.dearpygui as dpg

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
        self._dialog_tag = "new_hotstring_dialog"
        self._closed = False

    def show(self) -> None:
        """Create and show the dialog (blocks until dismissed)."""
        from kodex_py.storage.models import Hotstring, TriggerType

        # Generate unique tags for this dialog instance
        dialog_id = id(self)
        name_tag = f"nh_name_{dialog_id}"
        bundle_tag = f"nh_bundle_{dialog_id}"
        text_tag = f"nh_text_{dialog_id}"
        script_tag = f"nh_script_{dialog_id}"
        trigger_space_tag = f"nh_trig_space_{dialog_id}"
        trigger_tab_tag = f"nh_trig_tab_{dialog_id}"
        trigger_enter_tag = f"nh_trig_enter_{dialog_id}"
        trigger_instant_tag = f"nh_trig_instant_{dialog_id}"

        bundles = self.db.get_bundles()
        bundle_names = [b.name for b in bundles]

        # Find default bundle index
        default_idx = 0
        for i, name in enumerate(bundle_names):
            if name == self._default_bundle:
                default_idx = i
                break

        def _on_instant_toggle(sender, app_data):
            """When Instant is checked, uncheck other triggers."""
            if app_data:  # instant checked
                dpg.set_value(trigger_space_tag, False)
                dpg.set_value(trigger_tab_tag, False)
                dpg.set_value(trigger_enter_tag, False)

        def _on_ok():
            name = dpg.get_value(name_tag).strip()
            if not name:
                # Show warning
                self._show_warning("Name cannot be empty.")
                return

            replacement = dpg.get_value(text_tag).rstrip("\n")
            triggers = set()

            if dpg.get_value(trigger_space_tag):
                triggers.add(TriggerType.SPACE)
            if dpg.get_value(trigger_tab_tag):
                triggers.add(TriggerType.TAB)
            if dpg.get_value(trigger_enter_tag):
                triggers.add(TriggerType.ENTER)
            if dpg.get_value(trigger_instant_tag):
                triggers.add(TriggerType.INSTANT)

            if not triggers:
                self._show_warning("Select at least one trigger.")
                return

            # Find bundle
            bname = dpg.get_value(bundle_tag)
            bundle = self.db.get_bundle_by_name(bname)
            if bundle is None:
                bundle = self.db.create_bundle(bname)

            hs = Hotstring(
                name=name,
                replacement=replacement,
                is_script=dpg.get_value(script_tag),
                bundle_id=bundle.id,
                triggers=triggers,
            )
            try:
                self.db.save_hotstring(hs)
                self._close_dialog()
            except Exception as e:
                self._show_warning(f"Error: {e}")

        def _on_cancel():
            self._close_dialog()

        # Build the dialog
        with dpg.window(
            label="Kodex — New Hotstring",
            tag=self._dialog_tag,
            modal=True,
            no_close=True,
            width=520,
            height=480,
            pos=[200, 100],
        ):
            # Name
            dpg.add_text("Hotstring name:")
            dpg.add_input_text(tag=name_tag, width=-1)

            dpg.add_spacer(height=8)

            # Bundle
            dpg.add_text("Bundle:")
            dpg.add_combo(
                tag=bundle_tag,
                items=bundle_names,
                default_value=bundle_names[default_idx] if bundle_names else "Default",
                width=-1,
            )

            dpg.add_spacer(height=8)

            # Triggers
            with dpg.collapsing_header(label="Triggers", default_open=True):
                with dpg.group(horizontal=True):
                    dpg.add_checkbox(label="Space", tag=trigger_space_tag, default_value=True)
                    dpg.add_checkbox(label="Tab", tag=trigger_tab_tag)
                    dpg.add_checkbox(label="Enter", tag=trigger_enter_tag)
                    dpg.add_checkbox(
                        label="Instant",
                        tag=trigger_instant_tag,
                        callback=_on_instant_toggle,
                    )

            dpg.add_spacer(height=8)

            # Script mode
            dpg.add_checkbox(label="Script mode (::scr::)", tag=script_tag)

            dpg.add_spacer(height=8)

            # Replacement text
            dpg.add_text("Replacement text:")
            dpg.add_input_text(
                tag=text_tag,
                multiline=True,
                width=-1,
                height=180,
            )

            dpg.add_spacer(height=12)

            # Buttons
            with dpg.group(horizontal=True):
                dpg.add_button(label="Cancel", callback=_on_cancel, width=80)
                dpg.add_spacer(width=8)
                dpg.add_button(label="OK", callback=_on_ok, width=80)

        # Focus name input
        dpg.focus_item(name_tag)

        # Wait for dialog to close (poll-based for modal behavior)
        while dpg.does_item_exist(self._dialog_tag) and dpg.is_dearpygui_running():
            dpg.render_dearpygui_frame()

    def _close_dialog(self) -> None:
        """Close and clean up the dialog."""
        self._closed = True
        if dpg.does_item_exist(self._dialog_tag):
            dpg.delete_item(self._dialog_tag)

    def _show_warning(self, message: str) -> None:
        """Show a warning popup."""
        warn_tag = f"nh_warning_{id(self)}"

        def _close_warning():
            if dpg.does_item_exist(warn_tag):
                dpg.delete_item(warn_tag)

        with dpg.window(
            label="Kodex",
            tag=warn_tag,
            modal=True,
            no_close=True,
            width=300,
            height=100,
            pos=[300, 200],
        ):
            dpg.add_text(message)
            dpg.add_spacer(height=12)
            dpg.add_button(label="OK", callback=_close_warning, width=60)
