"""Tests for frame_processor module."""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from plymotion.frame_processor import optimize_frames


def test_optimize_frames_fits_within_max_size(tmp_path: Path) -> None:
    """Frames are scaled down to fit within max_size, no padding to a fixed canvas."""
    for i in range(3):
        img = Image.new("RGB", (800 + i * 100, 600 + i * 50), (i * 80, 100, 200))
        img.save(tmp_path / f"frame{i + 1}.png")

    count = optimize_frames(tmp_path, (400, 300))
    assert count == 3

    for i in range(3):
        img = Image.open(tmp_path / f"frame{i + 1}.png")
        assert img.width <= 400
        assert img.height <= 300
        img.close()


def test_optimize_frames_does_not_pad_smaller_images(tmp_path: Path) -> None:
    """An image already smaller than max_size is left at its own size, not
    padded up to a fixed canvas — Plymouth centers the sprite itself."""
    img = Image.new("RGB", (640, 480), (255, 128, 0))
    img.save(tmp_path / "frame1.png")

    optimize_frames(tmp_path, (1920, 1080))

    result = Image.open(tmp_path / "frame1.png")
    assert result.size == (640, 480)
    result.close()


def test_optimize_frames_reduces_palette(tmp_path: Path) -> None:
    """The saved PNG uses an indexed palette of at most `colors` colors."""
    img = Image.new("RGB", (200, 150))
    for x in range(200):
        for y in range(150):
            img.putpixel((x, y), (x % 256, y % 256, (x + y) % 256))
    img.save(tmp_path / "frame1.png")

    optimize_frames(tmp_path, (200, 150), colors=32)

    result = Image.open(tmp_path / "frame1.png")
    assert result.mode == "P"
    assert len(result.getcolors(maxcolors=256)) <= 32
    result.close()


def test_optimize_frames_shrinks_file_size_for_noisy_content(tmp_path: Path) -> None:
    """A noisy, photo-like frame ends up smaller after palette reduction.

    (A perfectly smooth mathematical gradient is a bad proxy here: it's
    already near-perfectly predictable for lossless PNG's filters/zlib, so
    quantizing it can even grow it. Real video frames have sensor noise and
    non-periodic detail that compress far worse as 24-bit truecolor — this
    generates a closer analogue with per-pixel randomness.)
    """
    import random

    rng = random.Random(0)
    img = Image.new("RGB", (480, 360))
    for x in range(480):
        for y in range(360):
            img.putpixel((x, y), (rng.randrange(256), rng.randrange(256), rng.randrange(256)))
    path = tmp_path / "frame1.png"
    img.save(path, "PNG")
    truecolor_size = path.stat().st_size

    optimize_frames(tmp_path, (480, 360), colors=64)

    assert path.stat().st_size < truecolor_size


def test_optimize_frames_empty(tmp_path: Path) -> None:
    """Empty directory returns 0."""
    count = optimize_frames(tmp_path, (1920, 1080))
    assert count == 0
