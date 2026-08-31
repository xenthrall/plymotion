"""Process and optimize PNG frames for boot splash use."""

from __future__ import annotations

from pathlib import Path

from PIL import Image


def optimize_frames(
    frames_dir: Path,
    resolution: tuple[int, int],
) -> int:
    """Resize and optimize all PNG frames in a directory. Returns count."""
    target_w, target_h = resolution
    frames = sorted(frames_dir.glob("frame*.png"))

    for frame_path in frames:
        img = Image.open(frame_path)
        img = img.convert("RGB")

        # Maintain aspect ratio, fit within target
        img.thumbnail((target_w, target_h), Image.Resampling.LANCZOS)

        # Center on target canvas (black background)
        canvas = Image.new("RGB", (target_w, target_h), (0, 0, 0))
        offset_x = (target_w - img.width) // 2
        offset_y = (target_h - img.height) // 2
        canvas.paste(img, (offset_x, offset_y))

        canvas.save(
            frame_path,
            "PNG",
            optimize=True,
            compress_level=9,
        )

    return len(frames)
