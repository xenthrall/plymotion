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

    def fake_extract_frames(video_path: Path, output_dir: Path, fps: int = 30) -> int:
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

    script = (output_dir / "mytheme-plymouth.script").read_text()
    assert "/usr/share/plymouth/themes/mytheme/frame" in script


def test_convert_respects_custom_image_dir(tmp_path: Path) -> None:
    """--image-dir overrides the default ImageDir written into the theme."""
    video = tmp_path / "input.mp4"
    video.write_bytes(b"fake")
    output_dir = tmp_path / "out"

    result = runner.invoke(
        app,
        ["convert", "-i", str(video), "-o", str(output_dir), "--image-dir", "/opt/custom"],
    )

    assert result.exit_code == 0, result.output
    script = (output_dir / "plymotion-plymouth.script").read_text()
    assert "/opt/custom/frame" in script
