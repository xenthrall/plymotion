"""Convert view: pick a video/GIF, trim it, and generate a theme into the local library."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, cast

import flet as ft

from plymotion import library
from plymotion.ui.context import AppContext
from plymotion.ui.widgets import FPS_OPTIONS, RESOLUTIONS, dropdown_options

_ALLOWED_EXTENSIONS = ["mp4", "mkv", "webm", "avi", "mov", "m4v", "gif"]


def build_convert_view(ctx: AppContext) -> ft.Control:
    page = ctx.page

    video_path = ft.TextField(label="Video o GIF", read_only=True, expand=True)
    theme_name = ft.TextField(label="Nombre del theme", value="Mi theme", width=200)
    resolution = ft.Dropdown(
        label="Resolución", value="1920x1080", options=dropdown_options(RESOLUTIONS), width=170
    )
    fps = ft.Dropdown(label="FPS", value="30", options=dropdown_options(FPS_OPTIONS), width=100)
    trim_start_field = ft.TextField(label="Inicio (s)", value="0", width=100)
    trim_duration_field = ft.TextField(
        label="Duración (s, vacío = hasta el final)", width=260
    )

    progress = ft.ProgressBar(value=0)
    convert_status = ft.Text("Listo para convertir", italic=True, size=12)

    hint_text = ft.Text(
        "Selecciona un video o GIF para empezar.", size=12, color=ft.Colors.OUTLINE
    )

    # FilePicker is a "Service" control: it auto-registers itself against the
    # current page just by being constructed here (Service.init() does
    # that). It must NOT be added to page.overlay/content — that surfaces a
    # red "Unknown control: FilePicker" error banner in the client renderer.
    file_picker = ft.FilePicker()

    async def on_pick_video(_e: Any) -> None:
        files = await file_picker.pick_files(
            dialog_title="Selecciona un video o GIF",
            file_type=ft.FilePickerFileType.CUSTOM,
            allowed_extensions=_ALLOWED_EXTENSIONS,
        )
        if not files or not files[0].path:
            return
        video_path.value = files[0].path
        page.update()
        show_video_info(files[0].path)

    def show_video_info(path: str) -> None:
        from plymotion.video_extractor import get_video_info

        ctx.log(f"Video seleccionado: {path}")
        try:
            info = get_video_info(Path(path))
            hint_text.value = (
                f"Original: {info['width']}x{info['height']}, duración: {info['duration']}s. "
                "Recorta a un clip corto (Inicio/Duración): el arranque real suele durar solo "
                "unos segundos."
            )
        except Exception as exc:
            hint_text.value = f"(No se pudo leer info del video: {exc})"
        page.update()

    def load_video(path: str) -> None:
        video_path.value = path
        page.update()
        show_video_info(path)

    ctx.load_video_into_convert = load_video

    def start_convert() -> None:
        if ctx.is_busy():
            ctx.notify("Espera a que termine la operación actual.")
            return

        video = video_path.value
        if not video:
            ctx.notify("Selecciona un video primero.")
            return
        if not Path(video).is_file():
            ctx.notify(f"El archivo no existe:\n{video}")
            return

        try:
            trim_start_val = float(trim_start_field.value or "0")
        except ValueError:
            ctx.notify("Inicio de recorte inválido: debe ser un número de segundos.")
            return
        trim_duration_val: float | None = None
        if trim_duration_field.value:
            try:
                trim_duration_val = float(trim_duration_field.value)
            except ValueError:
                ctx.notify("Duración de recorte inválida: debe ser un número de segundos.")
                return

        ctx.set_busy(True)
        progress.value = 0
        convert_status.value = "Iniciando conversión..."
        ctx.set_status("Iniciando conversión...")
        ctx.log("--- Iniciando conversión ---")
        page.update()

        page.run_thread(
            run_convert,
            video,
            resolution.value or "1920x1080",
            fps.value or "30",
            theme_name.value or "plymotion",
            trim_start_val,
            trim_duration_val,
        )

    def update_progress(value: int, text: str) -> None:
        progress.value = value / 100
        convert_status.value = text
        ctx.set_status(text)
        ctx.log(text)
        page.update()

    def run_convert(
        video_str: str,
        resolution_str: str,
        fps_str: str,
        name: str,
        trim_start_val: float,
        trim_duration_val: float | None,
    ) -> None:
        from plymotion.frame_processor import optimize_frames
        from plymotion.template_generator import (
            estimate_loop_seconds,
            generate_plymouth,
            generate_script,
        )
        from plymotion.video_extractor import extract_frames

        try:
            video = Path(video_str)
            w, h = resolution_str.split("x")
            target_w, target_h = int(w), int(h)
            fps_val = int(fps_str)

            slug = library.unique_slug(name)
            out_dir = library.LIBRARY_THEMES_DIR / slug

            # Frames are extracted directly into the theme dir (flat
            # layout), next to the .script/.plymouth files, so ImageDir can
            # point straight at the eventual installed theme directory.
            update_progress(0, "Extrayendo frames...")
            frame_count = extract_frames(
                video, out_dir, fps=fps_val,
                start_time=trim_start_val, duration=trim_duration_val,
            )
            update_progress(33, f"Extraídos {frame_count} frames")

            update_progress(40, "Optimizando frames...")
            optimize_frames(out_dir, (target_w, target_h))
            update_progress(70, f"Optimizados a {target_w}x{target_h}")

            update_progress(80, "Generando archivos Plymouth...")
            script_path = out_dir / f"{slug}-plymouth.script"
            plymouth_path = out_dir / f"{slug}-plymouth.plymouth"
            image_dir = f"/usr/share/plymouth/themes/{slug}"

            generate_script(script_path, frame_count, image_dir)
            generate_plymouth(
                plymouth_path, name, image_dir, f"{image_dir}/{slug}-plymouth.script"
            )
            loop_seconds = estimate_loop_seconds(frame_count)
            library.save_manifest(
                out_dir,
                name=name,
                frame_count=frame_count,
                resolution=[target_w, target_h],
                fps=fps_val,
                loop_seconds=loop_seconds,
                source_video=str(video),
                trim_start=trim_start_val,
                trim_duration=trim_duration_val,
                created_at=datetime.now(timezone.utc).isoformat(),
            )

            update_progress(
                100,
                f"Listo! {frame_count} frames ≈ {loop_seconds:.1f}s de reproducción en loop "
                f"(Plymouth refresca a ~50Hz, tasa fija). Guardado en la galería como '{name}'.",
            )
            ctx.set_status("Conversión completada")
            ctx.log("--- Conversión completada ---")
            ctx.refresh_gallery()

        except Exception as exc:
            ctx.set_status("Error en la conversión")
            ctx.log(f"ERROR: {exc}")
            ctx.notify(str(exc))
        finally:
            ctx.set_busy(False)

    convert_btn = ft.FilledButton(
        "Convertir", icon=ft.Icons.PLAY_ARROW, on_click=lambda _e: start_convert()
    )
    ctx.on_busy_change(lambda busy: setattr(convert_btn, "disabled", busy))

    video_row = cast(
        "list[ft.Control]",
        [video_path, ft.FilledButton("Examinar", icon=ft.Icons.VIDEO_FILE, on_click=on_pick_video)],
    )
    options_row = cast(
        "list[ft.Control]",
        [resolution, fps, theme_name, trim_start_field, trim_duration_field],
    )

    return ft.Column(
        spacing=14,
        controls=[
            ft.Text("Convertir video o GIF", size=20, weight=ft.FontWeight.BOLD),
            ft.Row(video_row),
            hint_text,
            ft.Row(options_row, wrap=True),
            progress,
            convert_status,
            ft.Row([convert_btn]),
        ],
    )
