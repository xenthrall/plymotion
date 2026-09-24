"""Library and installed-system theme use cases."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from plymotion.core import installer, library
from plymotion.services.progress import NullReporter, Reporter


class NotFound(LookupError):
    """The requested theme, frame or file doesn't exist."""


def require_library_theme(slug: str) -> library.LibraryTheme:
    theme = library.get_library_theme(slug)
    if theme is None:
        raise NotFound(f"El tema '{slug}' no está en la galería.")
    return theme


def frame_path(theme_dir: Path, index: int) -> Path:
    """The `index`-th (1-based) frame of a theme, in playback order."""
    frames = library.sorted_frames(theme_dir)
    if not 1 <= index <= len(frames):
        raise NotFound(f"Frame {index} fuera de rango (1-{len(frames)}).")
    return frames[index - 1]


def installed_theme_dir(dir_name: str) -> Path:
    """Resolve an installed theme directory name, refusing anything outside THEMES_DIR."""
    candidate = (installer.THEMES_DIR / dir_name).resolve()
    if candidate.parent != installer.THEMES_DIR.resolve() or not candidate.is_dir():
        raise NotFound(f"El tema '{dir_name}' no está instalado.")
    return candidate


def installed_slugs() -> set[str]:
    """Directory names of installed themes, to mark library themes as installed."""
    return {theme.directory.name for theme in installer.list_installed_themes()}


def install_from_library(slug: str, reporter: Reporter | None = None) -> None:
    rep = reporter or NullReporter()
    theme = require_library_theme(slug)
    rep.progress(None, "Esperando autorización (pkexec)")
    rep.log(f"Instalando '{theme.name}': copia, backup, update-alternatives y initramfs")
    installer.install_theme(theme.directory, theme_name=theme.slug)
    rep.log(f"'{theme.name}' instalado y activado como tema de arranque")
    rep.progress(100, "Instalado")


def run_system_action(
    description: str, action: Callable[[], object], reporter: Reporter | None = None
) -> None:
    """Run a privileged installer call with uniform progress reporting."""
    rep = reporter or NullReporter()
    rep.progress(None, "Esperando autorización (pkexec)")
    rep.log(description)
    action()
    rep.progress(100, "Listo")
