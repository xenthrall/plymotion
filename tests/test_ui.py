"""Tests for UI module."""

from __future__ import annotations

import tkinter as tk

import pytest


@pytest.fixture
def root() -> tk.Tk:
    """Create a Tk root for testing (headless)."""
    root = tk.Tk()
    root.withdraw()
    yield root
    root.destroy()


def test_widgets_import() -> None:
    """Widgets module imports without error."""
    from plymotion.ui.widgets import FilePicker, LabeledCombo, LogPanel, StatusBar
    assert FilePicker is not None
    assert LabeledCombo is not None
    assert StatusBar is not None
    assert LogPanel is not None


def test_app_import() -> None:
    """App module imports without error."""
    from plymotion.ui.app import PlymotionApp
    assert PlymotionApp is not None


def test_labeled_combo(root: tk.Tk) -> None:
    """LabeledCombo can be created and read."""
    from plymotion.ui.widgets import LabeledCombo

    combo = LabeledCombo(root, "Test:", ["a", "b", "c"], default="b")
    combo.pack()
    assert combo.get() == "b"


def test_status_bar(root: tk.Tk) -> None:
    """StatusBar can be created and updated."""
    from plymotion.ui.widgets import StatusBar

    bar = StatusBar(root)
    bar.pack()
    bar.set("Working")
    assert bar.cget("text") == "Working"
    bar.clear()
    assert bar.cget("text") == "Listo"


def test_log_panel(root: tk.Tk) -> None:
    """LogPanel accumulates lines and can be cleared."""
    from plymotion.ui.widgets import LogPanel

    panel = LogPanel(root)
    panel.pack()
    panel.append("first")
    panel.append("second")

    content = panel._text.get("1.0", "end")
    assert "first" in content
    assert "second" in content

    panel.clear()
    assert panel._text.get("1.0", "end").strip() == ""


def test_file_picker_on_change_callback(root: tk.Tk) -> None:
    """FilePicker invokes on_change when a value is set via _browse-equivalent."""
    from plymotion.ui.widgets import FilePicker

    seen: list[str] = []
    picker = FilePicker(root, on_change=seen.append)
    picker.pack()

    # Simulate what _browse does after a user picks a file.
    picker._path.set("dummy.mp4")
    if picker._on_change is not None:
        picker._on_change(picker.get())

    assert seen == ["dummy.mp4"]
