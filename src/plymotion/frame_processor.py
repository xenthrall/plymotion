"""Process and optimize PNG frames for boot splash use."""

from __future__ import annotations

from pathlib import Path

from PIL import Image

DEFAULT_COLORS = 64


def optimize_frames(
    frames_dir: Path,
    max_size: tuple[int, int],
    colors: int = DEFAULT_COLORS,
) -> int:
    """Resize and optimize all PNG frames in a directory. Returns count.

    Frames are scaled to fit within `max_size` (aspect ratio preserved) and
    quantized to an indexed palette of at most `colors` colors before being
    saved back as PNG.

    Two things keep boot-splash frames small:
    - No padding to a fixed canvas: Plymouth centers the sprite itself via
      Window.GetWidth()/GetHeight() at boot time (see template_generator's
      generated script), so pasting onto a black canvas the size of the
      whole screen just adds dead weight, especially for a video that
      already matches the target aspect ratio (then max_size does nothing
      but the source stays at full, expensive-to-compress resolution).
    - A quantized (indexed) palette: PNG compresses a handful of flat
      colors far better than 24-bit truecolor gradients from real video
      footage, which is the dominant factor in frame size once resolution
      is reasonable. Undithered, since dithering trades file size for a
      smoother gradient look, and small size is the priority here.

    Note on `optimize=True`: benchmarking showed it costs 2-4x the encode
    time for a size gain typically well under 5%, so it's deliberately
    left off — compress_level=9 alone gets nearly all of the size benefit.
    """
    max_w, max_h = max_size
    frames = sorted(frames_dir.glob("frame*.png"))

    for frame_path in frames:
        img = Image.open(frame_path)
        img = img.convert("RGB")
        img.thumbnail((max_w, max_h), Image.Resampling.LANCZOS)
        quantized = img.quantize(
            colors=colors,
            method=Image.Quantize.FASTOCTREE,
            dither=Image.Dither.NONE,
        )
        quantized.save(
            frame_path,
            "PNG",
            optimize=False,
            compress_level=9,
        )

    return len(frames)
