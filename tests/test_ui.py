"""Tests for the Flet UI module."""

from __future__ import annotations

import flet as ft


def test_widgets_import() -> None:
    """Widgets module imports without error."""
    from plymotion.ui.widgets import append_log, dropdown_options
    assert append_log is not None
    assert dropdown_options is not None


def test_app_import() -> None:
    """App module imports without error."""
    from plymotion.ui.app import main, run
    assert main is not None
    assert run is not None


def test_dropdown_options() -> None:
    """dropdown_options builds one DropdownOption per value, keyed by itself."""
    from plymotion.ui.widgets import dropdown_options

    options = dropdown_options(["a", "b", "c"])
    assert [o.key for o in options] == ["a", "b", "c"]
    assert [o.text for o in options] == ["a", "b", "c"]


def test_append_log() -> None:
    """append_log adds one Text control per call, in order."""
    from plymotion.ui.widgets import append_log

    log_view = ft.ListView()
    append_log(log_view, "first")
    append_log(log_view, "second")

    assert len(log_view.controls) == 2
    assert log_view.controls[0].value == "first"
    assert log_view.controls[1].value == "second"
