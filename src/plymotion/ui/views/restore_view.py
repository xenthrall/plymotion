"""Restore view: a standalone tool (separate from the theme workflow) that
turns a picked sequence of still images back into a video or GIF, which can
then be picked up in the Convertir view like any other source file.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import flet as ft

from plymotion import image_sequence
from plymotion.sorting import natural_sort_key
from plymotion.ui.context import AppContext
from plymotion.ui.os_utils import open_in_file_manager
from plymotion.ui.widgets import FPS_OPTIONS, dropdown_options

_ALLOWED_EXTENSIONS = ["png", "jpg", "jpeg", "bmp", "webp", "tif", "tiff"]
_FORMATS = ["MP4", "GIF"]


def build_restore_view(ctx: AppContext) -> ft.Control:
    page = ctx.page

    picked_images: dict[str, list[Path]] = {"value": []}
    last_output: dict[str, Path | None] = {"value": None}

    images_summary = ft.Text(
        "Selecciona una secuencia de imágenes para empezar.", size=12, color=ft.Colors.OUTLINE
    )
    output_name = ft.TextField(label="Nombre de salida", value="video-restaurado", width=220)
    output_format = ft.Dropdown(
        label="Formato", value="MP4", width=110, options=dropdown_options(_FORMATS)
    )
    fps = ft.Dropdown(label="FPS", value="24", options=dropdown_options(FPS_OPTIONS), width=100)
    max_width_field = ft.TextField(label="Ancho máx (px, opcional)", width=200)

    progress = ft.ProgressBar(visible=False)
    status = ft.Text("", italic=True, size=12)

    open_folder_btn = ft.OutlinedButton(
        "Abrir carpeta", icon=ft.Icons.FOLDER_OPEN,
        on_click=lambda _e: last_output["value"] and open_in_file_manager(
            cast(Path, last_output["value"]).parent
        ),
    )
    use_in_convert_btn = ft.FilledButton(
        "Usar en Convertir", icon=ft.Icons.ARROW_FORWARD,
        on_click=lambda _e: _use_in_convert(),
    )
    result_row = ft.Row([open_folder_btn, use_in_convert_btn], visible=False)

    def _use_in_convert() -> None:
        output = last_output["value"]
        if output is None:
            return
        ctx.load_video_into_convert(str(output))
        ctx.switch_view(0)

    file_picker = ft.FilePicker()

    async def on_pick_images(_e: Any) -> None:
        files = await file_picker.pick_files(
            dialog_title="Selecciona la secuencia de imágenes",
            file_type=ft.FilePickerFileType.CUSTOM,
            allowed_extensions=_ALLOWED_EXTENSIONS,
            allow_multiple=True,
        )
        if not files:
            return
        paths = sorted((Path(f.path) for f in files if f.path), key=natural_sort_key)
        picked_images["value"] = paths
        images_summary.value = (
            f"{len(paths)} imágenes seleccionadas, en orden natural "
            f"(de '{paths[0].name}' a '{paths[-1].name}')."
        )
        ctx.log(f"Secuencia seleccionada: {len(paths)} imágenes.")
        page.update()

    def start_build() -> None:
        if ctx.is_busy():
            ctx.notify("Espera a que termine la operación actual.")
            return

        images = picked_images["value"]
        if not images:
            ctx.notify("Selecciona primero una secuencia de imágenes.")
            return

        try:
            fps_val = int(fps.value or "24")
        except ValueError:
            ctx.notify("FPS inválido.")
            return

        max_width_val: int | None = None
        if max_width_field.value:
            try:
                max_width_val = int(max_width_field.value)
            except ValueError:
                ctx.notify("Ancho máximo inválido: debe ser un número de píxeles.")
                return

        name = output_name.value or "video-restaurado"
        extension = ".gif" if output_format.value == "GIF" else ".mp4"

        ctx.set_busy(True)
        progress.visible = True
        status.value = "Generando video desde las imágenes..."
        result_row.visible = False
        ctx.set_status("Restaurando video...")
        ctx.log(f"--- Restaurando video desde {len(images)} imágenes ---")
        page.update()

        page.run_thread(run_build, list(images), name, extension, fps_val, max_width_val)

    def run_build(
        images: list[Path], name: str, extension: str, fps_val: int, max_width_val: int | None
    ) -> None:
        try:
            output_path = image_sequence.unique_output_path(name, extension)
            image_sequence.build_video_from_images(
                images, output_path, fps=fps_val, max_width=max_width_val
            )
            last_output["value"] = output_path
            status.value = f"Listo! Guardado en: {output_path}"
            ctx.set_status("Video restaurado")
            ctx.log(f"--- Video generado: {output_path} ---")
            result_row.visible = True
        except Exception as exc:
            status.value = "Error al generar el video."
            ctx.set_status("Error al restaurar video")
            ctx.log(f"ERROR: {exc}")
            ctx.notify(str(exc))
        finally:
            progress.visible = False
            ctx.set_busy(False)
            page.update()

    build_btn = ft.FilledButton(
        "Generar video", icon=ft.Icons.MOVIE_FILTER, on_click=lambda _e: start_build()
    )
    ctx.on_busy_change(lambda busy: setattr(build_btn, "disabled", busy))

    pick_row = cast(
        "list[ft.Control]",
        [
            ft.FilledButton(
                "Seleccionar imágenes", icon=ft.Icons.BURST_MODE, on_click=on_pick_images
            ),
            images_summary,
        ],
    )
    options_row = cast(
        "list[ft.Control]", [output_name, output_format, fps, max_width_field]
    )

    return ft.Column(
        spacing=14,
        controls=[
            ft.Text("Restaurar video desde imágenes", size=20, weight=ft.FontWeight.BOLD),
            ft.Text(
                "Herramienta aparte: toma una secuencia de imágenes sueltas y genera un "
                "video o GIF a partir de ellas. Útil cuando ya tienes los frames "
                "extraídos de otra fuente. El resultado se puede enviar directo a "
                "Convertir para generar un theme.",
                size=12, color=ft.Colors.OUTLINE,
            ),
            ft.Row(pick_row),
            ft.Row(options_row, wrap=True),
            ft.Row([build_btn]),
            progress,
            status,
            result_row,
        ],
    )
