"""Tests for video_extractor module."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

import pytest

import plymotion.video_extractor as video_extractor
from plymotion.video_extractor import extract_frames


class _FakeRun:
    """Captures the argv passed to subprocess.run, without executing anything."""

    def __init__(self, returncode: int = 0, stderr: str = "") -> None:
        self.returncode = returncode
        self.stderr = stderr
        self.calls: list[list[str]] = []

    def __call__(self, argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        self.calls.append(argv)
        return subprocess.CompletedProcess(argv, self.returncode, stdout="", stderr=self.stderr)

    @property
    def last(self) -> list[str]:
        assert self.calls
        return self.calls[-1]


def test_extract_frames_no_trim_by_default(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Without start_time/duration, ffmpeg gets no -ss/-t flags."""
    fake_run = _FakeRun()
    monkeypatch.setattr(video_extractor, "ffmpeg_available", lambda: True)
    monkeypatch.setattr(video_extractor.subprocess, "run", fake_run)

    video = tmp_path / "input.mp4"
    out_dir = tmp_path / "out"

    extract_frames(video, out_dir, fps=24)

    argv = fake_run.last
    assert argv[0] == "ffmpeg"
    assert "-ss" not in argv
    assert "-t" not in argv
    assert argv[argv.index("-i") + 1] == str(video)
    assert "fps=24" in argv


def test_extract_frames_applies_trim(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """start_time becomes input-side -ss, duration becomes -t after -i."""
    fake_run = _FakeRun()
    monkeypatch.setattr(video_extractor, "ffmpeg_available", lambda: True)
    monkeypatch.setattr(video_extractor.subprocess, "run", fake_run)

    video = tmp_path / "input.gif"
    out_dir = tmp_path / "out"

    extract_frames(video, out_dir, fps=30, start_time=2.5, duration=8.0)

    argv = fake_run.last
    i_index = argv.index("-i")
    ss_index = argv.index("-ss")
    t_index = argv.index("-t")

    assert ss_index < i_index, "-ss must be applied on the input side (before -i)"
    assert t_index > i_index, "-t must come after -i"
    assert argv[ss_index + 1] == "2.5"
    assert argv[t_index + 1] == "8.0"


def test_extract_frames_zero_start_time_omits_ss(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """start_time=0.0 (the default) does not add a no-op -ss flag."""
    fake_run = _FakeRun()
    monkeypatch.setattr(video_extractor, "ffmpeg_available", lambda: True)
    monkeypatch.setattr(video_extractor.subprocess, "run", fake_run)

    extract_frames(tmp_path / "input.mp4", tmp_path / "out", start_time=0.0, duration=5.0)

    argv = fake_run.last
    assert "-ss" not in argv
    assert "-t" in argv


def test_extract_frames_raises_without_ffmpeg(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A missing ffmpeg binary is reported clearly instead of failing inside subprocess."""
    monkeypatch.setattr(video_extractor, "ffmpeg_available", lambda: False)

    with pytest.raises(FileNotFoundError):
        extract_frames(tmp_path / "input.mp4", tmp_path / "out")


def test_extract_frames_raises_on_ffmpeg_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A non-zero ffmpeg exit code surfaces stderr in the raised error."""
    fake_run = _FakeRun(returncode=1, stderr="invalid data found")
    monkeypatch.setattr(video_extractor, "ffmpeg_available", lambda: True)
    monkeypatch.setattr(video_extractor.subprocess, "run", fake_run)

    with pytest.raises(RuntimeError, match="invalid data found"):
        extract_frames(tmp_path / "input.mp4", tmp_path / "out")
