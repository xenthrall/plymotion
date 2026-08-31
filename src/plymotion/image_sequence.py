"""Build a video or GIF from a sequence of still images (the reverse of
video_extractor.extract_frames): load a picked set of images, get a video
back out that can then be fed into the normal convert flow.
"""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from PIL import Image

from plymotion import library
from plymotion.video_extractor import ffmpeg_available

RESTORED_DIR = library.LIBRARY_DIR / "restored"


def unique_output_path(name: str, extension: str) -> Path:
    """A path under RESTORED_DIR for `name` + `extension` that won't overwrite
    an existing file, following the same "-2, -3, ..." pattern as
    library.unique_slug()."""
    RESTORED_DIR.mkdir(parents=True, exist_ok=True)
    base = library.slugify(name)
    candidate = base
    n = 2
    while (RESTORED_DIR / f"{candidate}{extension}").exists():
        candidate = f"{base}-{n}"
        n += 1
    return RESTORED_DIR / f"{candidate}{extension}"


def build_video_from_images(
    image_paths: list[Path],
    output_path: Path,
    fps: int = 24,
    max_width: int | None = None,
) -> Path:
    """Assemble `image_paths`, in the given order, into a video or GIF.

    The output format is picked from `output_path`'s extension (.gif, or
    any ffmpeg-supported video container otherwise). Images are normalized
    to sequentially-numbered PNGs in a temp dir first, so mixed source
    formats and an arbitrary picker order both just work — caller is
    responsible for sorting `image_paths` into the desired order first
    (e.g. with plymotion.sorting.natural_sort_key).
    """
    if not image_paths:
        raise ValueError("No images provided.")
    if not ffmpeg_available():
        raise FileNotFoundError("ffmpeg not found. Install it: sudo apt install ffmpeg")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="plymotion-sequence-") as tmp:
        tmp_dir = Path(tmp)
        for i, src in enumerate(image_paths, start=1):
            with Image.open(src) as img:
                img.convert("RGB").save(tmp_dir / f"frame{i}.png")

        pattern = str(tmp_dir / "frame%d.png")
        if output_path.suffix.lower() == ".gif":
            _build_gif(pattern, fps, max_width, output_path)
        else:
            _build_video(pattern, fps, max_width, output_path)

    return output_path


def _scale_filter(max_width: int | None) -> str:
    if max_width is not None:
        # -2 keeps the height even (required by libx264) while preserving
        # aspect ratio at the given width.
        return f"scale={max_width}:-2:flags=lanczos"
    # No target width: still need even width/height for libx264, in case a
    # source image had an odd dimension.
    return "scale=trunc(iw/2)*2:trunc(ih/2)*2"


def _build_video(pattern: str, fps: int, max_width: int | None, output_path: Path) -> None:
    cmd = [
        "ffmpeg", "-y", "-framerate", str(fps), "-i", pattern,
        "-vf", _scale_filter(max_width),
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        str(output_path),
    ]
    _run(cmd)


def _build_gif(pattern: str, fps: int, max_width: int | None, output_path: Path) -> None:
    scale = _scale_filter(max_width or 480)
    with tempfile.TemporaryDirectory(prefix="plymotion-palette-") as tmp:
        palette = Path(tmp) / "palette.png"
        _run([
            "ffmpeg", "-y", "-framerate", str(fps), "-i", pattern,
            "-vf", f"fps={fps},{scale},palettegen",
            str(palette),
        ])
        _run([
            "ffmpeg", "-y", "-framerate", str(fps), "-i", pattern, "-i", str(palette),
            "-lavfi", f"fps={fps},{scale}[x];[x][1:v]paletteuse",
            str(output_path),
        ])


def _run(cmd: list[str]) -> None:
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed:\n{result.stderr}")
