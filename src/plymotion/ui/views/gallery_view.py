"""Gallery view: local library of generated themes, browsable like a photo gallery."""

from __future__ import annotations

from typing import Any

import flet as ft

from plymotion import library
from plymotion.ui import widgets
from plymotion.ui.context import AppContext
from plymotion.ui.os_utils import open_in_file_manager

PREVIEW_SIZE = (360, 200)


def build_gallery_view(ctx: AppContext) -> ft.Control:
    page = ctx.page

    grid = ft.GridView(
        expand=True,
        max_extent=widgets.CARD_WIDTH + 20,
        spacing=12,
        run_spacing=12,
        child_aspect_ratio=0.72,
    )
    empty_state = ft.Column(
        visible=False,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        controls=[
            ft.Icon(ft.Icons.COLLECTIONS_OUTLINED, size=48, color=ft.Colors.OUTLINE),
            ft.Text(
                "Aún no hay temas en la galería. Convierte un video o GIF para empezar.",
                italic=True, size=13, color=ft.Colors.OUTLINE,
            ),
        ],
    )

    def open_preview(theme: library.LibraryTheme) -> None:
        frames = library.sample_preview_frames(theme.directory)
        if not frames:
            ctx.notify("Este tema no tiene frames para previsualizar.")
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

    def do_install(theme: library.LibraryTheme) -> None:
        from plymotion.installer import install_theme

        ctx.set_busy(True)
        ctx.set_status(f"Instalando '{theme.name}'...")
        ctx.log(f"--- Instalando '{theme.name}' (pkexec) ---")

        def run() -> None:
            try:
                install_theme(theme.directory, theme_name=theme.slug)
                ctx.set_status("Theme instalado")
                ctx.log(f"--- '{theme.name}' instalado ---")
                ctx.notify(f"'{theme.name}' instalado correctamente.")
                ctx.refresh_system()
            except Exception as exc:
                ctx.set_status("Error en la instalación")
                ctx.log(f"ERROR: {exc}")
                ctx.notify(str(exc))
            finally:
                ctx.set_busy(False)

        page.run_thread(run)

    def confirm_install(theme: library.LibraryTheme) -> None:
        if ctx.is_busy():
            ctx.notify("Espera a que termine la operación actual.")
            return
        ctx.confirm_action(
            "Confirmar instalación",
            f"Se instalará '{theme.name}' como tema de arranque del sistema "
            "(con backup del que tenga el mismo nombre).\nEl sistema pedirá "
            "contraseña de administrador (pkexec).\n\n¿Continuar?",
            "Instalar",
            lambda: do_install(theme),
        )

    def confirm_delete(theme: library.LibraryTheme) -> None:
        if ctx.is_busy():
            ctx.notify("Espera a que termine la operación actual.")
            return

        def do_delete() -> None:
            library.delete_library_theme(theme.slug)
            ctx.log(f"'{theme.name}' eliminado de la galería.")
            ctx.notify(f"'{theme.name}' eliminado de la galería.")
            refresh()

        ctx.confirm_action(
            "Eliminar de la galería",
            f"Se eliminará '{theme.name}' de la galería local (no afecta a un "
            "tema ya instalado en el sistema con estos archivos).\n\n¿Continuar?",
            "Eliminar",
            do_delete,
        )

    def build_card(theme: library.LibraryTheme) -> ft.Card:
        w, h = theme.resolution
        subtitle = f"{theme.frame_count} frames · {w}x{h} · loop ~{theme.loop_seconds:.1f}s"
        return widgets.theme_card(
            title=theme.name,
            subtitle=subtitle,
            thumbnail=theme.thumbnail,
            on_thumbnail_click=lambda _e, t=theme: open_preview(t),
            actions=[
                ft.IconButton(
                    icon=ft.Icons.PLAY_CIRCLE_OUTLINE, tooltip="Previsualizar",
                    on_click=lambda _e, t=theme: open_preview(t),
                ),
                ft.IconButton(
                    icon=ft.Icons.INSTALL_DESKTOP, tooltip="Instalar en el sistema",
                    on_click=lambda _e, t=theme: confirm_install(t),
                ),
                ft.IconButton(
                    icon=ft.Icons.FOLDER_OPEN, tooltip="Abrir carpeta",
                    on_click=lambda _e, t=theme: open_in_file_manager(t.directory),
                ),
                ft.IconButton(
                    icon=ft.Icons.DELETE_OUTLINE, tooltip="Eliminar de la galería",
                    icon_color=ft.Colors.ERROR,
                    on_click=lambda _e, t=theme: confirm_delete(t),
                ),
            ],
        )

    def refresh() -> None:
        themes = sorted(
            library.list_library_themes(), key=lambda t: t.created_at, reverse=True
        )
        grid.controls = [build_card(t) for t in themes]
        empty_state.visible = not themes
        grid.visible = bool(themes)
        page.update()

    ctx.refresh_gallery = refresh
    refresh()

    return ft.Column(
        expand=True,
        spacing=14,
        controls=[
            ft.Row(
                [
                    ft.Text("Galería de temas generados", size=20, weight=ft.FontWeight.BOLD),
                    ft.IconButton(
                        icon=ft.Icons.REFRESH, tooltip="Actualizar", on_click=lambda _e: refresh()
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            empty_state,
            grid,
        ],
    )
