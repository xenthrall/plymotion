"""Login view: replace the distro logo shown on the GDM login screen."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any, cast

import flet as ft

from plymotion import login_logo
from plymotion.ui.context import AppContext
from plymotion.ui.widgets import dropdown_options

HEIGHT_OPTIONS = ["48", "72", "96", "128", "160"]

# Approximates the dark greeter background so the preview shows the logo
# the way it will actually read (Ubuntu's logo is white-on-dark).
_MOCK_SCREEN_COLOR = "#1d1d1d"
_MOCK_SCREEN_SIZE = (500, 170)


def _mock_screen(
    caption: str, logo_bytes: bytes | None, size: tuple[int, int] | None
) -> ft.Control:
    """A dark panel with the logo drawn at its real pixel size, bottom-centered."""
    if logo_bytes is not None and size is not None:
        logo: ft.Control = ft.Image(src=logo_bytes, width=size[0], height=size[1])
    else:
        logo = ft.Text("(sin logo)", size=12, italic=True, color=ft.Colors.GREY_500)
    return ft.Column(
        tight=True,
        spacing=6,
        controls=[
            ft.Text(caption, weight=ft.FontWeight.W_500, size=13),
            ft.Container(
                width=_MOCK_SCREEN_SIZE[0],
                height=_MOCK_SCREEN_SIZE[1],
                bgcolor=_MOCK_SCREEN_COLOR,
                border_radius=8,
                padding=ft.Padding.only(bottom=12),
                alignment=ft.Alignment.BOTTOM_CENTER,
                content=logo,
            ),
        ],
    )


def build_login_view(ctx: AppContext) -> ft.Control:
    page = ctx.page

    image_path = ft.TextField(label="Imagen del logo", read_only=True, expand=True)
    height = ft.Dropdown(
        label="Alto máx. (px)", value=str(login_logo.DEFAULT_LOGO_HEIGHT),
        options=dropdown_options(HEIGHT_OPTIONS), width=150, editable=True,
        on_select=lambda _e: refresh(),
        on_text_change=lambda _e: refresh(),
    )
    current_panel = ft.Container()
    new_panel = ft.Container()
    status_text = ft.Text(size=12, italic=True, color=ft.Colors.OUTLINE)

    # See convert_view: FilePicker registers itself on construction and must
    # not be added to the page's controls.
    file_picker = ft.FilePicker()

    def parse_height() -> int | None:
        try:
            value = int(height.value or login_logo.DEFAULT_LOGO_HEIGHT)
        except ValueError:
            return None
        return value if value > 0 else None

    def refresh_current() -> None:
        if login_logo.is_custom_logo_installed():
            logo = login_logo.LOGO_INSTALL_PATH
            caption = "Actual: logo personalizado (Plymotion)"
        else:
            logo = login_logo.distro_default_logo()
            caption = "Actual: logo de la distro"
        preview = login_logo.previewable_path(logo) if logo else None
        if preview is not None:
            from PIL import Image

            with Image.open(preview) as img:
                size = img.size
            current_panel.content = _mock_screen(caption, preview.read_bytes(), size)
        else:
            current_panel.content = _mock_screen(caption, None, None)
        restore_btn.disabled = ctx.is_busy() or not login_logo.is_custom_logo_installed()

    def refresh_new_preview() -> None:
        source = image_path.value
        max_h = parse_height()
        if not source or max_h is None:
            new_panel.content = None
            return
        try:
            with tempfile.TemporaryDirectory(prefix="plymotion-logo-preview-") as tmp:
                out = Path(tmp) / "preview.png"
                size = login_logo.prepare_logo(Path(source), out, max_height=max_h)
                data = out.read_bytes()
        except Exception as exc:
            new_panel.content = ft.Text(f"No se pudo leer la imagen: {exc}", color=ft.Colors.ERROR)
            return
        new_panel.content = _mock_screen(f"Nuevo: {size[0]}x{size[1]} px", data, size)

    def refresh() -> None:
        refresh_current()
        refresh_new_preview()
        page.update()

    async def on_pick_image(_e: Any) -> None:
        files = await file_picker.pick_files(
            dialog_title="Selecciona el logo",
            file_type=ft.FilePickerFileType.CUSTOM,
            allowed_extensions=login_logo.SUPPORTED_EXTENSIONS,
        )
        if not files or not files[0].path:
            return
        image_path.value = files[0].path
        ctx.log(f"Logo seleccionado: {files[0].path}")
        refresh()

    def run_privileged(busy_message: str, action: Any, success_message: str) -> None:
        ctx.set_busy(True)
        ctx.set_status(busy_message)
        ctx.log(f"--- {busy_message} (pkexec) ---")

        def run() -> None:
            try:
                action()
                ctx.set_status(success_message)
                ctx.log(f"--- {success_message} ---")
                ctx.notify(success_message)
            except Exception as exc:
                ctx.set_status("Error")
                ctx.log(f"ERROR: {exc}")
                ctx.notify(str(exc))
            finally:
                ctx.set_busy(False)
                refresh()

        page.run_thread(run)

    def confirm_apply() -> None:
        if ctx.is_busy():
            ctx.notify("Espera a que termine la operación actual.")
            return
        source = image_path.value
        if not source:
            ctx.notify("Selecciona una imagen primero.")
            return
        if not Path(source).is_file():
            ctx.notify(f"El archivo no existe:\n{source}")
            return
        max_h = parse_height()
        if max_h is None:
            ctx.notify("Alto inválido: debe ser un número entero positivo.")
            return
        ctx.confirm_action(
            "Cambiar logo del login",
            "La imagen se copiará a /usr/share/plymotion y GDM la mostrará en lugar "
            "del logo de la distro. Se verá la próxima vez que aparezca la pantalla "
            "de login (al cerrar sesión o reiniciar).\n"
            "El sistema pedirá contraseña de administrador (pkexec).\n\n¿Continuar?",
            "Aplicar",
            lambda: run_privileged(
                "Aplicando logo del login...",
                lambda: login_logo.install_logo(Path(source), max_height=max_h),
                "Logo del login actualizado",
            ),
        )

    def confirm_restore() -> None:
        if ctx.is_busy():
            ctx.notify("Espera a que termine la operación actual.")
            return
        ctx.confirm_action(
            "Restaurar logo de la distro",
            "Se eliminará el logo personalizado y GDM volverá a mostrar el logo "
            "original de la distro.\n"
            "El sistema pedirá contraseña de administrador (pkexec).\n\n¿Continuar?",
            "Restaurar",
            lambda: run_privileged(
                "Restaurando logo de la distro...",
                login_logo.restore_default_logo,
                "Logo de la distro restaurado",
            ),
        )

    apply_btn = ft.FilledButton(
        "Aplicar logo", icon=ft.Icons.CHECK, on_click=lambda _e: confirm_apply()
    )
    restore_btn = ft.OutlinedButton(
        "Restaurar logo de la distro", icon=ft.Icons.RESTORE,
        on_click=lambda _e: confirm_restore(),
    )

    def on_busy(busy: bool) -> None:
        apply_btn.disabled = busy
        restore_btn.disabled = busy or not login_logo.is_custom_logo_installed()

    ctx.on_busy_change(on_busy)

    if not login_logo.gdm_available():
        apply_btn.disabled = True
        status_text.value = (
            f"No se encontró GDM ({login_logo.GDM_DCONF_DIR}). Esta función solo "
            "aplica a sistemas con la pantalla de login de GNOME."
        )

    refresh_current()

    picker_row = cast(
        "list[ft.Control]",
        [
            image_path,
            height,
            ft.FilledButton("Examinar", icon=ft.Icons.IMAGE, on_click=on_pick_image),
        ],
    )

    return ft.Column(
        expand=True,
        spacing=14,
        scroll=ft.ScrollMode.AUTO,
        controls=[
            ft.Text("Logo de la pantalla de login", size=20, weight=ft.FontWeight.BOLD),
            ft.Text(
                "Reemplaza el logo de la distro que GDM muestra abajo en la pantalla de "
                "login. GDM lo dibuja a su tamaño real en píxeles, así que la imagen se "
                "ajusta al alto elegido (el de Ubuntu mide 72 px). Usa un PNG con fondo "
                "transparente y colores claros: el fondo del login es oscuro.",
                size=12, color=ft.Colors.OUTLINE,
            ),
            ft.Row(picker_row),
            ft.Row(
                cast("list[ft.Control]", [current_panel, new_panel]),
                wrap=True, spacing=16, vertical_alignment=ft.CrossAxisAlignment.START,
            ),
            status_text,
            ft.Row(cast("list[ft.Control]", [apply_btn, restore_btn])),
        ],
    )
