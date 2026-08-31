"""Safe Plymouth theme installer with backup and rollback."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

THEMES_DIR = Path("/usr/share/plymouth/themes")
BACKUP_DIR = Path("/var/backups/plymotion")


def backup_current_theme(theme_name: str = "plymotion") -> Path | None:
    """Backup the current theme before overwriting. Returns backup path or None."""
    theme_dir = THEMES_DIR / theme_name
    if not theme_dir.exists():
        return None

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    backup_path = BACKUP_DIR / theme_name
    if backup_path.exists():
        shutil.rmtree(backup_path)
    shutil.copytree(theme_dir, backup_path)
    return backup_path


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

    Steps:
    1. Backup current theme
    2. Validate source
    3. Copy files
    4. Update alternatives
    5. Update initramfs
    """
    # Validate source
    errors = validate_theme(source_dir)
    if errors:
        raise ValueError("Theme validation failed:\n" + "\n".join(f"  - {e}" for e in errors))

    # Backup
    backup_current_theme(theme_name)

    # Copy
    dest = THEMES_DIR / theme_name
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(source_dir, dest)

    # Find .plymouth file
    plymouth_file = next(dest.glob("*.plymouth"))
    alt_path = str(plymouth_file)

    # Update alternatives
    subprocess.run(
        [
            "update-alternatives", "--install",
            "/usr/share/plymouth/themes/default.plymouth",
            "default.plymouth",
            alt_path,
            str(priority),
        ],
        check=True,
    )

    # Update initramfs
    subprocess.run(
        ["update-initramfs", "-u"],
        check=True,
    )


def restore_backup(theme_name: str = "plymotion") -> bool:
    """Restore theme from backup. Returns True if restored."""
    backup_path = BACKUP_DIR / theme_name
    if not backup_path.exists():
        return False

    dest = THEMES_DIR / theme_name
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(backup_path, dest)
    return True


def reset_to_default() -> None:
    """Reset Plymouth to the default text theme."""
    subprocess.run(
        ["plymouth-set-default-theme", "-R", "text"],
        check=True,
    )
