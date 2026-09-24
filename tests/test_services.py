"""Tests for the plymotion.services layer."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from PIL import Image

import plymotion.core.library as library
import plymotion.services.convert as convert
from plymotion.services import login_logo as logo_service
from plymotion.services import sequence, themes
from plymotion.services.progress import Cancelled


class RecordingReporter:
    def __init__(self, cancel_after: int | None = None) -> None:
        self.events: list[tuple[float | None, str | None]] = []
        self.lines: list[str] = []
        self.checks = 0
        self.cancel_after = cancel_after

    def progress(self, percent: float | None, stage: str | None = None) -> None:
        self.events.append((percent, stage))

    def log(self, message: str) -> None:
        self.lines.append(message)

    def check_cancelled(self) -> None:
        self.checks += 1
        if self.cancel_after is not None and self.checks > self.cancel_after:
            raise Cancelled()


@pytest.fixture
def library_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    themes_dir = tmp_path / "themes"
    monkeypatch.setattr(library, "LIBRARY_THEMES_DIR", themes_dir)
    return themes_dir


def _fake_extract(frames: int) -> Any:
    def fake(video: Path, out_dir: Path, **_kwargs: Any) -> int:
        out_dir.mkdir(parents=True, exist_ok=True)
        for i in range(1, frames + 1):
            Image.new("RGB", (64, 48), (i * 10 % 255, 0, 0)).save(out_dir / f"frame{i}.png")
        return frames

    return fake


def _video(tmp_path: Path) -> Path:
    video = tmp_path / "clip.mp4"
    video.write_bytes(b"fake")
    return video


def test_convert_creates_library_theme(
    tmp_path: Path, library_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(convert, "extract_frames", _fake_extract(12))
    reporter = RecordingReporter()

    theme = convert.convert_video(
        convert.ConvertOptions(video=_video(tmp_path), name="Mi Tema", max_width=32, max_height=24),
        reporter,
    )

    assert theme.slug == "mi-tema"
    assert theme.frame_count == 12
    assert (library_dir / "mi-tema" / "mi-tema.plymouth").is_file()
    assert (library_dir / "mi-tema" / "mi-tema.script").is_file()
    assert theme.total_bytes > 0
    assert reporter.events[-1] == (100, "Listo")
    with Image.open(library_dir / "mi-tema" / "frame1.png") as img:
        assert img.size[0] <= 32


def test_convert_cancel_removes_partial_theme(
    tmp_path: Path, library_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(convert, "extract_frames", _fake_extract(5))

    with pytest.raises(Cancelled):
        convert.convert_video(
            convert.ConvertOptions(video=_video(tmp_path), name="x"),
            RecordingReporter(cancel_after=2),
        )

    assert not (library_dir / "x").exists()


def test_convert_rejects_bad_options(tmp_path: Path, library_dir: Path) -> None:
    with pytest.raises(ValueError, match="no existe"):
        convert.convert_video(convert.ConvertOptions(video=tmp_path / "nope.mp4", name="x"))
    with pytest.raises(ValueError, match="FPS"):
        convert.convert_video(convert.ConvertOptions(video=_video(tmp_path), name="x", fps=0))


def test_estimate_respects_trim() -> None:
    est = convert.estimate(duration=10, fps=30, trim_start=2, trim_duration=3)
    assert est.frame_count == 90
    assert est.loop_seconds == pytest.approx(1.8)

    clipped = convert.estimate(duration=10, fps=10, trim_start=8, trim_duration=5)
    assert clipped.frame_count == 20


def test_frame_path_bounds(tmp_path: Path) -> None:
    for i in (1, 2, 10):
        (tmp_path / f"frame{i}.png").write_bytes(b"")
    assert themes.frame_path(tmp_path, 3).name == "frame10.png"
    with pytest.raises(themes.NotFound):
        themes.frame_path(tmp_path, 4)


def test_installed_theme_dir_refuses_traversal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import plymotion.core.installer as installer

    (tmp_path / "themes" / "spinner").mkdir(parents=True)
    monkeypatch.setattr(installer, "THEMES_DIR", tmp_path / "themes")
    assert themes.installed_theme_dir("spinner").name == "spinner"
    with pytest.raises(themes.NotFound):
        themes.installed_theme_dir("../../etc")


def test_require_library_theme_rejects_bad_slug(library_dir: Path) -> None:
    with pytest.raises(themes.NotFound):
        themes.require_library_theme("../secret")


def test_logo_preview_is_cached_and_sized(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(logo_service, "PREVIEW_DIR", tmp_path / "previews")
    source = tmp_path / "logo.png"
    Image.new("RGBA", (400, 200)).save(source)

    preview = logo_service.make_preview(source, max_height=50)

    assert (preview.width, preview.height) == (100, 50)
    assert logo_service.preview_path(preview.id) == preview.path
    assert logo_service.preview_path("../x") is None


def test_sequence_output_path_rejects_traversal() -> None:
    assert sequence.output_path("../prefs.json") is None
    assert sequence.output_path("missing.mp4") is None


def test_sequence_validate() -> None:
    with pytest.raises(ValueError, match="al menos una"):
        sequence.SequenceOptions(images=[], name="x").validate()
