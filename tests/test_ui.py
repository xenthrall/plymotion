"""Tests for the Flet UI module."""

from __future__ import annotations

from pathlib import Path

import flet as ft
import pytest


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
    from plymotion.ui.widgets import build_preview_gif, theme_card

    assert AppContext is not None
    assert theme_card is not None
    assert build_preview_gif is not None
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


def _make_frames(tmp_path: Path, count: int) -> list[Path]:
    from PIL import Image as PILImage

    frames = []
    for i in range(count):
        p = tmp_path / f"frame{i}.png"
        PILImage.new("RGB", (16, 12), (i * 20 % 255, 0, 0)).save(p)
        frames.append(p)
    return frames


def test_build_preview_gif_produces_animated_gif(tmp_path: Path) -> None:
    """The result is a real multi-frame GIF, one frame per input PNG, that
    Flet's Image control can animate natively (client-side) once set as src
    — no background thread or repeated control.update() needed."""
    import io

    from PIL import Image as PILImage

    from plymotion.ui.widgets import build_preview_gif

    frames = _make_frames(tmp_path, 5)
    gif_bytes = build_preview_gif(frames, fps=10)

    assert gif_bytes[:6] in (b"GIF87a", b"GIF89a")
    with PILImage.open(io.BytesIO(gif_bytes)) as gif:
        assert gif.is_animated
        assert gif.n_frames == 5


def test_build_preview_gif_loops_forever(tmp_path: Path) -> None:
    """loop=0 in the GIF header means infinite looping, matching how the
    real Plymouth splash loops."""
    import io

    from PIL import Image as PILImage

    from plymotion.ui.widgets import build_preview_gif

    frames = _make_frames(tmp_path, 3)
    gif_bytes = build_preview_gif(frames, fps=10)

    with PILImage.open(io.BytesIO(gif_bytes)) as gif:
        assert gif.info.get("loop") == 0


def test_build_preview_gif_rejects_empty_frame_list() -> None:
    from plymotion.ui.widgets import build_preview_gif

    with pytest.raises(ValueError):
        build_preview_gif([])
