"""Preferences window — mirrors AHK preferences_GUI.ahk.

Four tabs:
- General: hotkeys, send mode, sound, startup
- Print: cheatsheet generation
- Stats: expansion statistics
- Agent Info: agent-specific information for global variables
"""

from __future__ import annotations

import logging
import tkinter as tk
from tkinter import filedialog, messagebox
from typing import TYPE_CHECKING

import customtkinter as ctk

if TYPE_CHECKING:
    from kodex_py.storage.database import Database

log = logging.getLogger(__name__)


class PreferencesWindow:
    """Preferences dialog with General / Print / Stats / Agent Info tabs."""

    def __init__(self, db: "Database", parent=None, on_save=None) -> None:
        self.db = db
        self._parent = parent
        self._on_save = on_save  # Callback after config is saved

    def show(self) -> None:
        from kodex_py.config import load_config, save_config
        from kodex_py.storage.models import SendMode

        cfg = load_config(self.db)

        win = ctk.CTkToplevel(self._parent)
        win.title("Kodex — Preferences")
        win.geometry("550x620")  # Increased size for Agent Info tab
        win.minsize(500, 550)
        win.grab_set()
        win.lift()
        win.focus_force()
        
        # Set window icon
        try:
            from kodex_py.gui.manager import _set_window_icon
            _set_window_icon(win, self.db)
        except Exception as e:
            log.debug("Could not set window icon: %s", e)

        # ── Variables ──
        hk_create_var = tk.StringVar(value=cfg.hotkey_create)
        hk_manage_var = tk.StringVar(value=cfg.hotkey_manage)
        hk_disable_var = tk.StringVar(value=cfg.hotkey_disable)
        hk_tracker_var = tk.StringVar(value=cfg.hotkey_tracker)

        current_mode = "Clipboard" if cfg.send_mode == SendMode.CLIPBOARD else "Direct"
        mode_var = tk.StringVar(value=current_mode)

        sound_var = tk.BooleanVar(value=cfg.play_sound)
        startup_var = tk.BooleanVar(value=cfg.run_at_startup)
        autocorrect_var = tk.BooleanVar(value=cfg.autocorrect_enabled)

        # ── Stats data ──
        expanded = self.db.get_stat("expanded") or 0
        chars = self.db.get_stat("chars_saved") or 0
        hours = chars / 24_000 if chars else 0
        total_hs = len(self.db.get_hotstrings())
        total_bundles = len(self.db.get_bundles())

        # ── Agent Info variables (load early) ──
        agent_name_var = tk.StringVar(value="")
        agent_email_var = tk.StringVar(value="")
        agent_team_var = tk.StringVar(value="")
        agent_workdays_var = tk.StringVar(value="")
        agent_shift_var = tk.StringVar(value="")
        agent_company_var = tk.StringVar(value="")
        
        try:
            from kodex_py.utils.agent_info import load_agent_info, save_agent_info, AgentInfo
            from pathlib import Path
            
            data_dir = Path(self.db.db_path).parent if self.db and self.db.db_path else None
            current_agent = load_agent_info(data_dir)
            
            agent_name_var.set(current_agent.name)
            agent_email_var.set(current_agent.email)
            agent_team_var.set(current_agent.team)
            agent_workdays_var.set(current_agent.workdays)
            agent_shift_var.set(current_agent.shift)
            agent_company_var.set(current_agent.company)
            
            agent_info_available = True
        except Exception as e:
            log.warning("Could not load agent info: %s", e)
            agent_info_available = False
            AgentInfo = None
            save_agent_info = None
            data_dir = None

        # ── Main layout ──
        main_frame = ctk.CTkFrame(win, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=16, pady=16)

        # Tabs
        tabview = ctk.CTkTabview(main_frame, height=480)
        tabview.pack(fill="both", expand=True)

        # ══════════════════════════════════════════════════════════════
        # ── General Tab ──
        # ══════════════════════════════════════════════════════════════
        gen = tabview.add("General")
        gen_scroll = ctk.CTkScrollableFrame(gen, fg_color="transparent")
        gen_scroll.pack(fill="both", expand=True)

        # Hotkeys section
        hk_frame = ctk.CTkFrame(gen_scroll, corner_radius=6)
        hk_frame.pack(fill="x", pady=(8, 8), padx=4)
        ctk.CTkLabel(
            hk_frame, text="Hotkeys", font=ctk.CTkFont(weight="bold"), anchor="w"
        ).pack(anchor="w", padx=12, pady=(8, 4))

        def _hotkey_row(parent, label: str, var: tk.StringVar) -> None:
            row = ctk.CTkFrame(parent, fg_color="transparent")
            row.pack(fill="x", padx=12, pady=2)
            ctk.CTkLabel(row, text=label, width=160, anchor="w").pack(side="left")
            ctk.CTkEntry(row, textvariable=var, width=180).pack(side="left")

        _hotkey_row(hk_frame, "Create hotstring:", hk_create_var)
        _hotkey_row(hk_frame, "Manage hotstrings:", hk_manage_var)
        _hotkey_row(hk_frame, "Disable toggle:", hk_disable_var)
        _hotkey_row(hk_frame, "Ticket tracker:", hk_tracker_var)
        ctk.CTkFrame(hk_frame, fg_color="transparent", height=8).pack()

        # Send mode section
        mode_frame = ctk.CTkFrame(gen_scroll, corner_radius=6)
        mode_frame.pack(fill="x", pady=(0, 8), padx=4)
        ctk.CTkLabel(
            mode_frame, text="Send Mode", font=ctk.CTkFont(weight="bold"), anchor="w"
        ).pack(anchor="w", padx=12, pady=(8, 4))
        
        mode_row = ctk.CTkFrame(mode_frame, fg_color="transparent")
        mode_row.pack(fill="x", padx=12, pady=(0, 4))
        mode_combo = ctk.CTkComboBox(
            mode_row, values=["Direct", "Clipboard"], variable=mode_var, width=200
        )
        mode_combo.pack(side="left")
        
        ctk.CTkLabel(
            mode_frame,
            text="Direct = keystroke injection  |  Clipboard = Ctrl+V paste",
            text_color="gray60",
            anchor="w",
        ).pack(anchor="w", padx=12, pady=(0, 8))

        # Checkboxes
        checks_frame = ctk.CTkFrame(gen_scroll, fg_color="transparent")
        checks_frame.pack(fill="x", padx=4, pady=(0, 8))
        ctk.CTkCheckBox(
            checks_frame, text="Play sound on expansion", variable=sound_var
        ).pack(anchor="w", pady=3)
        ctk.CTkCheckBox(
            checks_frame, text="Run at Windows startup", variable=startup_var
        ).pack(anchor="w", pady=3)
        ctk.CTkCheckBox(
            checks_frame, text="Enable autocorrect", variable=autocorrect_var
        ).pack(anchor="w", pady=3)

        # ══════════════════════════════════════════════════════════════
        # ── Print Tab ──
        # ══════════════════════════════════════════════════════════════
        prn = tabview.add("Print")
        prn_inner = ctk.CTkFrame(prn, fg_color="transparent")
        prn_inner.pack(fill="both", expand=True, padx=8, pady=20)
        ctk.CTkLabel(
            prn_inner, 
            text="Generate a printable HTML cheatsheet\nof all your hotstrings.", 
            anchor="w",
            justify="left",
        ).pack(anchor="w", pady=(0, 20))

        def _do_cheatsheet():
            from kodex_py.gui.cheatsheet import generate_cheatsheet

            path = filedialog.asksaveasfilename(
                parent=win,
                title="Save Cheatsheet",
                defaultextension=".html",
                initialfile="kodex-cheatsheet.html",
                filetypes=[("HTML files", "*.html"), ("All files", "*.*")],
            )
            if path:
                generate_cheatsheet(self.db, path)
                messagebox.showinfo("Kodex", f"Cheatsheet saved to:\n{path}", parent=win)

        ctk.CTkButton(prn_inner, text="Generate Cheatsheet", command=_do_cheatsheet).pack(
            anchor="w"
        )

        # ══════════════════════════════════════════════════════════════
        # ── Stats Tab ──
        # ══════════════════════════════════════════════════════════════
        stats = tabview.add("Stats")
        stats_inner = ctk.CTkFrame(stats, fg_color="transparent")
        stats_inner.pack(fill="both", expand=True, padx=8, pady=12)

        def _stat_row(label: str, value: str) -> None:
            row = ctk.CTkFrame(stats_inner, fg_color="transparent")
            row.pack(fill="x", pady=4)
            ctk.CTkLabel(row, text=label, width=160, anchor="w").pack(side="left")
            ctk.CTkLabel(row, text=value, text_color="#64C8FF", anchor="w").pack(side="left")

        _stat_row("Hotstrings:", str(total_hs))
        _stat_row("Bundles:", str(total_bundles))
        _stat_row("Expansions:", f"{expanded:,}")
        _stat_row("Characters saved:", f"{chars:,}")
        _stat_row("Hours saved:", f"{hours:.1f}")

        # ══════════════════════════════════════════════════════════════
        # ── Agent Info Tab ──
        # ══════════════════════════════════════════════════════════════
        agent_tab = tabview.add("Agent Info")
        agent_inner = ctk.CTkFrame(agent_tab, fg_color="transparent")
        agent_inner.pack(fill="both", expand=True, padx=8, pady=12)
        
        ctk.CTkLabel(
            agent_inner,
            text="Agent Information",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(anchor="w", pady=(0, 8))
        
        ctk.CTkLabel(
            agent_inner,
            text="This information is available as global variables:\n"
                 "%agent_name%, %agent_email%, %agent_team%, etc.",
            text_color="gray60",
            justify="left",
        ).pack(anchor="w", pady=(0, 12))
        
        def _agent_field(label: str, var: tk.StringVar) -> None:
            row = ctk.CTkFrame(agent_inner, fg_color="transparent")
            row.pack(fill="x", pady=4)
            ctk.CTkLabel(row, text=label, width=120, anchor="w").pack(side="left")
            ctk.CTkEntry(row, textvariable=var, width=280).pack(side="left", padx=(0, 8))
        
        _agent_field("Agent Name:", agent_name_var)
        _agent_field("Agent Email:", agent_email_var)
        _agent_field("Agent Team:", agent_team_var)
        _agent_field("Workdays:", agent_workdays_var)
        _agent_field("Shift:", agent_shift_var)
        _agent_field("Company:", agent_company_var)
        
        ctk.CTkLabel(
            agent_inner,
            text="Example workdays: Sunday, Monday, Tuesday, Wednesday, Thursday\n"
                 "Example shift: 9am-6pm",
            text_color="gray50",
            font=ctk.CTkFont(size=11),
            justify="left",
        ).pack(anchor="w", pady=(12, 0))

        # ══════════════════════════════════════════════════════════════
        # ── Bottom Buttons ──
        # ══════════════════════════════════════════════════════════════
        btn_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        btn_frame.pack(fill="x", pady=(12, 0))

        def _on_save():
            # Save general config
            cfg.hotkey_create = hk_create_var.get()
            cfg.hotkey_manage = hk_manage_var.get()
            cfg.hotkey_disable = hk_disable_var.get()
            cfg.hotkey_tracker = hk_tracker_var.get()
            cfg.send_mode = (
                SendMode.CLIPBOARD if mode_var.get() == "Clipboard" else SendMode.DIRECT
            )
            cfg.play_sound = sound_var.get()
            cfg.run_at_startup = startup_var.get()
            cfg.autocorrect_enabled = autocorrect_var.get()
            save_config(self.db, cfg)
            
            # Save agent info
            if agent_info_available and AgentInfo and save_agent_info:
                try:
                    new_agent = AgentInfo(
                        name=agent_name_var.get(),
                        email=agent_email_var.get(),
                        team=agent_team_var.get(),
                        workdays=agent_workdays_var.get(),
                        shift=agent_shift_var.get(),
                        company=agent_company_var.get(),
                    )
                    save_agent_info(new_agent, data_dir)
                except Exception as e:
                    log.warning("Failed to save agent info: %s", e)
            
            # Notify app to reload config
            if self._on_save:
                self._on_save()
            
            win.grab_release()
            win.destroy()

        def _on_cancel():
            win.grab_release()
            win.destroy()

        win.bind("<Escape>", lambda _: _on_cancel())

        ctk.CTkButton(btn_frame, text="Cancel", command=_on_cancel, width=100, 
                      fg_color="gray40", hover_color="gray30").pack(side="right", padx=(8, 0))
        ctk.CTkButton(btn_frame, text="Save", command=_on_save, width=100).pack(side="right")

        win.wait_window()
