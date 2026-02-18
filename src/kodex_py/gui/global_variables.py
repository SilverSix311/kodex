"""Global Variables management UI — tkinter pane for managing user-defined variables.

Provides a tab/section in settings for:
- Viewing all variables (name, type, value)
- Adding new variables with type selection
- Editing existing variables
- Deleting variables
"""

from __future__ import annotations

import json
import logging
from typing import Any

log = logging.getLogger(__name__)


class GlobalVariablesPane:
    """UI pane for managing global variables."""

    def __init__(self, parent, global_vars=None) -> None:
        """Initialize the Global Variables pane.
        
        Args:
            parent: Parent tkinter widget
            global_vars: GlobalVariables instance (or None to use singleton)
        """
        import tkinter as tk
        from tkinter import ttk
        
        self.parent = parent
        self._frame = ttk.Frame(parent, padding=12)
        
        # Get or create GlobalVariables instance
        if global_vars is None:
            from kodex_py.utils.global_variables import get_global_variables
            self._gv = get_global_variables()
        else:
            self._gv = global_vars
        
        self._selected_var: str | None = None
        self._create_widgets()
        self._load_variables()

    @property
    def frame(self):
        """Return the frame widget for embedding in notebook/parent."""
        return self._frame

    def _create_widgets(self) -> None:
        """Build the UI components."""
        import tkinter as tk
        from tkinter import ttk
        
        # Main container with two columns
        main = ttk.Frame(self._frame)
        main.pack(fill=tk.BOTH, expand=True)
        
        # ── Left: Variable list ──
        left = ttk.Frame(main)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=False, padx=(0, 8))
        
        ttk.Label(left, text="Variables:", font=("Segoe UI", 10, "bold")).pack(anchor=tk.W)
        
        # Treeview for variables
        columns = ("type", "value")
        self._tree = ttk.Treeview(left, columns=columns, show="tree headings", height=15)
        self._tree.heading("#0", text="Name", anchor=tk.W)
        self._tree.heading("type", text="Type", anchor=tk.W)
        self._tree.heading("value", text="Value", anchor=tk.W)
        self._tree.column("#0", width=120, minwidth=80)
        self._tree.column("type", width=70, minwidth=50)
        self._tree.column("value", width=180, minwidth=100)
        self._tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._tree.bind("<<TreeviewSelect>>", self._on_select)
        
        scrollbar = ttk.Scrollbar(left, orient=tk.VERTICAL, command=self._tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self._tree.config(yscrollcommand=scrollbar.set)
        
        # ── Right: Editor ──
        right = ttk.Frame(main)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Name
        name_frame = ttk.Frame(right)
        name_frame.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(name_frame, text="Name:").pack(side=tk.LEFT)
        self._name_var = tk.StringVar()
        self._name_entry = ttk.Entry(name_frame, textvariable=self._name_var, width=25)
        self._name_entry.pack(side=tk.LEFT, padx=(4, 0))
        
        # Type selector
        type_frame = ttk.Frame(right)
        type_frame.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(type_frame, text="Type:").pack(side=tk.LEFT)
        self._type_var = tk.StringVar(value="string")
        self._type_combo = ttk.Combobox(
            type_frame,
            textvariable=self._type_var,
            values=["string", "int", "decimal", "boolean", "array", "dict"],
            state="readonly",
            width=12
        )
        self._type_combo.pack(side=tk.LEFT, padx=(4, 0))
        self._type_combo.bind("<<ComboboxSelected>>", self._on_type_change)
        
        # Value editor frame (changes based on type)
        self._value_frame = ttk.LabelFrame(right, text="Value")
        self._value_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 8))
        
        # Default: text entry for string values
        self._value_var = tk.StringVar()
        self._value_widget = None
        self._create_value_editor("string")
        
        # Buttons
        btn_frame = ttk.Frame(right)
        btn_frame.pack(fill=tk.X)
        
        ttk.Button(btn_frame, text="+ New", command=self._new_variable).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(btn_frame, text="Save", command=self._save_variable).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(btn_frame, text="Delete", command=self._delete_variable).pack(side=tk.LEFT)
        ttk.Button(btn_frame, text="Refresh", command=self._load_variables).pack(side=tk.RIGHT)
        
        # ── Freshdesk context section (read-only) ──
        fd_frame = ttk.LabelFrame(self._frame, text="Ticket Context (from Freshdesk extension)")
        fd_frame.pack(fill=tk.X, pady=(12, 0))
        
        self._fd_tree = ttk.Treeview(fd_frame, columns=("value",), show="tree headings", height=4)
        self._fd_tree.heading("#0", text="Field", anchor=tk.W)
        self._fd_tree.heading("value", text="Value", anchor=tk.W)
        self._fd_tree.column("#0", width=150, minwidth=100)
        self._fd_tree.column("value", width=300, minwidth=150)
        self._fd_tree.pack(fill=tk.X, padx=4, pady=4)
        
        ttk.Label(
            fd_frame,
            text="These values come from the Freshdesk browser extension and override global variables.",
            foreground="gray"
        ).pack(anchor=tk.W, padx=4, pady=(0, 4))

    def _create_value_editor(self, var_type: str) -> None:
        """Create appropriate value editor widget based on type."""
        import tkinter as tk
        from tkinter import ttk
        
        # Clear existing widget
        if self._value_widget:
            self._value_widget.destroy()
        
        if var_type == "boolean":
            # Checkbox for boolean
            self._bool_var = tk.BooleanVar()
            self._value_widget = ttk.Checkbutton(
                self._value_frame,
                text="True",
                variable=self._bool_var
            )
            self._value_widget.pack(anchor=tk.W, padx=8, pady=8)
        
        elif var_type in ("array", "dict"):
            # Multi-line text for JSON
            self._value_widget = tk.Text(
                self._value_frame,
                wrap=tk.WORD,
                font=("Consolas", 10),
                height=6,
                width=40
            )
            self._value_widget.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)
            
            # Hint label
            hint = "Enter JSON array" if var_type == "array" else "Enter JSON object"
            ttk.Label(self._value_frame, text=f"Hint: {hint}", foreground="gray").pack(anchor=tk.W, padx=4)
        
        else:
            # Single-line entry for string, int, decimal
            self._value_widget = ttk.Entry(
                self._value_frame,
                textvariable=self._value_var,
                width=40
            )
            self._value_widget.pack(anchor=tk.W, padx=8, pady=8)
            
            if var_type == "int":
                ttk.Label(self._value_frame, text="Hint: Enter an integer (e.g., 42)", foreground="gray").pack(anchor=tk.W, padx=8)
            elif var_type == "decimal":
                ttk.Label(self._value_frame, text="Hint: Enter a decimal number (e.g., 3.14)", foreground="gray").pack(anchor=tk.W, padx=8)

    def _on_type_change(self, event=None) -> None:
        """Handle type selection change."""
        self._create_value_editor(self._type_var.get())

    def _load_variables(self) -> None:
        """Load variables into the treeview."""
        import tkinter as tk
        
        # Reload from files
        self._gv.load()
        
        # Clear tree
        for item in self._tree.get_children():
            self._tree.delete(item)
        
        # Add global variables
        for name, data in sorted(self._gv.list_all().items()):
            var_type = data.get("type", "string")
            value = data.get("value")
            value_str = self._format_value(value)
            self._tree.insert("", tk.END, iid=name, text=name, values=(var_type, value_str))
        
        # Load freshdesk context
        for item in self._fd_tree.get_children():
            self._fd_tree.delete(item)
        
        for name, value in sorted(self._gv.get_freshdesk_context().items()):
            value_str = self._format_value(value)
            self._fd_tree.insert("", tk.END, text=name, values=(value_str,))

    def _format_value(self, value: Any) -> str:
        """Format a value for display."""
        if isinstance(value, bool):
            return "true" if value else "false"
        elif isinstance(value, (list, dict)):
            return json.dumps(value, ensure_ascii=False)
        else:
            return str(value)

    def _on_select(self, event=None) -> None:
        """Handle treeview selection."""
        import tkinter as tk
        
        selection = self._tree.selection()
        if not selection:
            return
        
        name = selection[0]
        self._selected_var = name
        
        variables = self._gv.list_all()
        if name not in variables:
            return
        
        data = variables[name]
        var_type = data.get("type", "string")
        value = data.get("value")
        
        # Update editor
        self._name_var.set(name)
        self._type_var.set(var_type)
        self._create_value_editor(var_type)
        self._set_value(var_type, value)

    def _set_value(self, var_type: str, value: Any) -> None:
        """Set the value in the appropriate widget."""
        import tkinter as tk
        
        if var_type == "boolean":
            self._bool_var.set(bool(value))
        elif var_type in ("array", "dict"):
            self._value_widget.delete("1.0", tk.END)
            self._value_widget.insert("1.0", json.dumps(value, indent=2, ensure_ascii=False))
        else:
            self._value_var.set(str(value) if value is not None else "")

    def _get_value(self, var_type: str) -> Any:
        """Get the value from the appropriate widget."""
        import tkinter as tk
        from tkinter import messagebox
        
        if var_type == "boolean":
            return self._bool_var.get()
        
        elif var_type == "array":
            text = self._value_widget.get("1.0", tk.END).strip()
            try:
                value = json.loads(text)
                if not isinstance(value, list):
                    raise ValueError("Must be a JSON array")
                return value
            except (json.JSONDecodeError, ValueError) as e:
                messagebox.showerror("Invalid Value", f"Invalid JSON array: {e}")
                return None
        
        elif var_type == "dict":
            text = self._value_widget.get("1.0", tk.END).strip()
            try:
                value = json.loads(text)
                if not isinstance(value, dict):
                    raise ValueError("Must be a JSON object")
                return value
            except (json.JSONDecodeError, ValueError) as e:
                messagebox.showerror("Invalid Value", f"Invalid JSON object: {e}")
                return None
        
        elif var_type == "int":
            try:
                return int(self._value_var.get())
            except ValueError:
                messagebox.showerror("Invalid Value", "Please enter a valid integer.")
                return None
        
        elif var_type == "decimal":
            try:
                return float(self._value_var.get())
            except ValueError:
                messagebox.showerror("Invalid Value", "Please enter a valid decimal number.")
                return None
        
        else:  # string
            return self._value_var.get()

    def _new_variable(self) -> None:
        """Clear editor for new variable."""
        import tkinter as tk
        
        self._selected_var = None
        self._name_var.set("")
        self._type_var.set("string")
        self._create_value_editor("string")
        self._value_var.set("")
        self._tree.selection_remove(self._tree.selection())
        self._name_entry.focus_set()

    def _save_variable(self) -> None:
        """Save the current variable."""
        from tkinter import messagebox
        
        name = self._name_var.get().strip()
        if not name:
            messagebox.showwarning("Kodex", "Variable name cannot be empty.")
            return
        
        # Validate name (alphanumeric + underscore, starts with letter/underscore)
        import re
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', name):
            messagebox.showwarning(
                "Kodex",
                "Variable name must start with a letter or underscore,\n"
                "and contain only letters, numbers, and underscores."
            )
            return
        
        var_type = self._type_var.get()
        value = self._get_value(var_type)
        
        if value is None and var_type in ("array", "dict", "int", "decimal"):
            # Validation failed
            return
        
        # Check if renaming
        if self._selected_var and self._selected_var != name:
            self._gv.delete(self._selected_var)
        
        self._gv.set(name, value, var_type)
        self._selected_var = name
        self._load_variables()
        
        # Re-select the saved item
        if name in self._tree.get_children():
            self._tree.selection_set(name)
            self._tree.see(name)

    def _delete_variable(self) -> None:
        """Delete the selected variable."""
        from tkinter import messagebox
        
        if not self._selected_var:
            return
        
        if messagebox.askyesno("Kodex", f"Delete variable '{self._selected_var}'?"):
            self._gv.delete(self._selected_var)
            self._selected_var = None
            self._load_variables()
            self._new_variable()


class GlobalVariablesWindow:
    """Standalone window for global variables management."""

    def __init__(self, parent=None, global_vars=None) -> None:
        self._parent = parent
        self._global_vars = global_vars
        self._dialog = None

    def show(self) -> None:
        """Create and show the window."""
        import tkinter as tk
        
        self._dialog = tk.Toplevel(self._parent)
        self._dialog.title("Kodex — Global Variables")
        self._dialog.geometry("700x550")
        self._dialog.resizable(True, True)
        if self._parent:
            self._dialog.transient(self._parent)
        
        pane = GlobalVariablesPane(self._dialog, self._global_vars)
        pane.frame.pack(fill=tk.BOTH, expand=True)
        
        # Close button
        btn_frame = tk.Frame(self._dialog)
        btn_frame.pack(fill=tk.X, padx=8, pady=8)
        tk.Button(btn_frame, text="Close", command=self._dialog.destroy).pack(side=tk.RIGHT)
        
        self._dialog.focus_set()
