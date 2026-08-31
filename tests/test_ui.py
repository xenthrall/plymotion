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
    from plymotion.ui.widgets import FilePicker, LabeledCombo, StatusBar
    assert FilePicker is not None
    assert LabeledCombo is not None
    assert StatusBar is not None


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
