"""Native file dialogs, so the client gets real paths instead of uploads.

A browser can't hand a page the path of a picked file, and uploading a
multi-hundred-MB video to our own disk would be absurd. The desktop shell
(plymotion.desktop) plugs in a pywebview-backed picker; outside it
(browser dev mode) zenity is used when installed.
"""

from __future__ import annotations

import shutil
import subprocess
from typing import Protocol

from plymotion.services.convert import VIDEO_EXTENSIONS
from plymotion.services.login_logo import IMAGE_EXTENSIONS

TITLES = {
    "video": "Selecciona un video o GIF",
    "image": "Selecciona una imagen",
    "images": "Selecciona las imágenes de la secuencia",
}


def extensions_for(kind: str) -> list[str]:
    return VIDEO_EXTENSIONS if kind == "video" else IMAGE_EXTENSIONS


class FileDialogs(Protocol):
    def pick(self, kind: str) -> list[str]:
        """Show a picker for `kind` ("video" | "image" | "images"); [] when cancelled."""
        ...


class ZenityDialogs:
    @staticmethod
    def available() -> bool:
        return shutil.which("zenity") is not None

    def pick(self, kind: str) -> list[str]:
        patterns = " ".join(f"*.{ext} *.{ext.upper()}" for ext in extensions_for(kind))
        cmd = ["zenity", "--file-selection", f"--title={TITLES[kind]}",
               f"--file-filter=Archivos | {patterns}", "--separator=\n"]
        if kind == "images":
            cmd.append("--multiple")
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            return []
        return [line for line in result.stdout.splitlines() if line]


def default_dialogs() -> FileDialogs | None:
    return ZenityDialogs() if ZenityDialogs.available() else None
