"""Reusable tkinter widgets for Plymotion UI."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from tkinter import ttk


class FilePicker(ttk.Frame):
    """File selection widget with browse button."""

    def __init__(
        self,
        master: tk.Widget,
        label: str = "File",
        filetypes: list[tuple[str, str]] | None = None,
        on_change: Callable[[str], None] | None = None,
        **kwargs,
    ) -> None:
        super().__init__(master, **kwargs)
        self._filetypes = filetypes or [
            ("Video files", "*.mp4 *.webm *.avi *.mkv *.mov"),
            ("All files", "*.*"),
        ]
        self._on_change = on_change
        self._path = tk.StringVar()

        ttk.Label(self, text=label).grid(row=0, column=0, sticky="w", padx=(0, 5))
        self._entry = ttk.Entry(self, textvariable=self._path, width=40)
        self._entry.grid(row=0, column=1, sticky="ew", padx=(0, 5))
        ttk.Button(self, text="Examinar", command=self._browse).grid(row=0, column=2)
        self.columnconfigure(1, weight=1)

    def _browse(self) -> None:
        from tkinter import filedialog

        path = filedialog.askopenfilename(filetypes=self._filetypes)
        if path:
            self._path.set(path)
            if self._on_change is not None:
                self._on_change(path)

    def get(self) -> str:
        return self._path.get()

    def set(self, value: str) -> None:
        self._path.set(value)


class LabeledCombo(ttk.Frame):
    """Labeled dropdown combo box."""

    def __init__(
        self,
        master: tk.Widget,
        label: str,
        values: list[str],
        default: str = "",
        **kwargs,
    ) -> None:
        super().__init__(master, **kwargs)
        self._var = tk.StringVar(value=default)

        ttk.Label(self, text=label).grid(row=0, column=0, sticky="w", padx=(0, 5))
        self._combo = ttk.Combobox(
            self, textvariable=self._var, values=values, state="readonly"
        )
        self._combo.grid(row=0, column=1, sticky="ew")
        self.columnconfigure(1, weight=1)

    def get(self) -> str:
        return self._var.get()


class LogPanel(ttk.Frame):
    """Scrollable, read-only log of step-by-step conversion messages."""

    def __init__(self, master: tk.Widget, height: int = 8, **kwargs) -> None:
        super().__init__(master, **kwargs)

        self._text = tk.Text(
            self,
            height=height,
            wrap="word",
            state="disabled",
            font=("monospace", 9),
        )
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=self._text.yview)
        self._text.configure(yscrollcommand=scrollbar.set)

        self._text.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

    def append(self, line: str) -> None:
        """Add a line to the log and scroll to the bottom."""
        self._text.configure(state="normal")
        self._text.insert("end", line + "\n")
        self._text.configure(state="disabled")
        self._text.see("end")

    def clear(self) -> None:
        self._text.configure(state="normal")
        self._text.delete("1.0", "end")
        self._text.configure(state="disabled")


class StatusBar(ttk.Label):
    """Status message bar at the bottom."""

    def __init__(self, master: tk.Widget, **kwargs) -> None:
        super().__init__(master, text="Listo", relief="sunken", anchor="w", **kwargs)
        self._messages: list[str] = []

    def set(self, text: str) -> None:
        self.configure(text=text)
        self._messages.append(text)

    def clear(self) -> None:
        self.configure(text="Listo")
