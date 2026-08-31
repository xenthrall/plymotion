"""Small reusable Flet helpers for the Plymotion UI."""

from __future__ import annotations

import io
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

import flet as ft
from PIL import Image

# Boot splash sprites don't need to match the screen's native resolution —
# Plymouth just centers this image on top of an otherwise black boot
# console — so smaller presets are offered too: for busy/photographic
# source video, only those realistically get each frame under ~5KB;
# flatter, illustration-style content (logos, GIF-sourced animations) hits
# that at larger sizes too. 1920x1080 (or another large preset) is here for
# a splash meant to genuinely cover the whole screen — scaling a smaller
# saved frame up to screen size at boot time instead (rather than saving it
# at full size to begin with) was tried and reverted: it measurably delays
# the splash's first frame from appearing.
RESOLUTIONS = ["160x120", "240x180", "320x240", "480x360", "640x480", "1280x720", "1920x1080"]
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


def build_preview_gif(frames: list[Path], fps: float = 12.0) -> bytes:
    """Assemble already-extracted PNG frames into a single in-memory animated GIF.

    Earlier this cycled a still ft.Image's `src` on a timer from a
    background thread, updating it after the dialog showing it was already
    open — but page.show_dialog() renders dialogs through a separate
    `_dialogs` stack, and neither a bare page.update() nor a targeted
    control.update() reliably reached it in practice, so the preview just
    sat on the first frame. Baking one animated GIF and setting it as
    `src` once, before the dialog is even shown, sidesteps that class of
    bug entirely: Flutter animates the GIF itself, client-side, no Python
    thread or repeated update() call involved.
    """
    if not frames:
        raise ValueError("No frames to preview.")
    duration_ms = max(round(1000 / fps), 20)
    images = [Image.open(f).convert("RGB") for f in frames]
    try:
        buf = io.BytesIO()
        images[0].save(
            buf, format="GIF", save_all=True, append_images=images[1:],
            duration=duration_ms, loop=0,
        )
        return buf.getvalue()
    finally:
        for img in images:
            img.close()
