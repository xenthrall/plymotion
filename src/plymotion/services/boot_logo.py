"""Show the login screen logo during the boot splash too.

The firmware's own logo (ACPI BGRT), drawn before Plymouth starts, can't be
changed from the OS. What can: Ubuntu's bgrt/spinner themes draw a logo
("watermark") near the bottom of the splash, exactly where GDM later draws
its login logo. Plymotion themes do the same with an optional
watermark.png, filled from whatever logo GDM currently shows (Plymotion's
custom one, or the distro's), so the logo stays put from boot to login.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from plymotion.core import library, login_logo
from plymotion.core.template_generator import WATERMARK_FILENAME, generate_script
from plymotion.services.login_logo import current_logo
from plymotion.services.themes import require_library_theme

# Same bounds the login logo is prepared with; GDM and Plymouth both draw
# it at its natural pixel size.
MAX_SIZE = (login_logo.MAX_LOGO_WIDTH, 400)


def login_logo_source() -> Path | None:
    """The PNG GDM currently shows as login logo, if any."""
    path, _custom = current_logo()
    return path


def write_watermark(theme_dir: Path, source: Path) -> tuple[int, int]:
    """Copy `source` into `theme_dir` as the theme's watermark (RGBA PNG)."""
    with Image.open(source) as img:
        logo = img.convert("RGBA")
    logo.thumbnail(MAX_SIZE, Image.Resampling.LANCZOS)
    logo.save(theme_dir / WATERMARK_FILENAME, "PNG")
    return logo.size


def set_library_boot_logo(slug: str, enabled: bool) -> library.LibraryTheme:
    """Add (from the current login logo) or remove a library theme's boot logo.

    Only touches the library copy; the installed theme changes when the
    theme is (re)installed.
    """
    theme = require_library_theme(slug)
    watermark = theme.directory / WATERMARK_FILENAME
    if enabled:
        source = login_logo_source()
        if source is None:
            raise ValueError("No hay logo de login para usar: aplica uno primero.")
        write_watermark(theme.directory, source)
    else:
        watermark.unlink(missing_ok=True)

    frame_count = len(library.sorted_frames(theme.directory))
    generate_script(theme.directory / f"{theme.slug}.script", frame_count, watermark=enabled)
    library.update_manifest(theme.directory, boot_logo=enabled)
    updated = library.get_library_theme(slug)
    assert updated is not None
    return updated
