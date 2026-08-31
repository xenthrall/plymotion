"""System view: themes actually installed under /usr/share/plymouth/themes."""

from __future__ import annotations

from typing import Any

import flet as ft

from plymotion import installer, library
from plymotion.ui import widgets
from plymotion.ui.context import AppContext

PREVIEW_SIZE = (360, 200)


def build_system_view(ctx: AppContext) -> ft.Control:
    page = ctx.page

    grid = ft.GridView(
        expand=True,
        max_extent=widgets.CARD_WIDTH + 20,
        spacing=12,
        run_spacing=12,
        child_aspect_ratio=0.68,
    )
    empty_state = ft.Column(
        visible=False,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        controls=[
            ft.Icon(ft.Icons.DESKTOP_WINDOWS, size=48, color=ft.Colors.OUTLINE),
            ft.Text(
                "No se encontraron temas instalados en el sistema.",
                italic=True, size=13, color=ft.Colors.OUTLINE,
            ),
        ],
    )

    def open_preview(theme: installer.InstalledTheme) -> None:
        # Only themes plymotion itself generated/installed follow the
        # frame*.png naming convention sample_preview_frames looks for;
        # other Plymouth themes (spinner, bgrt, ...) just won't have a
        # preview available, which is fine — we don't try to understand
        # every theme's arbitrary image layout.
        frames = library.sample_preview_frames(theme.directory)
        if not frames:
            ctx.notify("Este tema no tiene frames legibles para previsualizar.")
            return

        cancelled = {"value": False}
        image = ft.Image(
            src=frames[0].read_bytes(),
            width=PREVIEW_SIZE[0], height=PREVIEW_SIZE[1],
            fit=ft.BoxFit.CONTAIN, border_radius=8,
        )

        def close_preview(_e: Any = None) -> None:
            cancelled["value"] = True
            page.pop_dialog()

        dialog = ft.AlertDialog(
            title=ft.Text(theme.name),
            content=ft.Container(
                content=image, width=PREVIEW_SIZE[0] + 20, height=PREVIEW_SIZE[1] + 20,
                alignment=ft.Alignment.CENTER,
            ),
            actions=[ft.TextButton("Cerrar", on_click=close_preview)],
            on_dismiss=lambda _e: cancelled.__setitem__("value", True),
        )
        page.show_dialog(dialog)
        page.run_thread(
            widgets.animate_preview, image, frames,
            fps=12.0, loops=6, is_cancelled=lambda: cancelled["value"],
        )

    def run_privileged(
        busy_message: str, log_message: str, action: Any, success_message: str
    ) -> None:
        ctx.set_busy(True)
        ctx.set_status(busy_message)
        ctx.log(log_message)

        def run() -> None:
            try:
                action()
                ctx.set_status(success_message)
                ctx.log(f"--- {success_message} ---")
                ctx.notify(success_message)
                refresh()
            except Exception as exc:
                ctx.set_status("Error")
                ctx.log(f"ERROR: {exc}")
                ctx.notify(str(exc))
            finally:
                ctx.set_busy(False)

        page.run_thread(run)

    def confirm_activate(theme: installer.InstalledTheme) -> None:
        if ctx.is_busy():
            ctx.notify("Espera a que termine la operación actual.")
            return
        ctx.confirm_action(
            "Activar theme",
            f"'{theme.name}' pasará a ser el theme de arranque por defecto.\n"
            "El sistema pedirá contraseña de administrador (pkexec).\n\n¿Continuar?",
            "Activar",
            lambda: run_privileged(
                f"Activando '{theme.name}'...", f"--- Activando '{theme.name}' (pkexec) ---",
                lambda: installer.activate_theme(theme.directory.name),
                f"'{theme.name}' activado",
            ),
        )

    def confirm_uninstall(theme: installer.InstalledTheme) -> None:
        if ctx.is_busy():
            ctx.notify("Espera a que termine la operación actual.")
            return
        extra = (
            " Es el theme activo, así que primero se volverá a modo texto."
            if theme.is_default else ""
        )
        ctx.confirm_action(
            "Eliminar theme instalado",
            f"Se eliminará '{theme.name}' del sistema.{extra}\nEl sistema pedirá "
            "contraseña de administrador (pkexec).\n\n¿Continuar?",
            "Eliminar",
            lambda: run_privileged(
                f"Eliminando '{theme.name}'...", f"--- Eliminando '{theme.name}' (pkexec) ---",
                lambda: installer.uninstall_theme(theme.directory.name),
                f"'{theme.name}' eliminado",
            ),
        )

    def build_card(theme: installer.InstalledTheme) -> ft.Card:
        actions: list[ft.Control] = [
            ft.IconButton(
                icon=ft.Icons.PLAY_CIRCLE_OUTLINE, tooltip="Previsualizar",
                on_click=lambda _e, t=theme: open_preview(t),
            ),
        ]
        if not theme.is_default:
            actions.append(ft.IconButton(
                icon=ft.Icons.CHECK_CIRCLE_OUTLINE, tooltip="Activar",
                on_click=lambda _e, t=theme: confirm_activate(t),
            ))
        actions.append(ft.IconButton(
            icon=ft.Icons.DELETE_OUTLINE, tooltip="Eliminar", icon_color=ft.Colors.ERROR,
            on_click=lambda _e, t=theme: confirm_uninstall(t),
        ))
        first_frame = library.sample_preview_frames(theme.directory, max_frames=1)
        return widgets.theme_card(
            title=theme.name,
            subtitle=theme.description or theme.directory.name,
            thumbnail=first_frame[0] if first_frame else None,
            badge="Activo" if theme.is_default else None,
            on_thumbnail_click=lambda _e, t=theme: open_preview(t),
            actions=actions,
        )

    def confirm_test_active() -> None:
        if ctx.is_busy():
            ctx.notify("Espera a que termine la operación actual.")
            return
        ctx.confirm_action(
            "Probar boot splash",
            "Se mostrará el splash del theme activo actualmente durante unos "
            "segundos, sobre tu sesión en curso (la pantalla puede parpadear "
            "brevemente).\nEl sistema pedirá contraseña de administrador "
            "(pkexec).\n\n¿Continuar?",
            "Probar",
            lambda: run_privileged(
                "Mostrando splash activo...", "--- Probando theme activo (pkexec) ---",
                lambda: installer.preview_installed_theme(seconds=6),
                "Prueba finalizada",
            ),
        )

    def refresh() -> None:
        themes = installer.list_installed_themes()
        grid.controls = [build_card(t) for t in themes]
        empty_state.visible = not themes
        grid.visible = bool(themes)
        page.update()

    ctx.refresh_system = refresh
    refresh()

    return ft.Column(
        expand=True,
        spacing=14,
        controls=[
            ft.Row(
                [
                    ft.Text("Temas instalados en el sistema", size=20, weight=ft.FontWeight.BOLD),
                    ft.Row(
                        [
                            ft.OutlinedButton(
                                "Probar tema activo", icon=ft.Icons.PLAY_CIRCLE_OUTLINE,
                                on_click=lambda _e: confirm_test_active(),
                            ),
                            ft.IconButton(
                                icon=ft.Icons.REFRESH, tooltip="Actualizar",
                                on_click=lambda _e: refresh(),
                            ),
                        ]
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            empty_state,
            grid,
        ],
    )
