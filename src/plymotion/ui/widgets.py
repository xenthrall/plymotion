"""Small reusable Flet helpers for the Plymotion UI."""

from __future__ import annotations

import flet as ft

RESOLUTIONS = ["1920x1080", "1366x768", "1280x720", "2560x1440", "3840x2160"]
FPS_OPTIONS = ["15", "24", "30", "60"]


def dropdown_options(values: list[str]) -> list[ft.DropdownOption]:
    """Build DropdownOption entries where the key and label are the same string."""
    return [ft.DropdownOption(key=v, text=v) for v in values]


def append_log(log_view: ft.ListView, line: str) -> None:
    """Append a monospace line to a log ListView. Caller is responsible for page.update()."""
    log_view.controls.append(ft.Text(line, size=12, font_family="monospace", selectable=True))
