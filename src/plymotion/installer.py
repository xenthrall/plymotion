"""Safe Plymouth theme installer with backup and rollback.

All steps that touch the system (writing under /usr/share/plymouth or
/var/backups, update-alternatives, update-initramfs) run as a single
`pkexec` invocation, so the desktop shows one graphical password prompt
per action instead of requiring the whole app to run as root.
"""

from __future__ import annotations

import shlex
import subprocess
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


def validate_theme(theme_dir: Path) -> list[str]:
    """Validate a theme directory. Returns list of error messages (empty = valid)."""
    errors = []

    plymouth_files = list(theme_dir.glob("*.plymouth"))
    if not plymouth_files:
        errors.append("No .plymouth config file found")
        return errors

    config = plymouth_files[0]
    content = config.read_text()

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
update-initramfs -u
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
update-initramfs -u
"""
    _run_privileged(script)
    return True


def reset_to_default() -> None:
    """Point Plymouth back at the plain text theme and regenerate the initramfs."""
    script = f"""set -e
update-alternatives --set default.plymouth {shlex.quote(str(TEXT_THEME_PLYMOUTH))}
update-initramfs -u
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
