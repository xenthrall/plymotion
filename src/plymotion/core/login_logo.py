"""Replace the distro logo on the GDM login screen (Ubuntu + GNOME).

GDM shows the image named by the `org.gnome.login-screen logo` GSettings
key centered near the bottom of the login screen. Ubuntu sets it through a
schema override shipped by `ubuntu-settings`
(logo='/usr/share/pixmaps/ubuntu-logo-text-dark.svg').

Instead of editing that override or the admin-owned
/etc/gdm3/greeter.dconf-defaults, a self-contained drop-in keyfile is added
to /usr/share/gdm/dconf. GDM's `generate-config` (ExecStartPre of
gdm.service) compiles every keyfile there, in name order, into the greeter's
dconf database, so a later-sorting "95-..." file wins over both the distro
default and 90-debian-settings. Restoring the distro logo is just deleting
that file and our copy of the image.
"""

from __future__ import annotations

import configparser
import shlex
import tempfile
from pathlib import Path

from PIL import Image

from plymotion.core.installer import run_privileged

GDM_DCONF_DIR = Path("/usr/share/gdm/dconf")
DCONF_SNIPPET = GDM_DCONF_DIR / "95-plymotion-logo"
GDM_GENERATE_CONFIG = Path("/usr/share/gdm/generate-config")
SCHEMA_OVERRIDES_DIR = Path("/usr/share/glib-2.0/schemas")

# Outside /home on purpose: GDM runs as the unprivileged `gdm` user, which
# typically can't read into a 0750 home directory.
LOGO_INSTALL_PATH = Path("/usr/share/plymotion/login-logo.png")

# GDM draws the logo at its natural pixel size (no scaling), aligned where
# Plymouth draws its watermark, so the image must be pre-sized. Ubuntu's own
# logo (and the Plymouth watermark it matches) is 187x72.
DEFAULT_LOGO_HEIGHT = 72
MAX_LOGO_WIDTH = 480

SUPPORTED_EXTENSIONS = ["png", "jpg", "jpeg", "webp", "bmp"]


def gdm_available() -> bool:
    """Whether this system has GDM's greeter dconf directory to write into."""
    return GDM_DCONF_DIR.is_dir()


def is_custom_logo_installed() -> bool:
    return DCONF_SNIPPET.is_file()


def distro_default_logo() -> Path | None:
    """The logo the distro configures via GSettings schema overrides, if any.

    Best-effort: overrides are applied in name order, so the last one
    setting the key wins, same as glib-compile-schemas.
    """
    logo: str | None = None
    for override in sorted(SCHEMA_OVERRIDES_DIR.glob("*.gschema.override")):
        parser = configparser.ConfigParser(interpolation=None, strict=False)
        try:
            parser.read(override)
        except configparser.Error:
            continue
        if parser.has_option("org.gnome.login-screen", "logo"):
            logo = parser.get("org.gnome.login-screen", "logo").strip().strip("'\"")
    return Path(logo) if logo else None


def previewable_path(logo: Path) -> Path | None:
    """A raster version of `logo` the UI can display (it doesn't render SVG).

    Ubuntu ships a same-named PNG next to its SVG logo, so prefer that.
    """
    if logo.suffix.lower() == ".svg":
        logo = logo.with_suffix(".png")
    return logo if logo.is_file() else None


def prepare_logo(
    source: Path,
    output: Path,
    max_height: int = DEFAULT_LOGO_HEIGHT,
    max_width: int = MAX_LOGO_WIDTH,
) -> tuple[int, int]:
    """Fit `source` within max_width x max_height and save it as a PNG.

    Aspect ratio and transparency are preserved, and the image is never
    upscaled. Returns the resulting (width, height).
    """
    with Image.open(source) as img:
        logo = img.convert("RGBA")
    logo.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
    output.parent.mkdir(parents=True, exist_ok=True)
    logo.save(output, "PNG")
    return logo.size


def _dconf_snippet() -> str:
    return (
        "# Written by Plymotion: custom GDM login screen logo.\n"
        "# Delete this file and run /usr/share/gdm/generate-config to go back\n"
        "# to the distro logo.\n"
        "[org/gnome/login-screen]\n"
        f"logo='{LOGO_INSTALL_PATH}'\n"
    )


def _regenerate_gdm_config() -> str:
    # Also runs on every GDM start; running it now just means the compiled
    # database is already up to date before the next login screen.
    q = shlex.quote(str(GDM_GENERATE_CONFIG))
    return f"if [ -x {q} ]; then {q}; fi\n"


def install_logo(
    source: Path,
    max_height: int = DEFAULT_LOGO_HEIGHT,
) -> tuple[int, int]:
    """Resize `source` and make it the GDM login screen logo (one pkexec prompt).

    Returns the installed logo's (width, height). The change shows the next
    time the login screen appears (logout or reboot).
    """
    if not gdm_available():
        raise RuntimeError(f"GDM not found ({GDM_DCONF_DIR} does not exist).")

    with tempfile.TemporaryDirectory(prefix="plymotion-logo-") as tmp:
        prepared = Path(tmp) / "login-logo.png"
        size = prepare_logo(source, prepared, max_height=max_height)
        snippet = Path(tmp) / "snippet"
        snippet.write_text(_dconf_snippet())

        script = f"""set -e
install -D -m 644 {shlex.quote(str(prepared))} {shlex.quote(str(LOGO_INSTALL_PATH))}
install -m 644 {shlex.quote(str(snippet))} {shlex.quote(str(DCONF_SNIPPET))}
{_regenerate_gdm_config()}"""
        run_privileged(script)
    return size


def restore_default_logo() -> None:
    """Remove Plymotion's logo override so GDM shows the distro logo again."""
    script = f"""set -e
rm -f {shlex.quote(str(DCONF_SNIPPET))} {shlex.quote(str(LOGO_INSTALL_PATH))}
{_regenerate_gdm_config()}"""
    run_privileged(script)
