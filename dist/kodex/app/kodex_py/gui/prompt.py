"""Text prompt dialog — shown when a replacement contains %p.

Mirrors AHK textprompt_GUI.ahk: modal, always-on-top, shows the template
and lets the user fill in the %p placeholder.
"""

from __future__ import annotations

import logging

log = logging.getLogger(__name__)


def show_prompt(template: str, parent=None) -> str | None:
    """Show a prompt dialog for the %p variable.

    Returns the user's input, or None if cancelled.
    """
    import tkinter as tk
    from tkinter import ttk

    result = [None]

    dialog = tk.Toplevel(parent)
    dialog.title("Kodex — Fill In")
    dialog.geometry("400x250")
    dialog.resizable(False, False)
    dialog.attributes("-topmost", True)
    if parent:
        dialog.transient(parent)
    dialog.grab_set()

    frame = ttk.Frame(dialog, padding=12)
    frame.pack(fill=tk.BOTH, expand=True)

    ttk.Label(frame, text="Template:").pack(anchor=tk.W)
    template_display = tk.Text(frame, height=5, wrap=tk.WORD, state=tk.DISABLED,
                                font=("Consolas", 9))
    template_display.pack(fill=tk.X, pady=(0, 8))
    template_display.config(state=tk.NORMAL)
    template_display.insert("1.0", template)
    # Highlight %p
    start = "1.0"
    while True:
        pos = template_display.search("%p", start, stopindex=tk.END)
        if not pos:
            break
        end_pos = f"{pos}+2c"
        template_display.tag_add("highlight", pos, end_pos)
        start = end_pos
    template_display.tag_config("highlight", background="#FFD700", foreground="#000")
    template_display.config(state=tk.DISABLED)

    ttk.Label(frame, text="Fill in:").pack(anchor=tk.W)
    input_var = tk.StringVar()
    entry = ttk.Entry(frame, textvariable=input_var, width=40)
    entry.pack(fill=tk.X, pady=(0, 8))
    entry.focus_set()

    btn_frame = ttk.Frame(frame)
    btn_frame.pack(fill=tk.X)

    def on_ok(*_):
        result[0] = input_var.get()
        dialog.destroy()

    def on_cancel():
        dialog.destroy()

    entry.bind("<Return>", on_ok)
    ttk.Button(btn_frame, text="OK", command=on_ok).pack(side=tk.RIGHT, padx=(4, 0))
    ttk.Button(btn_frame, text="Cancel", command=on_cancel).pack(side=tk.RIGHT)

    dialog.wait_window()
    return result[0]
