"""Tests for frame_processor module."""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from plymotion.frame_processor import optimize_frames


def test_optimize_frames(tmp_path: Path) -> None:
    """Frames are resized to target resolution."""
    # Create test images at different sizes
    for i in range(3):
        img = Image.new("RGB", (800 + i * 100, 600 + i * 50), (i * 80, 100, 200))
        img.save(tmp_path / f"frame{i + 1}.png")

    count = optimize_frames(tmp_path, (1920, 1080))
    assert count == 3

    # Verify all frames are now 1920x1080
    for i in range(3):
        img = Image.open(tmp_path / f"frame{i + 1}.png")
        assert img.size == (1920, 1080)
        img.close()


def test_optimize_frames_maintains_aspect_ratio(tmp_path: Path) -> None:
    """Non-standard aspect ratios are centered on black canvas."""
    img = Image.new("RGB", (640, 480), (255, 128, 0))
    img.save(tmp_path / "frame1.png")

    optimize_frames(tmp_path, (1920, 1080))

    result = Image.open(tmp_path / "frame1.png")
    assert result.size == (1920, 1080)
    # Check that center has the original color
    pixel = result.getpixel((960, 540))
    assert pixel == (255, 128, 0)
    result.close()


def test_optimize_frames_empty(tmp_path: Path) -> None:
    """Empty directory returns 0."""
    count = optimize_frames(tmp_path, (1920, 1080))
    assert count == 0
