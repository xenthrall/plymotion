"""Extract frames from video files using ffmpeg."""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
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


@dataclass(frozen=True)
class VideoInfo:
    width: int
    height: int
    duration: float
    fps: float | None
    codec: str
    size_bytes: int


def _parse_rate(rate: str | None) -> float | None:
    """ffprobe frame rates come as fractions like "30000/1001"."""
    if not rate or rate == "0/0":
        return None
    num, _, den = rate.partition("/")
    try:
        value = float(num) / float(den or 1)
    except (ValueError, ZeroDivisionError):
        return None
    return round(value, 3) if value > 0 else None


def get_video_info(video_path: Path) -> VideoInfo:
    """Get video dimensions, duration and frame rate using ffprobe.

    Duration falls back to the container's when the stream doesn't carry
    one, which is the usual case for animated GIFs and WebM.
    """
    cmd = [
        "ffprobe",
        "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height,duration,avg_frame_rate,r_frame_rate,codec_name"
        ":format=duration",
        "-of", "json",
        str(video_path),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed:\n{result.stderr}")

    data = json.loads(result.stdout)
    streams = data.get("streams") or []
    if not streams:
        raise RuntimeError("The file has no video stream.")
    stream = streams[0]
    duration = stream.get("duration") or data.get("format", {}).get("duration") or 0
    return VideoInfo(
        width=int(stream.get("width", 0)),
        height=int(stream.get("height", 0)),
        duration=float(duration),
        fps=_parse_rate(stream.get("avg_frame_rate")) or _parse_rate(stream.get("r_frame_rate")),
        codec=str(stream.get("codec_name", "")),
        size_bytes=video_path.stat().st_size,
    )
