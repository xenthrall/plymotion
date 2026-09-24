"""Video/GIF -> Plymouth theme in the local library."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from plymotion.core import library
from plymotion.core.frame_processor import DEFAULT_COLORS, optimize_frames
from plymotion.core.template_generator import (
    PLYMOUTH_DEFAULT_REFRESH_RATE,
    estimate_loop_seconds,
    generate_plymouth,
    generate_script,
)
from plymotion.core.video_extractor import extract_frames
from plymotion.services.progress import NullReporter, Reporter

VIDEO_EXTENSIONS = ["mp4", "mkv", "webm", "avi", "mov", "m4v", "gif"]


@dataclass(frozen=True)
class ConvertOptions:
    video: Path
    name: str
    max_width: int = 320
    max_height: int = 240
    fps: int = 30
    colors: int = DEFAULT_COLORS
    trim_start: float = 0.0
    trim_duration: float | None = None

    def validate(self) -> None:
        if not self.video.is_file():
            raise ValueError(f"El archivo no existe: {self.video}")
        if not self.name.strip():
            raise ValueError("El nombre del tema no puede estar vacío.")
        if not (16 <= self.max_width <= 7680 and 16 <= self.max_height <= 4320):
            raise ValueError("Resolución fuera de rango (16x16 a 7680x4320).")
        if not 1 <= self.fps <= 120:
            raise ValueError("FPS fuera de rango (1-120).")
        if not 2 <= self.colors <= 256:
            raise ValueError("Colores fuera de rango (2-256).")
        if self.trim_start < 0:
            raise ValueError("El inicio del recorte no puede ser negativo.")
        if self.trim_duration is not None and self.trim_duration <= 0:
            raise ValueError("La duración del recorte debe ser mayor que cero.")


@dataclass(frozen=True)
class ConvertEstimate:
    frame_count: int
    loop_seconds: float
    refresh_rate: int


def estimate(duration: float, fps: int, trim_start: float = 0.0,
             trim_duration: float | None = None) -> ConvertEstimate:
    """Frames the conversion will produce and how long one loop plays at boot.

    Plymouth replays one frame per refresh at a fixed rate, so a clip
    extracted at 30 fps plays back at 50/30 of its real speed.
    """
    remaining = max(duration - trim_start, 0.0)
    clip = min(trim_duration, remaining) if trim_duration is not None else remaining
    frame_count = max(int(round(clip * fps)), 0)
    return ConvertEstimate(
        frame_count=frame_count,
        loop_seconds=estimate_loop_seconds(frame_count),
        refresh_rate=PLYMOUTH_DEFAULT_REFRESH_RATE,
    )


def convert_video(opts: ConvertOptions, reporter: Reporter | None = None) -> library.LibraryTheme:
    """Extract, optimize and package `opts.video` as a new library theme.

    On failure or cancellation the half-written theme directory is removed,
    so the gallery never shows a broken entry.
    """
    rep = reporter or NullReporter()
    opts.validate()

    slug = library.unique_slug(opts.name)
    out_dir = library.LIBRARY_THEMES_DIR / slug
    try:
        # Frames are extracted directly into the theme dir (flat layout),
        # next to the .script/.plymouth files, so ImageDir can point
        # straight at the eventual installed theme directory.
        rep.progress(2, "Extrayendo frames")
        rep.log(f"Extrayendo frames de {opts.video.name} a {opts.fps} fps")
        frame_count = extract_frames(
            opts.video, out_dir, fps=opts.fps,
            start_time=opts.trim_start, duration=opts.trim_duration,
        )
        if frame_count == 0:
            raise RuntimeError(
                "ffmpeg no produjo ningún frame (¿el recorte está fuera del video?)."
            )
        rep.log(f"{frame_count} frames extraídos")
        rep.check_cancelled()

        def on_frame(done: int, total: int) -> None:
            rep.check_cancelled()
            if done == total or done % 10 == 0:
                rep.progress(30 + 60 * done / total, f"Optimizando frames ({done}/{total})")

        rep.progress(30, "Optimizando frames")
        optimize_frames(
            out_dir, (opts.max_width, opts.max_height), colors=opts.colors, on_progress=on_frame,
        )
        total_bytes = sum(f.stat().st_size for f in out_dir.glob("frame*.png"))
        avg_kb = total_bytes / frame_count / 1024
        rep.log(f"Frames optimizados: {opts.colors} colores, ~{avg_kb:.1f} KB por frame")

        rep.progress(92, "Generando archivos Plymouth")
        # Filenames MUST match the theme directory name (slug.plymouth, not
        # slug-plymouth.plymouth): Ubuntu/Debian's initramfs-tools plymouth
        # hook expects themes/<slug>/<slug>.plymouth and silently drops any
        # theme that doesn't match when baking the initramfs, which makes
        # the theme play fine on preview/shutdown (live filesystem) but
        # fall back to a text-mode error at real boot. See
        # installer.validate_theme().
        image_dir = f"/usr/share/plymouth/themes/{slug}"
        generate_script(out_dir / f"{slug}.script", frame_count)
        generate_plymouth(
            out_dir / f"{slug}.plymouth", opts.name, image_dir, f"{image_dir}/{slug}.script"
        )
        loop_seconds = estimate_loop_seconds(frame_count)
        library.save_manifest(
            out_dir,
            name=opts.name,
            frame_count=frame_count,
            resolution=[opts.max_width, opts.max_height],
            fps=opts.fps,
            colors=opts.colors,
            loop_seconds=loop_seconds,
            total_bytes=total_bytes,
            source_video=str(opts.video),
            trim_start=opts.trim_start,
            trim_duration=opts.trim_duration,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        rep.log(f"Tema '{opts.name}' guardado en la galería ({loop_seconds:.1f} s por loop)")
        rep.progress(100, "Listo")
    except BaseException:
        shutil.rmtree(out_dir, ignore_errors=True)
        raise

    theme = library.get_library_theme(slug)
    assert theme is not None
    return theme
