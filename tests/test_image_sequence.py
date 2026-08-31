"""Tests for image_sequence module (images -> video/GIF)."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

import pytest
from PIL import Image

import plymotion.image_sequence as image_sequence
from plymotion.image_sequence import build_video_from_images, unique_output_path


class _FakeRun:
    """Captures every ffmpeg invocation without executing anything."""

    def __init__(self, returncode: int = 0, stderr: str = "") -> None:
        self.returncode = returncode
        self.stderr = stderr
        self.calls: list[list[str]] = []

    def __call__(self, argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        self.calls.append(argv)
        return subprocess.CompletedProcess(argv, self.returncode, stdout="", stderr=self.stderr)


def _make_images(tmp_path: Path, count: int) -> list[Path]:
    paths = []
    for i in range(count):
        p = tmp_path / f"src{i}.png"
        Image.new("RGB", (64, 48), (i * 10 % 255, 0, 0)).save(p)
        paths.append(p)
    return paths


def test_unique_output_path_avoids_collisions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    restored_dir = tmp_path / "restored"
    monkeypatch.setattr(image_sequence, "RESTORED_DIR", restored_dir)

    first = unique_output_path("My Video", ".mp4")
    first.parent.mkdir(parents=True, exist_ok=True)
    first.write_bytes(b"")
    second = unique_output_path("My Video", ".mp4")

    assert first.name == "my-video.mp4"
    assert second.name == "my-video-2.mp4"


def test_build_video_from_images_raises_without_images(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        build_video_from_images([], tmp_path / "out.mp4")


def test_build_video_from_images_raises_without_ffmpeg(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(image_sequence, "ffmpeg_available", lambda: False)
    images = _make_images(tmp_path, 2)

    with pytest.raises(FileNotFoundError):
        build_video_from_images(images, tmp_path / "out.mp4")


def test_build_video_from_images_mp4_single_ffmpeg_call(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_run = _FakeRun()
    monkeypatch.setattr(image_sequence, "ffmpeg_available", lambda: True)
    monkeypatch.setattr(image_sequence.subprocess, "run", fake_run)
    images = _make_images(tmp_path, 3)
    output = tmp_path / "out.mp4"

    result = build_video_from_images(images, output, fps=15)

    assert result == output
    assert len(fake_run.calls) == 1
    argv = fake_run.calls[0]
    assert argv[0] == "ffmpeg"
    assert "-framerate" in argv and "15" in argv
    assert "libx264" in argv


def test_build_video_from_images_gif_two_pass(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """GIF output goes through a palettegen pass, then a paletteuse pass."""
    fake_run = _FakeRun()
    monkeypatch.setattr(image_sequence, "ffmpeg_available", lambda: True)
    monkeypatch.setattr(image_sequence.subprocess, "run", fake_run)
    images = _make_images(tmp_path, 3)
    output = tmp_path / "out.gif"

    build_video_from_images(images, output, fps=12, max_width=240)

    assert len(fake_run.calls) == 2
    palette_call, final_call = fake_run.calls
    assert "palettegen" in " ".join(palette_call)
    assert "paletteuse" in " ".join(final_call)
    assert "240" in " ".join(palette_call)


def test_build_video_from_images_raises_on_ffmpeg_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_run = _FakeRun(returncode=1, stderr="invalid argument")
    monkeypatch.setattr(image_sequence, "ffmpeg_available", lambda: True)
    monkeypatch.setattr(image_sequence.subprocess, "run", fake_run)
    images = _make_images(tmp_path, 2)

    with pytest.raises(RuntimeError, match="invalid argument"):
        build_video_from_images(images, tmp_path / "out.mp4")
