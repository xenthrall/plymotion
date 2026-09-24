"""GDM login logo use cases: previews for the client plus install/restore."""

from __future__ import annotations

import hashlib
import tempfile
from dataclasses import dataclass
from pathlib import Path

from plymotion.core import login_logo

PREVIEW_DIR = Path(tempfile.gettempdir()) / "plymotion-logo-previews"
IMAGE_EXTENSIONS = login_logo.SUPPORTED_EXTENSIONS


@dataclass(frozen=True)
class LogoPreview:
    id: str
    path: Path
    width: int
    height: int


def current_logo() -> tuple[Path | None, bool]:
    """(displayable path of the logo GDM shows now, whether it is Plymotion's)."""
    if login_logo.is_custom_logo_installed():
        return login_logo.previewable_path(login_logo.LOGO_INSTALL_PATH), True
    logo = login_logo.distro_default_logo()
    return (login_logo.previewable_path(logo) if logo else None), False


def make_preview(source: Path, max_height: int) -> LogoPreview:
    """Resize `source` exactly as install_logo() would, into a temp file the client can show."""
    if not source.is_file():
        raise ValueError(f"El archivo no existe: {source}")
    if source.suffix.lower().lstrip(".") not in IMAGE_EXTENSIONS:
        raise ValueError("Formato no soportado: usa PNG, JPG, WebP o BMP.")
    if not 16 <= max_height <= 400:
        raise ValueError("El alto máximo debe estar entre 16 y 400 px.")

    stat = source.stat()
    key = f"{source.resolve()}:{stat.st_mtime_ns}:{stat.st_size}:{max_height}"
    preview_id = hashlib.sha256(key.encode()).hexdigest()[:16]
    output = PREVIEW_DIR / f"{preview_id}.png"
    width, height = login_logo.prepare_logo(source, output, max_height=max_height)
    return LogoPreview(id=preview_id, path=output, width=width, height=height)


def preview_path(preview_id: str) -> Path | None:
    if not preview_id.isalnum():
        return None
    path = PREVIEW_DIR / f"{preview_id}.png"
    return path if path.is_file() else None
