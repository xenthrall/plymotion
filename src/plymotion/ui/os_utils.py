"""Small cross-platform OS-integration helpers for the Flet UI."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def open_in_file_manager(path: Path) -> None:
    if sys.platform == "darwin":
        subprocess.Popen(["open", str(path)])
    elif sys.platform.startswith("win"):
        subprocess.Popen(["explorer", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(path)])
