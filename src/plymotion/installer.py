"""Safe Plymouth theme installer with backup and rollback.

All steps that touch the system (writing under /usr/share/plymouth or
/var/backups, update-alternatives, update-initramfs) run as a single
`pkexec` invocation, so the desktop shows one graphical password prompt
per action instead of requiring the whole app to run as root.
"""

from __future__ import annotations

import configparser
import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path

THEMES_DIR = Path("/usr/share/plymouth/themes")
BACKUP_DIR = Path("/var/backups/plymotion")

# Fallback used by reset_to_default(): not every distro ships the
# `plymouth-set-default-theme` wrapper script, but the `text` theme and
# update-alternatives are part of the plymouth package itself.
TEXT_THEME_PLYMOUTH = THEMES_DIR / "text" / "text.plymouth"


def _run_privileged(script: str) -> None:
    """Run a shell script as root via pkexec, raising with stderr on failure."""
    result = subprocess.run(
        ["pkexec", "bash", "-c", script],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"Command failed (exit {result.returncode})")


@dataclass(frozen=True)
class InstalledTheme:
    name: str
    description: str
    directory: Path
    plymouth_path: Path
    is_default: bool


def _current_default_theme_dir_name() -> str | None:
    """Best-effort resolution of which installed theme is the system default.

    Reliable when the theme was set via update-alternatives (Debian/Ubuntu),
    which is what install_theme()/reset_to_default() use. On distros that
    don't manage the default.plymouth symlink this way, this may not
    resolve, and every theme will show as non-default.
    """
    default_link = THEMES_DIR / "default.plymouth"
    try:
        return default_link.resolve(strict=True).parent.name
    except OSError:
        return None


def list_installed_themes() -> list[InstalledTheme]:
    """List Plymouth themes installed under THEMES_DIR. Read-only, no pkexec."""
    if not THEMES_DIR.is_dir():
        return []

    default_dir_name = _current_default_theme_dir_name()
    themes = []
    for plymouth_file in sorted(THEMES_DIR.glob("*/*.plymouth")):
        parser = configparser.ConfigParser()
        try:
            parser.read(plymouth_file)
            section = parser["Plymouth Theme"]
        except (configparser.Error, KeyError):
            continue

        themes.append(
            InstalledTheme(
                name=section.get("Name", plymouth_file.parent.name),
                description=section.get("Description", ""),
                directory=plymouth_file.parent,
                plymouth_path=plymouth_file,
                is_default=plymouth_file.parent.name == default_dir_name,
            )
        )
    return themes


def validate_theme(theme_dir: Path) -> list[str]:
    """Validate a theme directory. Returns list of error messages (empty = valid)."""
    errors = []

    plymouth_files = list(theme_dir.glob("*.plymouth"))
    if not plymouth_files:
        errors.append("No .plymouth config file found")
        return errors

    config = plymouth_files[0]
    content = config.read_text()

    # Ubuntu/Debian's initramfs-tools plymouth hook resolves each theme's
    # module/files as themes/<dir-name>/<dir-name>.plymouth (derived from the
    # update-alternatives target's basename), and silently skips baking a
    # theme into the initramfs if that path doesn't exist. A mismatch here
    # means the theme still looks fine live (preview, shutdown/reboot splash,
    # both read straight off disk) but boot itself falls back to a text-mode
    # error, since it runs from the initramfs snapshot instead.
    if config.stem != theme_dir.name:
        errors.append(
            f"Plymouth config filename '{config.name}' must match the theme "
            f"directory name '{theme_dir.name}' (expected '{theme_dir.name}.plymouth'): "
            "Ubuntu/Debian's initramfs-tools hook silently drops themes that don't "
            "match this when building the initramfs, which shows up as a working "
            "shutdown animation but a broken/text boot splash."
        )

    if "ModuleName=script" not in content:
        errors.append("Theme does not use the 'script' module")

    if "ScriptFile=" not in content:
        errors.append("No ScriptFile defined in .plymouth config")

    if "ImageDir=" not in content:
        errors.append("No ImageDir defined in .plymouth config")

    script_files = list(theme_dir.glob("*.script"))
    if not script_files:
        errors.append("No .script file found")
    elif script_files[0].stat().st_size == 0:
        errors.append("Script file is empty")

    frames = list(theme_dir.glob("frame*.png"))
    if not frames:
        errors.append("No frame images found (frame*.png)")

    return errors


