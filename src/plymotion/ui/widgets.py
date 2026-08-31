"""Small reusable Flet helpers for the Plymotion UI."""

from __future__ import annotations

import time
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

import flet as ft

# Boot splash sprites don't need to match the screen's native resolution —
# Plymouth just centers this image on top of an otherwise black boot
# console — so these are deliberately modest: bigger sizes mean bigger,
# slower-to-generate PNG frames for no visual benefit at typical splash
# sizes. Users who want more can still type a custom value. For busy/
# photographic source video, only the smaller presets realistically get
# each frame under ~5KB; flatter, illustration-style content (logos,
# GIF-sourced animations) hits that at larger sizes too.
RESOLUTIONS = ["160x120", "240x180", "320x240", "480x360", "640x480"]
FPS_OPTIONS = ["15", "24", "30", "60"]
COLOR_OPTIONS = ["16", "32", "64", "128", "256"]

CARD_WIDTH = 220
THUMBNAIL_HEIGHT = 124


def dropdown_options(values: list[str]) -> list[ft.DropdownOption]:
    """Build DropdownOption entries where the key and label are the same string."""
    return [ft.DropdownOption(key=v, text=v) for v in values]


def append_log(log_view: ft.ListView, line: str) -> None:
    """Append a monospace line to a log ListView. Caller is responsible for page.update()."""
    log_view.controls.append(ft.Text(line, size=12, font_family="monospace", selectable=True))


def _thumbnail_control(thumbnail: Path | None) -> ft.Control:
    if thumbnail is not None and thumbnail.is_file():
        return ft.Image(
            src=thumbnail.read_bytes(),
            width=CARD_WIDTH,
            height=THUMBNAIL_HEIGHT,
            fit=ft.BoxFit.COVER,
            border_radius=8,
        )
    return ft.Container(
        width=CARD_WIDTH,
        height=THUMBNAIL_HEIGHT,
        bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
        border_radius=8,
        alignment=ft.Alignment.CENTER,
        content=ft.Icon(ft.Icons.MOVIE_OUTLINED, color=ft.Colors.OUTLINE, size=32),
    )


def theme_card(
    *,
    title: str,
    subtitle: str,
    thumbnail: Path | None,
    actions: list[ft.Control],
    badge: str | None = None,
    on_thumbnail_click: Callable[[Any], Any] | None = None,
) -> ft.Card:
    """A gallery-style card: thumbnail, title/subtitle, and a row of action buttons.

    Shared by the library gallery view and the installed-system-themes view
    so both grids look and behave consistently.
    """
    thumb = _thumbnail_control(thumbnail)
    thumb_area: ft.Control = thumb
    if on_thumbnail_click is not None:
        thumb_area = ft.GestureDetector(content=thumb, on_tap=on_thumbnail_click)

    title_row = cast(
        "list[ft.Control]",
        [ft.Text(title, weight=ft.FontWeight.BOLD, size=14, overflow=ft.TextOverflow.ELLIPSIS)],
    )
    if badge:
        title_row.append(ft.Container(
            content=ft.Text(badge, size=10, color=ft.Colors.ON_PRIMARY),
            bgcolor=ft.Colors.PRIMARY,
            padding=ft.Padding.symmetric(horizontal=6, vertical=2),
            border_radius=6,
        ))

    return ft.Card(
        width=CARD_WIDTH,
        content=ft.Container(
            padding=10,
            content=ft.Column(
                tight=True,
                spacing=6,
                controls=[
                    thumb_area,
                    ft.Row(title_row, spacing=6),
                    ft.Text(subtitle, size=11, italic=True, color=ft.Colors.OUTLINE),
                    ft.Row(cast("list[ft.Control]", actions), spacing=4, wrap=True),
                ],
            ),
        ),
    )


def animate_preview(
    page: ft.Page,
    image: ft.Image,
    frames: list[Path],
    *,
    fps: float = 12.0,
    loops: int = 3,
    is_cancelled: Callable[[], bool] | None = None,
) -> None:
    """Cycle `image.src` through `frames` for a few loops. Runs synchronously —
    call via page.run_thread() so it doesn't block the UI event loop.

    `is_cancelled`, if given, is a zero-arg callable checked between frames so
    a closed preview dialog can stop the loop early instead of leaking it.
    """
    if not frames:
        return
    delay = 1.0 / fps
    for _ in range(loops):
        for frame in frames:
            if is_cancelled is not None and is_cancelled():
                return
            image.src = frame.read_bytes()
            page.update()
            time.sleep(delay)
