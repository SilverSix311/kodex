"""Text prompt dialog — shown when a replacement contains %p.

Mirrors AHK textprompt_GUI.ahk: modal, always-on-top, shows the template
and lets the user fill in the %p placeholder.
"""

from __future__ import annotations

import logging
import threading

import customtkinter as ctk

log = logging.getLogger(__name__)


def _get_root(parent=None):
    """Return the best available Tk root for parenting dialogs."""
    if parent is not None:
        return parent
    try:
        from kodex_py.tray import get_tk_root
        root = get_tk_root()
        if root is not None:
            return root
    except Exception:
        pass
    return None


def _show_prompt_dialog(template: str, parent=None) -> str | None:
    """Must be called from the main thread. Shows a modal prompt dialog."""
    result: list[str | None] = [None]

    win = ctk.CTkToplevel(parent)
    win.title("Kodex — Fill In")
    win.geometry("440x300")
    win.resizable(False, False)
    win.attributes("-topmost", True)
    win.grab_set()
    win.lift()
    win.focus_force()

    # Template display
    display_template = template.replace("%prompt%", "[%prompt%]")

    outer = ctk.CTkFrame(win, fg_color="transparent")
    outer.pack(fill="both", expand=True, padx=16, pady=16)

    ctk.CTkLabel(outer, text="Template:", anchor="w").pack(fill="x", pady=(0, 4))

    template_box = ctk.CTkTextbox(outer, height=90, wrap="word", state="disabled")
    template_box.pack(fill="x", pady=(0, 12))
    template_box.configure(state="normal")
    template_box.insert("1.0", display_template)
    template_box.configure(state="disabled")

    ctk.CTkLabel(outer, text="Fill in:", anchor="w").pack(fill="x", pady=(0, 4))
    input_entry = ctk.CTkEntry(outer, width=400)
    input_entry.pack(fill="x", pady=(0, 16))

    def _on_ok(_event=None):
        result[0] = input_entry.get()
        win.grab_release()
        win.destroy()

    def _on_cancel(_event=None):
        result[0] = None
        win.grab_release()
        win.destroy()

    win.bind("<Return>", _on_ok)
    win.bind("<Escape>", _on_cancel)

    btn_row = ctk.CTkFrame(outer, fg_color="transparent")
    btn_row.pack(fill="x")
    ctk.CTkButton(btn_row, text="Cancel", command=_on_cancel, width=80).pack(side="left", padx=(0, 8))
    ctk.CTkButton(btn_row, text="OK", command=_on_ok, width=80).pack(side="left")

    input_entry.focus_set()
    win.wait_window()

    return result[0]


def show_prompt(template: str, parent=None) -> str | None:
    """Show a prompt dialog for the %p variable.

    Returns the user's input, or None if cancelled.
    Thread-safe: can be called from any thread.
    """
    if threading.current_thread() is threading.main_thread():
        return _show_prompt_dialog(template, parent)

    # Called from background thread — schedule on main thread and wait
    result: list[str | None] = [None]
    done = threading.Event()

    root = _get_root(parent)
    if root is None:
        log.warning("show_prompt: no Tk root available, returning empty string")
        return ""

    def _do():
        result[0] = _show_prompt_dialog(template, parent)
        done.set()

    root.after(0, _do)
    done.wait(timeout=300)  # 5-minute timeout
    return result[0]
