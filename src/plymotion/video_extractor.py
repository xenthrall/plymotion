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
) -> int:
    """Extract frames from video as PNG files. Returns frame count."""
    if not ffmpeg_available():
        raise FileNotFoundError(
            "ffmpeg not found. Install it: sudo apt install ffmpeg"
        )

    output_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        "ffmpeg",
        "-i", str(video_path),
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
