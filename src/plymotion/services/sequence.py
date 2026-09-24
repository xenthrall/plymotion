"""Image sequence -> video/GIF ("Restaurar")."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from plymotion.core import image_sequence
from plymotion.core.sorting import natural_sort_key
from plymotion.services.progress import NullReporter, Reporter

IMAGE_EXTENSIONS = ["png", "jpg", "jpeg", "webp", "bmp"]
OUTPUT_FORMATS = {"mp4": ".mp4", "gif": ".gif"}


@dataclass(frozen=True)
class SequenceOptions:
    images: list[Path]
    name: str
    output_format: str = "mp4"
    fps: int = 24
    max_width: int | None = None

    def validate(self) -> None:
        if not self.images:
            raise ValueError("Selecciona al menos una imagen.")
        missing = [str(p) for p in self.images if not p.is_file()]
        if missing:
            raise ValueError(f"No existen: {', '.join(missing[:3])}")
        if self.output_format not in OUTPUT_FORMATS:
            raise ValueError("Formato de salida inválido (mp4 o gif).")
        if not 1 <= self.fps <= 120:
            raise ValueError("FPS fuera de rango (1-120).")
        if self.max_width is not None and not 16 <= self.max_width <= 7680:
            raise ValueError("Ancho máximo fuera de rango (16-7680).")


def build(opts: SequenceOptions, reporter: Reporter | None = None) -> Path:
    rep = reporter or NullReporter()
    opts.validate()
    images = sorted(opts.images, key=natural_sort_key)
    output = image_sequence.unique_output_path(opts.name, OUTPUT_FORMATS[opts.output_format])
    rep.progress(None, f"Generando {opts.output_format.upper()} con ffmpeg")
    rep.log(f"{len(images)} imágenes a {opts.fps} fps -> {output.name}")
    image_sequence.build_video_from_images(images, output, fps=opts.fps, max_width=opts.max_width)
    rep.log(f"Guardado en {output}")
    rep.progress(100, "Listo")
    return output


def list_outputs() -> list[Path]:
    directory = image_sequence.RESTORED_DIR
    if not directory.is_dir():
        return []
    files = [p for p in directory.iterdir() if p.suffix in OUTPUT_FORMATS.values()]
    return sorted(files, key=lambda p: p.stat().st_mtime, reverse=True)


def output_path(filename: str) -> Path | None:
    """A restored output by bare filename; None for anything else."""
    if "/" in filename or filename.startswith("."):
        return None
    path = image_sequence.RESTORED_DIR / filename
    return path if path.is_file() and path.suffix in OUTPUT_FORMATS.values() else None