def install_theme(
    source_dir: Path,
    theme_name: str = "plymotion",
    priority: int = 120,
) -> None:
    """Install a theme to the system themes directory.

    Steps (run atomically as root via pkexec):
    1. Backup the current theme of the same name, if any
    2. Copy the new theme into place
    3. Register it with update-alternatives
    4. Regenerate the initramfs
    """
    errors = validate_theme(source_dir)
    if errors:
        raise ValueError("Theme validation failed:\n" + "\n".join(f"  - {e}" for e in errors))

    dest = THEMES_DIR / theme_name
    backup_path = BACKUP_DIR / theme_name

    script = f"""set -e
mkdir -p {shlex.quote(str(BACKUP_DIR))}
if [ -d {shlex.quote(str(dest))} ]; then
    rm -rf {shlex.quote(str(backup_path))}
    cp -r {shlex.quote(str(dest))} {shlex.quote(str(backup_path))}
fi
rm -rf {shlex.quote(str(dest))}
cp -r {shlex.quote(str(source_dir))} {shlex.quote(str(dest))}
plymouth_file=$(find {shlex.quote(str(dest))} -maxdepth 1 -name '*.plymouth' | head -n1)
update-alternatives --install /usr/share/plymouth/themes/default.plymouth \
default.plymouth "$plymouth_file" {int(priority)}
# -k all: plain `-u` only rebuilds the initramfs of the kernel that was
# "current" when this ran, which can silently differ from the kernel that
# actually gets booted next (e.g. right after a kernel upgrade), leaving
# the old theme baked into the boot image the user actually sees.
update-initramfs -u -k all
"""
    _run_privileged(script)


def restore_backup(theme_name: str = "plymotion") -> bool:
    """Restore a theme from its backup and regenerate the initramfs.

    Returns True if a backup existed and was restored, False if there was
    nothing to restore.
    """
    backup_path = BACKUP_DIR / theme_name
    if not backup_path.exists():
        return False

    dest = THEMES_DIR / theme_name
    script = f"""set -e
rm -rf {shlex.quote(str(dest))}
cp -r {shlex.quote(str(backup_path))} {shlex.quote(str(dest))}
update-initramfs -u -k all
"""
    _run_privileged(script)
    return True


def _find_installed_plymouth_file(theme_dir_name: str) -> Path | None:
    theme_dir = THEMES_DIR / theme_dir_name
    matches = list(theme_dir.glob("*.plymouth")) if theme_dir.is_dir() else []
    return matches[0] if matches else None


def activate_theme(theme_dir_name: str) -> None:
    """Point the system default at an already-installed theme.

    Unlike install_theme(), this does not copy any files — it only flips
    which already-installed theme is the default.
    """
    plymouth_file = _find_installed_plymouth_file(theme_dir_name)
    if plymouth_file is None:
        raise ValueError(f"Theme '{theme_dir_name}' is not installed under {THEMES_DIR}")

    script = f"""set -e
update-alternatives --set default.plymouth {shlex.quote(str(plymouth_file))}
update-initramfs -u -k all
"""
    _run_privileged(script)


def uninstall_theme(theme_dir_name: str) -> None:
    """Remove an installed theme, falling back to the text theme first if it's the default."""
    if theme_dir_name == TEXT_THEME_PLYMOUTH.parent.name:
        raise ValueError("Refusing to uninstall the built-in text theme (safety fallback).")

    plymouth_file = _find_installed_plymouth_file(theme_dir_name)
    if plymouth_file is None:
        raise ValueError(f"Theme '{theme_dir_name}' is not installed under {THEMES_DIR}")

    dest = THEMES_DIR / theme_dir_name
    default_link = THEMES_DIR / "default.plymouth"
    script = f"""set -e
if [ "$(readlink -f {shlex.quote(str(default_link))})" = \
"$(readlink -f {shlex.quote(str(plymouth_file))})" ]; then
    update-alternatives --set default.plymouth {shlex.quote(str(TEXT_THEME_PLYMOUTH))}
fi
update-alternatives --remove default.plymouth {shlex.quote(str(plymouth_file))}
rm -rf {shlex.quote(str(dest))}
update-initramfs -u -k all
"""
    _run_privileged(script)


def reset_to_default() -> None:
    """Point Plymouth back at the plain text theme and regenerate the initramfs."""
    script = f"""set -e
update-alternatives --set default.plymouth {shlex.quote(str(TEXT_THEME_PLYMOUTH))}
update-initramfs -u -k all
"""
    _run_privileged(script)


def preview_installed_theme(seconds: int = 6) -> None:
    """Show the currently installed default theme live, without rebooting.

    Runs plymouthd against the current default theme for `seconds`, then
    tells it to quit. This only previews whatever theme is already the
    system default (see install_theme) — it does not load an arbitrary
    theme directory.
    """
    script = f"""set -e
plymouthd --no-daemon --debug &
plymouthd_pid=$!
sleep 1
plymouth --show-splash
sleep {int(seconds)}
plymouth --quit
wait "$plymouthd_pid" 2>/dev/null || true
"""
    _run_privileged(script)
