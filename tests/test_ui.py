"""Tests for the Flet UI module."""

from __future__ import annotations

from pathlib import Path

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


def test_view_modules_import() -> None:
    """Each view module and its builder function import without error."""
    from plymotion.ui.views.convert_view import build_convert_view
    from plymotion.ui.views.gallery_view import build_gallery_view
    from plymotion.ui.views.restore_view import build_restore_view
    from plymotion.ui.views.system_view import build_system_view

    assert build_convert_view is not None
    assert build_gallery_view is not None
    assert build_system_view is not None
    assert build_restore_view is not None


def test_context_and_widgets_import() -> None:
    """Shared plumbing modules import without error."""
    from plymotion.ui.context import AppContext
    from plymotion.ui.os_utils import open_in_file_manager
    from plymotion.ui.widgets import animate_preview, theme_card

    assert AppContext is not None
    assert theme_card is not None
    assert animate_preview is not None
    assert open_in_file_manager is not None


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


class _FakeImage:
    """Duck-typed stand-in for ft.Image: tracks src changes and update() calls.

    animate_preview() only touches `.src` and `.update()`, so a real Flet
    control (which needs a live page/session to attach to) isn't needed.
    """

    def __init__(self) -> None:
        self.src: bytes | None = None
        self.update_calls = 0

    def update(self) -> None:
        self.update_calls += 1


def test_animate_preview_cycles_frames_via_control_update(tmp_path: Path) -> None:
    """Each frame change is pushed with image.update(), not a bare page.update()
    (a bare page.update() does not reach a control inside an open dialog)."""
    from plymotion.ui.widgets import animate_preview

    frames = []
    for i in range(3):
        p = tmp_path / f"frame{i}.png"
        p.write_bytes(f"frame-{i}".encode())
        frames.append(p)

    image = _FakeImage()
    animate_preview(image, frames, fps=1000, loops=2)  # type: ignore[arg-type]

    assert image.update_calls == len(frames) * 2
    assert image.src == frames[-1].read_bytes()


def test_animate_preview_stops_when_cancelled(tmp_path: Path) -> None:
    """is_cancelled() lets a closed dialog stop the loop instead of running to
    completion in the background."""
    from plymotion.ui.widgets import animate_preview

    frames = []
    for i in range(5):
        p = tmp_path / f"frame{i}.png"
        p.write_bytes(b"x")
        frames.append(p)

    image = _FakeImage()
    seen = {"count": 0}

    def is_cancelled() -> bool:
        seen["count"] += 1
        return seen["count"] > 2

    animate_preview(image, frames, fps=1000, loops=10, is_cancelled=is_cancelled)  # type: ignore[arg-type]

    assert image.update_calls == 2


def test_animate_preview_stops_gracefully_if_control_detached(tmp_path: Path) -> None:
    """If the control's update() raises RuntimeError (detached from the page,
    e.g. the dialog was closed), the loop stops instead of crashing the
    background thread."""
    from plymotion.ui.widgets import animate_preview

    class _DetachedImage(_FakeImage):
        def update(self) -> None:
            raise RuntimeError("Control must be added to the page first")

    frames = [tmp_path / "frame0.png"]
    frames[0].write_bytes(b"x")

    animate_preview(_DetachedImage(), frames, fps=1000, loops=5)  # type: ignore[arg-type]
    # No exception raised is the assertion here.
