"""Time Tracking window — displays and exports time tracking data.

Shows all tracked tickets from time_tracking.json with their total time.
Provides export functionality to CSV format.
"""

from __future__ import annotations

import csv
import json
import logging
from datetime import datetime
from pathlib import Path
from tkinter import messagebox
from typing import TYPE_CHECKING

import customtkinter as ctk

if TYPE_CHECKING:
    from kodex_py.storage.database import Database

log = logging.getLogger(__name__)


def _get_data_dir() -> Path:
    """Get the Kodex data directory."""
    import os
    
    kodex_root = os.environ.get("KODEX_ROOT")
    if kodex_root:
        portable_data = Path(kodex_root) / "data"
        home_data = Path.home() / ".kodex"
        if portable_data.exists() or not home_data.exists():
            return portable_data
    
    return Path.home() / ".kodex"


def _format_duration(seconds: float) -> str:
    """Format seconds as HH:MM:SS."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


class TimeTrackingWindow:
    """Time tracking display and export window."""

    def __init__(self, parent=None, db: "Database" = None) -> None:
        self._parent = parent
        self._db = db
        self._window: ctk.CTkToplevel | None = None
        self._data_dir = _get_data_dir()
        self._time_tracking_file = self._data_dir / "time_tracking.json"

    def show(self) -> None:
        """Show the time tracking window (creates if needed)."""
        if self._window is not None and self._window.winfo_exists():
            self._window.lift()
            self._window.focus_force()
            self._refresh_data()
            return

        self._create_window()

    def _create_window(self) -> None:
        """Create the time tracking window."""
        win = ctk.CTkToplevel(self._parent)
        win.title("Time Tracking")
        win.geometry("500x400")
        win.minsize(400, 300)
        
        # Set window icon
        from kodex_py.gui.manager import _set_window_icon
        _set_window_icon(win, self._db)
        
        self._window = win

        # ── Header ──
        header_frame = ctk.CTkFrame(win, fg_color="transparent")
        header_frame.pack(fill="x", padx=10, pady=(10, 5))
        
        ctk.CTkLabel(
            header_frame,
            text="Ticket Time Tracking",
            font=ctk.CTkFont(size=18, weight="bold"),
        ).pack(side="left")
        
        # Refresh button
        ctk.CTkButton(
            header_frame,
            text="⟳ Refresh",
            width=80,
            command=self._refresh_data,
        ).pack(side="right")

        # ── Column headers ──
        columns_frame = ctk.CTkFrame(win, fg_color="transparent")
        columns_frame.pack(fill="x", padx=10, pady=(5, 0))
        
        ctk.CTkLabel(
            columns_frame,
            text="Ticket #",
            font=ctk.CTkFont(weight="bold"),
            width=120,
            anchor="w",
        ).pack(side="left", padx=(10, 0))
        
        ctk.CTkLabel(
            columns_frame,
            text="Time (HH:MM:SS)",
            font=ctk.CTkFont(weight="bold"),
            width=120,
            anchor="w",
        ).pack(side="left", padx=(20, 0))
        
        ctk.CTkLabel(
            columns_frame,
            text="Total Seconds",
            font=ctk.CTkFont(weight="bold"),
            width=100,
            anchor="w",
        ).pack(side="left", padx=(20, 0))
        
        ctk.CTkLabel(
            columns_frame,
            text="Source",
            font=ctk.CTkFont(weight="bold"),
            width=80,
            anchor="w",
        ).pack(side="left", padx=(20, 0))

        # ── Scrollable list ──
        self._list_frame = ctk.CTkScrollableFrame(win)
        self._list_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # ── Bottom buttons ──
        button_frame = ctk.CTkFrame(win, fg_color="transparent")
        button_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        ctk.CTkButton(
            button_frame,
            text="Export to CSV",
            width=120,
            command=self._export_csv,
        ).pack(side="left")
        
        ctk.CTkButton(
            button_frame,
            text="Close",
            width=80,
            fg_color="gray",
            command=win.destroy,
        ).pack(side="right")

        # Load data
        self._refresh_data()

    def _load_time_tracking(self) -> dict:
        """Load time_tracking.json data."""
        if not self._time_tracking_file.exists():
            return {"tickets": {}, "_active": None}
        
        try:
            with open(self._time_tracking_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            log.warning("Could not read time_tracking.json: %s", e)
            return {"tickets": {}, "_active": None}

    def _refresh_data(self) -> None:
        """Refresh the ticket list from time_tracking.json."""
        # Clear existing items
        for widget in self._list_frame.winfo_children():
            widget.destroy()
        
        data = self._load_time_tracking()
        tickets = data.get("tickets", {})
        active = data.get("_active")
        active_ticket = active.get("ticket_number") if active else None
        
        if not tickets:
            ctk.CTkLabel(
                self._list_frame,
                text="No time tracking data found.",
                text_color="gray",
            ).pack(pady=20)
            return
        
        # Sort by total_seconds descending (most time first)
        sorted_tickets = sorted(
            tickets.items(),
            key=lambda x: x[1].get("total_seconds", 0),
            reverse=True,
        )
        
        for ticket_num, info in sorted_tickets:
            total_seconds = info.get("total_seconds", 0)
            source = info.get("source", "unknown")
            
            # Create row frame
            row = ctk.CTkFrame(self._list_frame, fg_color="transparent")
            row.pack(fill="x", pady=2)
            
            # Highlight active ticket
            ticket_text = ticket_num
            if ticket_num == active_ticket:
                ticket_text = f"▶ {ticket_num}"
            
            ctk.CTkLabel(
                row,
                text=ticket_text,
                width=120,
                anchor="w",
                font=ctk.CTkFont(weight="bold") if ticket_num == active_ticket else None,
            ).pack(side="left", padx=(10, 0))
            
            ctk.CTkLabel(
                row,
                text=_format_duration(total_seconds),
                width=120,
                anchor="w",
            ).pack(side="left", padx=(20, 0))
            
            ctk.CTkLabel(
                row,
                text=f"{total_seconds:.2f}",
                width=100,
                anchor="w",
            ).pack(side="left", padx=(20, 0))
            
            ctk.CTkLabel(
                row,
                text=source,
                width=80,
                anchor="w",
                text_color="gray",
            ).pack(side="left", padx=(20, 0))

    def _export_csv(self) -> None:
        """Export time tracking data to CSV in ~/Documents."""
        data = self._load_time_tracking()
        tickets = data.get("tickets", {})
        
        if not tickets:
            messagebox.showwarning("Export", "No time tracking data to export.")
            return
        
        # Build export path: ~/Documents/MM.DD.YYYY.TimeTracking.csv
        documents_dir = Path.home() / "Documents"
        documents_dir.mkdir(parents=True, exist_ok=True)
        
        date_str = datetime.now().strftime("%m.%d.%Y")
        export_path = documents_dir / f"{date_str}.TimeTracking.csv"
        
        try:
            with open(export_path, "w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                
                # Sort by ticket number for consistent output
                for ticket_num in sorted(tickets.keys()):
                    info = tickets[ticket_num]
                    total_seconds = info.get("total_seconds", 0)
                    writer.writerow([ticket_num, f"{total_seconds:.6f}"])
            
            log.info("Exported time tracking to %s", export_path)
            messagebox.showinfo(
                "Export Complete",
                f"Time tracking exported to:\n{export_path}\n\n{len(tickets)} tickets exported.",
            )
        
        except OSError as e:
            log.error("Failed to export CSV: %s", e)
            messagebox.showerror("Export Failed", f"Could not write CSV file:\n{e}")
