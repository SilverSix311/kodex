"""Preferences window — mirrors AHK preferences_GUI.ahk.

Three tabs:
- General: hotkeys, send mode, sound, startup
- Print: cheatsheet generation
- Stats: expansion statistics
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import dearpygui.dearpygui as dpg

if TYPE_CHECKING:
    from kodex_py.storage.database import Database

log = logging.getLogger(__name__)


class PreferencesWindow:
    """Preferences dialog with General / Print / Stats tabs."""

    def __init__(self, db: "Database", parent=None) -> None:
        self.db = db
        self._parent = parent
        self._dialog_tag = "preferences_dialog"
        self._closed = False

    def show(self) -> None:
        from kodex_py.config import load_config, save_config
        from kodex_py.storage.models import SendMode

        cfg = load_config(self.db)

        # Generate unique tags
        dialog_id = id(self)
        hk_create_tag = f"pref_hk_create_{dialog_id}"
        hk_manage_tag = f"pref_hk_manage_{dialog_id}"
        hk_disable_tag = f"pref_hk_disable_{dialog_id}"
        hk_tracker_tag = f"pref_hk_tracker_{dialog_id}"
        mode_tag = f"pref_mode_{dialog_id}"
        sound_tag = f"pref_sound_{dialog_id}"
        startup_tag = f"pref_startup_{dialog_id}"
        autocorrect_tag = f"pref_autocorrect_{dialog_id}"

        def _on_save():
            cfg.hotkey_create = dpg.get_value(hk_create_tag)
            cfg.hotkey_manage = dpg.get_value(hk_manage_tag)
            cfg.hotkey_disable = dpg.get_value(hk_disable_tag)
            cfg.hotkey_tracker = dpg.get_value(hk_tracker_tag)

            mode_val = dpg.get_value(mode_tag)
            cfg.send_mode = SendMode.CLIPBOARD if mode_val == "Clipboard" else SendMode.DIRECT

            cfg.play_sound = dpg.get_value(sound_tag)
            cfg.run_at_startup = dpg.get_value(startup_tag)
            cfg.autocorrect_enabled = dpg.get_value(autocorrect_tag)

            save_config(self.db, cfg)
            self._close_dialog()

        def _on_cancel():
            self._close_dialog()

        def _do_cheatsheet():
            from kodex_py.gui.cheatsheet import generate_cheatsheet

            # Use file dialog
            def _save_callback(sender, app_data):
                if app_data and "file_path_name" in app_data:
                    path = app_data["file_path_name"]
                    if path:
                        generate_cheatsheet(self.db, path)
                        self._show_info(f"Cheatsheet saved to {path}")

            dpg.add_file_dialog(
                label="Save Cheatsheet",
                callback=_save_callback,
                directory_selector=False,
                default_filename="kodex-cheatsheet.html",
                modal=True,
                width=500,
                height=400,
            )

        # Stats data
        expanded = self.db.get_stat("expanded")
        chars = self.db.get_stat("chars_saved")
        hours = chars / 24_000 if chars else 0
        total_hs = len(self.db.get_hotstrings())
        total_bundles = len(self.db.get_bundles())

        # Build dialog
        with dpg.window(
            label="Kodex — Preferences",
            tag=self._dialog_tag,
            modal=True,
            no_close=True,
            width=500,
            height=440,
            pos=[200, 100],
        ):
            with dpg.tab_bar():
                # ── General Tab ──
                with dpg.tab(label="General"):
                    dpg.add_spacer(height=8)

                    # Hotkeys section
                    with dpg.collapsing_header(label="Hotkeys", default_open=True):
                        with dpg.group():
                            with dpg.group(horizontal=True):
                                dpg.add_text("Create hotstring:", bullet=False)
                                dpg.add_spacer(width=20)
                                dpg.add_input_text(
                                    tag=hk_create_tag,
                                    default_value=cfg.hotkey_create,
                                    width=150,
                                )

                            with dpg.group(horizontal=True):
                                dpg.add_text("Manage hotstrings:")
                                dpg.add_spacer(width=8)
                                dpg.add_input_text(
                                    tag=hk_manage_tag,
                                    default_value=cfg.hotkey_manage,
                                    width=150,
                                )

                            with dpg.group(horizontal=True):
                                dpg.add_text("Disable toggle:")
                                dpg.add_spacer(width=30)
                                dpg.add_input_text(
                                    tag=hk_disable_tag,
                                    default_value=cfg.hotkey_disable,
                                    width=150,
                                )

                            with dpg.group(horizontal=True):
                                dpg.add_text("Ticket tracker:")
                                dpg.add_spacer(width=30)
                                dpg.add_input_text(
                                    tag=hk_tracker_tag,
                                    default_value=cfg.hotkey_tracker,
                                    width=150,
                                )

                    dpg.add_spacer(height=8)

                    # Send Mode section
                    with dpg.collapsing_header(label="Send Mode", default_open=True):
                        current_mode = "Clipboard" if cfg.send_mode == SendMode.CLIPBOARD else "Direct"
                        dpg.add_combo(
                            tag=mode_tag,
                            items=["Direct", "Clipboard"],
                            default_value=current_mode,
                            width=200,
                        )
                        dpg.add_text(
                            "Direct = keystroke injection\nClipboard = Ctrl+V paste",
                            color=(150, 150, 150),
                        )

                    dpg.add_spacer(height=8)

                    # Checkboxes
                    dpg.add_checkbox(
                        label="Play sound on expansion",
                        tag=sound_tag,
                        default_value=cfg.play_sound,
                    )
                    dpg.add_checkbox(
                        label="Run at Windows startup",
                        tag=startup_tag,
                        default_value=cfg.run_at_startup,
                    )
                    dpg.add_checkbox(
                        label="Enable autocorrect",
                        tag=autocorrect_tag,
                        default_value=cfg.autocorrect_enabled,
                    )

                # ── Print Tab ──
                with dpg.tab(label="Print"):
                    dpg.add_spacer(height=20)
                    dpg.add_text("Generate a printable HTML cheatsheet")
                    dpg.add_text("of all your hotstrings.")
                    dpg.add_spacer(height=20)
                    dpg.add_button(label="Generate Cheatsheet", callback=_do_cheatsheet)

                # ── Stats Tab ──
                with dpg.tab(label="Stats"):
                    dpg.add_spacer(height=12)

                    with dpg.table(header_row=False, borders_innerV=False, borders_outerH=False):
                        dpg.add_table_column(width_fixed=True, init_width_or_weight=150)
                        dpg.add_table_column()

                        with dpg.table_row():
                            dpg.add_text("Hotstrings:")
                            dpg.add_text(str(total_hs), color=(100, 200, 255))

                        with dpg.table_row():
                            dpg.add_text("Bundles:")
                            dpg.add_text(str(total_bundles), color=(100, 200, 255))

                        with dpg.table_row():
                            dpg.add_text("Expansions:")
                            dpg.add_text(f"{expanded:,}", color=(100, 200, 255))

                        with dpg.table_row():
                            dpg.add_text("Characters saved:")
                            dpg.add_text(f"{chars:,}", color=(100, 200, 255))

                        with dpg.table_row():
                            dpg.add_text("Hours saved:")
                            dpg.add_text(f"{hours:.1f}", color=(100, 200, 255))

            dpg.add_spacer(height=12)

            # Buttons
            with dpg.group(horizontal=True):
                dpg.add_button(label="Cancel", callback=_on_cancel, width=80)
                dpg.add_spacer(width=8)
                dpg.add_button(label="Save", callback=_on_save, width=80)

        # Wait for dialog to close
        while dpg.does_item_exist(self._dialog_tag) and dpg.is_dearpygui_running():
            dpg.render_dearpygui_frame()

    def _close_dialog(self) -> None:
        self._closed = True
        if dpg.does_item_exist(self._dialog_tag):
            dpg.delete_item(self._dialog_tag)

    def _show_info(self, message: str) -> None:
        """Show an info popup."""
        info_tag = f"pref_info_{id(self)}"

        def _close_info():
            if dpg.does_item_exist(info_tag):
                dpg.delete_item(info_tag)

        with dpg.window(
            label="Kodex",
            tag=info_tag,
            modal=True,
            no_close=True,
            width=350,
            height=100,
            pos=[300, 200],
        ):
            dpg.add_text(message)
            dpg.add_spacer(height=12)
            dpg.add_button(label="OK", callback=_close_info, width=60)
