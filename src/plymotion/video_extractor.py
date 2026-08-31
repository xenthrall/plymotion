"""Extract frames from video files using ffmpeg."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


def ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


def extract_frames(
    video_path: Path,
    output_dir: Path,
    fps: int = 30,
    start_time: float = 0.0,
    duration: float | None = None,
) -> int:
    """Extract frames from a video or animated GIF as PNG files.

    `start_time`/`duration` trim the source before extraction (in seconds).
    ffmpeg decodes GIF the same way as any other video container, so no
    format-specific handling is needed here.

    Returns frame count.
    """
    if not ffmpeg_available():
        raise FileNotFoundError(
            "ffmpeg not found. Install it: sudo apt install ffmpeg"
        )

    output_dir.mkdir(parents=True, exist_ok=True)

    cmd = ["ffmpeg"]
    if start_time > 0:
        # Input seeking (-ss before -i): fast, keyframe-based, plenty
        # accurate for trimming a boot splash clip.
        cmd += ["-ss", str(start_time)]
    cmd += ["-i", str(video_path)]
    if duration is not None:
        cmd += ["-t", str(duration)]
    cmd += [
        "-vf", f"fps={fps}",
        "-pix_fmt", "rgb24",
        str(output_dir / "frame%d.png"),
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed:\n{result.stderr}")

    return len(list(output_dir.glob("frame*.png")))


def get_video_info(video_path: Path) -> dict[str, int]:
    """Get video width, height, and duration using ffprobe."""
    cmd = [
        "ffprobe",
        "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height,duration",
        "-of", "json",
        str(video_path),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed:\n{result.stderr}")

    import json
    data = json.loads(result.stdout)
    stream = data["streams"][0]
    return {
        "width": int(stream.get("width", 1920)),
        "height": int(stream.get("height", 1080)),
        "duration": int(float(stream.get("duration", 0))),
    }
