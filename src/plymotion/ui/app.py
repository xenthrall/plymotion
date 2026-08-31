"""Plymotion main GUI window (Flet): sidebar shell wiring the Convertir,
Galería, Sistema, and Restaurar views together through a shared AppContext."""

from __future__ import annotations

from typing import Any, cast

import flet as ft

from plymotion import __version__, library
from plymotion.ui.context import AppContext
from plymotion.ui.views.convert_view import build_convert_view
from plymotion.ui.views.gallery_view import build_gallery_view
from plymotion.ui.views.restore_view import build_restore_view
from plymotion.ui.views.system_view import build_system_view
from plymotion.ui.widgets import append_log

THEME_SEED = ft.Colors.INDIGO

_THEME_MODE_BY_KEY = {
    "light": ft.ThemeMode.LIGHT,
    "dark": ft.ThemeMode.DARK,
    "system": ft.ThemeMode.SYSTEM,
}


async def main(page: ft.Page) -> None:
    """Build and wire up the Plymotion window for a single Flet session."""
    page.title = f"Plymotion v{__version__}"
    page.theme = ft.Theme(color_scheme_seed=THEME_SEED)
    page.dark_theme = ft.Theme(color_scheme_seed=THEME_SEED)
    page.theme_mode = _THEME_MODE_BY_KEY.get(
        cast(str, library.load_prefs().get("theme_mode")), ft.ThemeMode.SYSTEM
    )
    page.window.width = 980
    page.window.height = 720
    page.window.min_width = 760
    page.window.min_height = 560
    page.padding = 0
    page.spacing = 0

    # --- Shared log/status, used by every view via AppContext -----------------

    log_view = ft.ListView(spacing=2, auto_scroll=True)
    log_container = ft.Container(
        content=log_view,
        border=ft.Border.all(width=1, color=ft.Colors.OUTLINE),
        border_radius=8,
        padding=10,
        height=120,
    )
    status_text = ft.Text("Listo", italic=True, size=12)

    def log(line: str) -> None:
        append_log(log_view, line)
        page.update()

    def notify(text: str) -> None:
        page.show_dialog(ft.SnackBar(ft.Text(text), open=True))

    def set_status(text: str) -> None:
        status_text.value = text
        page.update()

    def confirm_action(title: str, message: str, confirm_label: str, on_confirm: Any) -> None:
        def do_action(_e: Any) -> None:
            page.pop_dialog()
            on_confirm()

        def cancel(_e: Any) -> None:
            page.pop_dialog()

        page.show_dialog(
            ft.AlertDialog(
                title=ft.Text(title),
                content=ft.Text(message),
                actions=cast(
                    "list[ft.Control]",
                    [
                        ft.TextButton("Cancelar", on_click=cancel),
                        ft.FilledButton(confirm_label, on_click=do_action),
                    ],
                ),
            )
        )

    # `busy`: true while any privileged (pkexec) action is running, checked by
    # every view before starting another one, so two pkexec prompts never
    # overlap regardless of which view they were triggered from.
    busy = {"value": False}

    def is_busy() -> bool:
        return busy["value"]

    def set_busy(value: bool) -> None:
        busy["value"] = value
        for listener in ctx.busy_listeners:
            listener(value)
        page.update()

    ctx = AppContext(
        page=page,
        log=log,
        notify=notify,
        set_status=set_status,
        confirm_action=confirm_action,
        is_busy=is_busy,
        set_busy=set_busy,
    )

    # --- Views ------------------------------------------------------------
    # Built once; NavigationRail just swaps which one is visible, so each
    # view keeps its own state (grids, dialogs) across navigation.
    convert_control = build_convert_view(ctx)
    gallery_control = build_gallery_view(ctx)
    system_control = build_system_view(ctx)
    restore_control = build_restore_view(ctx)
    views = [convert_control, gallery_control, system_control, restore_control]

    content_area = ft.Container(content=views[0], expand=True, padding=24)

    def on_nav_change(e: Any) -> None:
        content_area.content = views[e.control.selected_index]
        page.update()

    def switch_view(index: int) -> None:
        nav_rail.selected_index = index
        content_area.content = views[index]
        page.update()

    # --- Theme mode toggle (persisted) -----------------------------------
    def set_theme_mode(key: str) -> None:
        page.theme_mode = _THEME_MODE_BY_KEY[key]
        library.save_prefs(theme_mode=key)
        page.update()

    theme_toggle = ft.Row(
        cast(
            "list[ft.Control]",
            [
                ft.IconButton(
                    icon=ft.Icons.LIGHT_MODE, tooltip="Tema claro",
                    on_click=lambda _e: set_theme_mode("light"),
                ),
                ft.IconButton(
                    icon=ft.Icons.DARK_MODE, tooltip="Tema oscuro",
                    on_click=lambda _e: set_theme_mode("dark"),
                ),
                ft.IconButton(
                    icon=ft.Icons.BRIGHTNESS_AUTO, tooltip="Seguir al sistema",
                    on_click=lambda _e: set_theme_mode("system"),
                ),
            ],
        ),
        alignment=ft.MainAxisAlignment.CENTER,
    )

    nav_rail = ft.NavigationRail(
        selected_index=0,
        label_type=ft.NavigationRailLabelType.ALL,
        min_width=88,
        min_extended_width=160,
        destinations=[
            ft.NavigationRailDestination(
                icon=ft.Icons.MOVIE_CREATION_OUTLINED,
                selected_icon=ft.Icons.MOVIE_CREATION,
                label="Convertir",
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.COLLECTIONS_OUTLINED,
                selected_icon=ft.Icons.COLLECTIONS,
                label="Galería",
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.DESKTOP_WINDOWS_OUTLINED,
                selected_icon=ft.Icons.DESKTOP_WINDOWS,
                label="Sistema",
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.BURST_MODE_OUTLINED,
                selected_icon=ft.Icons.BURST_MODE,
                label="Restaurar",
            ),
        ],
        trailing=theme_toggle,
        pin_trailing_to_bottom=True,
        on_change=on_nav_change,
    )
    ctx.switch_view = switch_view

    page.add(
        ft.Row(
            expand=True,
            spacing=0,
            controls=cast(
                "list[ft.Control]",
                [
                    nav_rail,
                    ft.VerticalDivider(width=1),
                    ft.Column(
                        expand=True,
                        spacing=0,
                        controls=[
                            content_area,
                            ft.Container(
                                padding=ft.Padding.symmetric(horizontal=24, vertical=12),
                                content=ft.Column(
                                    spacing=6,
                                    controls=[
                                        ft.Text("Registro:", weight=ft.FontWeight.W_500, size=12),
                                        log_container,
                                        status_text,
                                    ],
                                ),
                            ),
                        ],
                    ),
                ],
            ),
        )
    )


def run(**kwargs: Any) -> None:
    """Launch the Flet app. Extra kwargs are forwarded to ft.run (e.g. view=...)."""
    ft.run(main, **kwargs)
