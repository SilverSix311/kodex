"""Text prompt dialog — shown when a replacement contains %p.

Mirrors AHK textprompt_GUI.ahk: modal, always-on-top, shows the template
and lets the user fill in the %p placeholder.
"""

from __future__ import annotations

import logging

log = logging.getLogger(__name__)

# Result storage for the modal dialog
_prompt_result: str | None = None


def show_prompt(template: str, parent=None) -> str | None:
    """Show a prompt dialog for the %p variable.

    Returns the user's input, or None if cancelled.

    Note: This creates a temporary viewport if Dear PyGui isn't already running.
    When called from an existing DPG context, it creates a modal window.
    """
    import dearpygui.dearpygui as dpg

    global _prompt_result
    _prompt_result = None

    # Check if DPG context exists
    dpg_running = False
    try:
        dpg_running = dpg.is_dearpygui_running()
    except Exception:
        pass

    dialog_tag = "prompt_dialog"
    input_tag = "prompt_input"

    def _on_ok():
        global _prompt_result
        _prompt_result = dpg.get_value(input_tag)
        dpg.delete_item(dialog_tag)
        if not dpg_running:
            dpg.stop_dearpygui()

    def _on_cancel():
        global _prompt_result
        _prompt_result = None
        dpg.delete_item(dialog_tag)
        if not dpg_running:
            dpg.stop_dearpygui()

    def _on_key_press(sender, app_data):
        if app_data == dpg.mvKey_Return:
            _on_ok()
        elif app_data == dpg.mvKey_Escape:
            _on_cancel()

    def _build_dialog():
        # Highlight %p in template for display
        display_template = template.replace("%p", "[%p]")

        with dpg.window(
            label="Kodex — Fill In",
            tag=dialog_tag,
            modal=True,
            no_close=True,
            width=420,
            height=280,
            pos=[100, 100],
        ):
            dpg.add_text("Template:")
            dpg.add_input_text(
                default_value=display_template,
                multiline=True,
                readonly=True,
                height=80,
                width=-1,
            )

            dpg.add_spacer(height=8)
            dpg.add_text("Fill in:")
            dpg.add_input_text(
                tag=input_tag,
                width=-1,
                on_enter=True,
                callback=lambda: _on_ok(),
            )

            dpg.add_spacer(height=12)
            with dpg.group(horizontal=True):
                dpg.add_button(label="Cancel", callback=_on_cancel, width=80)
                dpg.add_button(label="OK", callback=_on_ok, width=80)

        # Focus the input
        dpg.focus_item(input_tag)

        # Key handler for enter/escape
        with dpg.handler_registry(tag="prompt_key_handler"):
            dpg.add_key_press_handler(callback=_on_key_press)

    if dpg_running:
        # Already running — just add modal window
        _build_dialog()
        # Wait for dialog to close (busy-wait since we're in existing loop)
        while dpg.does_item_exist(dialog_tag):
            pass
    else:
        # Create temporary context
        dpg.create_context()
        dpg.create_viewport(title="Kodex — Fill In", width=440, height=300, always_on_top=True)
        dpg.setup_dearpygui()

        _build_dialog()

        dpg.show_viewport()
        dpg.start_dearpygui()
        dpg.destroy_context()

    # Cleanup key handler if it exists
    try:
        if dpg.does_item_exist("prompt_key_handler"):
            dpg.delete_item("prompt_key_handler")
    except Exception:
        pass

    return _prompt_result
