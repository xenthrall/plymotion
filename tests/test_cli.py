"""Tests for CLI module."""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image
from typer.testing import CliRunner

from plymotion.cli import app

runner = CliRunner()


@pytest.fixture(autouse=True)
def _stub_extract_frames(monkeypatch: pytest.MonkeyPatch) -> None:
    """Replace ffmpeg-backed extraction with a PIL-only stub for fast, offline tests."""

    def fake_extract_frames(
        video_path: Path,
        output_dir: Path,
        fps: int = 30,
        start_time: float = 0.0,
        duration: float | None = None,
    ) -> int:
        output_dir.mkdir(parents=True, exist_ok=True)
        for i in range(1, 4):
            Image.new("RGB", (320, 240), (i * 10, 0, 0)).save(output_dir / f"frame{i}.png")
        return 3

    monkeypatch.setattr("plymotion.video_extractor.extract_frames", fake_extract_frames)


def test_help() -> None:
    """CLI shows help text."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Plymouth boot splash" in result.output


def test_version() -> None:
    """CLI shows version."""
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.output


def test_convert_no_video_shows_error() -> None:
    """Convert command requires video input."""
    result = runner.invoke(app, ["convert"])
    assert result.exit_code != 0


def test_convert_flat_layout_and_default_image_dir(tmp_path: Path) -> None:
    """Frames land next to the theme files (no frames/ subdir), matching ImageDir."""
    video = tmp_path / "input.mp4"
    video.write_bytes(b"fake")
    output_dir = tmp_path / "out"

    result = runner.invoke(
        app,
        ["convert", "-i", str(video), "-o", str(output_dir), "-t", "mytheme"],
    )

    assert result.exit_code == 0, result.output
    assert not (output_dir / "frames").exists()
    assert (output_dir / "frame1.png").is_file()

    # The .script references frames relative to ImageDir ("/frameN.png"),
    # not a baked-in absolute path; ImageDir itself lives in the .plymouth.
    script = (output_dir / "mytheme-plymouth.script").read_text()
    assert '"/frame" + (i + 1) + ".png"' in script

    plymouth = (output_dir / "mytheme-plymouth.plymouth").read_text()
    assert "ImageDir=/usr/share/plymouth/themes/mytheme" in plymouth


def test_convert_passes_trim_options(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """--trim-start/--trim-duration reach extract_frames as start_time/duration."""
    calls: list[dict[str, object]] = []

    def capturing_extract_frames(
        video_path: Path,
        output_dir: Path,
        fps: int = 30,
        start_time: float = 0.0,
        duration: float | None = None,
    ) -> int:
        calls.append({"start_time": start_time, "duration": duration})
        output_dir.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (320, 240)).save(output_dir / "frame1.png")
        return 1

    monkeypatch.setattr("plymotion.video_extractor.extract_frames", capturing_extract_frames)

    video = tmp_path / "input.mp4"
    video.write_bytes(b"fake")
    output_dir = tmp_path / "out"

    result = runner.invoke(
        app,
        [
            "convert", "-i", str(video), "-o", str(output_dir),
            "--trim-start", "2.5", "--trim-duration", "8",
        ],
    )

    assert result.exit_code == 0, result.output
    assert calls == [{"start_time": 2.5, "duration": 8.0}]
    assert "Loop duration on screen" in result.output


def test_convert_fullscreen_flag_scales_frames_in_script(tmp_path: Path) -> None:
    """--fullscreen makes the generated .script scale frames to the screen size."""
    video = tmp_path / "input.mp4"
    video.write_bytes(b"fake")
    output_dir = tmp_path / "out"

    result = runner.invoke(
        app,
        ["convert", "-i", str(video), "-o", str(output_dir), "--fullscreen"],
    )

    assert result.exit_code == 0, result.output
    script = (output_dir / "plymotion-plymouth.script").read_text()
    assert "Scale(screen_w, screen_h)" in script


def test_convert_without_fullscreen_flag_does_not_scale(tmp_path: Path) -> None:
    """Without --fullscreen, the .script keeps the centered, unscaled behavior."""
    video = tmp_path / "input.mp4"
    video.write_bytes(b"fake")
    output_dir = tmp_path / "out"

    result = runner.invoke(app, ["convert", "-i", str(video), "-o", str(output_dir)])

    assert result.exit_code == 0, result.output
    script = (output_dir / "plymotion-plymouth.script").read_text()
    assert "Scale" not in script


def test_convert_respects_custom_image_dir(tmp_path: Path) -> None:
    """--image-dir overrides the default ImageDir written into the .plymouth config."""
    video = tmp_path / "input.mp4"
    video.write_bytes(b"fake")
    output_dir = tmp_path / "out"

    result = runner.invoke(
        app,
        ["convert", "-i", str(video), "-o", str(output_dir), "--image-dir", "/opt/custom"],
    )

    assert result.exit_code == 0, result.output
    plymouth = (output_dir / "plymotion-plymouth.plymouth").read_text()
    assert "ImageDir=/opt/custom" in plymouth
