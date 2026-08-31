"""Plymotion main GUI window (Flet)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any, cast

import flet as ft

from plymotion import __version__
from plymotion.ui.widgets import FPS_OPTIONS, RESOLUTIONS, append_log, dropdown_options


async def main(page: ft.Page) -> None:
    """Build and wire up the Plymotion window for a single Flet session."""
    page.title = f"Plymotion v{__version__}"
    page.theme_mode = ft.ThemeMode.SYSTEM
    page.window.width = 640
    page.window.height = 640
    page.window.min_width = 560
    page.window.min_height = 520
    page.padding = 20
    page.spacing = 14

    output_dir: dict[str, Path | None] = {"value": None}

    video_path = ft.TextField(label="Video", read_only=True, expand=True)
    theme_name = ft.TextField(label="Nombre del theme", value="plymotion", width=180)
    resolution = ft.Dropdown(
        label="Resolución", value="1920x1080",
        options=dropdown_options(RESOLUTIONS), width=170,
    )
    fps = ft.Dropdown(
        label="FPS", value="30",
        options=dropdown_options(FPS_OPTIONS), width=100,
    )

    progress = ft.ProgressBar(value=0)
    status_text = ft.Text("Listo", italic=True)

    log_view = ft.ListView(expand=True, spacing=2, auto_scroll=True)
    log_container = ft.Container(
        content=log_view,
        border=ft.Border.all(width=1, color=ft.Colors.OUTLINE),
        border_radius=8,
        padding=10,
        expand=True,
    )

    def log(line: str) -> None:
        append_log(log_view, line)
        page.update()

    def notify(text: str) -> None:
        page.show_dialog(ft.SnackBar(ft.Text(text), open=True))

    def set_status(text: str) -> None:
        status_text.value = text
        page.update()

    file_picker = ft.FilePicker()
    page.overlay.append(file_picker)

    async def on_pick_video(_e: Any) -> None:
        files = await file_picker.pick_files(
            dialog_title="Selecciona un video",
            file_type=ft.FilePickerFileType.VIDEO,
        )
        if not files or not files[0].path:
            return
        video_path.value = files[0].path
        page.update()
        show_video_info(files[0].path)

    def show_video_info(path: str) -> None:
        from plymotion.video_extractor import get_video_info

        log(f"Video seleccionado: {path}")
        try:
            info = get_video_info(Path(path))
            log(
                f"  Resolución original: {info['width']}x{info['height']}, "
                f"duración: {info['duration']}s"
            )
        except Exception as exc:
            log(f"  (No se pudo leer info del video: {exc})")

    convert_btn = ft.FilledButton(
        "Convertir", icon=ft.Icons.PLAY_ARROW, on_click=lambda _e: start_convert()
    )
    install_btn = ft.OutlinedButton(
        "Instalar", icon=ft.Icons.INSTALL_DESKTOP,
        on_click=lambda _e: confirm_install(), disabled=True,
    )
    open_dir_btn = ft.TextButton(
        "Abrir carpeta de salida", icon=ft.Icons.FOLDER_OPEN,
        on_click=lambda _e: open_output_dir(), disabled=True,
    )

    def set_buttons(
        *,
        convert: bool | None = None,
        install: bool | None = None,
        open_dir: bool | None = None,
    ) -> None:
        if convert is not None:
            convert_btn.disabled = not convert
        if install is not None:
            install_btn.disabled = not install
        if open_dir is not None:
            open_dir_btn.disabled = not open_dir
        page.update()

    def start_convert() -> None:
        video = video_path.value
        if not video:
            notify("Selecciona un video primero.")
            return
        if not Path(video).is_file():
            notify(f"El archivo no existe:\n{video}")
            return

        set_buttons(convert=False, install=False, open_dir=False)
        progress.value = 0
        set_status("Iniciando conversión...")
        log("--- Iniciando conversión ---")

        # Snapshot form values now: the background thread must not read
        # widget state that the user could change mid-conversion.
        page.run_thread(
            run_convert,
            video,
            resolution.value or "1920x1080",
            fps.value or "30",
            theme_name.value or "plymotion",
        )

    def update_progress(value: int, text: str) -> None:
        progress.value = value / 100
        set_status(text)
        log(text)

    def run_convert(video_str: str, resolution_str: str, fps_str: str, name: str) -> None:
        from plymotion.frame_processor import optimize_frames
        from plymotion.template_generator import generate_plymouth, generate_script
        from plymotion.video_extractor import extract_frames

        try:
            video = Path(video_str)
            w, h = resolution_str.split("x")
            target_w, target_h = int(w), int(h)
            fps_val = int(fps_str)

            out_dir = video.parent / f"plymotion-{name}"
            output_dir["value"] = out_dir

            # Frames are extracted directly into the theme dir (flat
            # layout), next to the .script/.plymouth files, so ImageDir
            # can point straight at the installed theme directory.
            update_progress(0, "Extrayendo frames...")
            frame_count = extract_frames(video, out_dir, fps=fps_val)
            update_progress(33, f"Extraídos {frame_count} frames")

            update_progress(40, "Optimizando frames...")
            optimize_frames(out_dir, (target_w, target_h))
            update_progress(70, f"Optimizados a {target_w}x{target_h}")

            update_progress(80, "Generando archivos Plymouth...")
            script_path = out_dir / f"{name}-plymouth.script"
            plymouth_path = out_dir / f"{name}-plymouth.plymouth"
            image_dir = f"/usr/share/plymouth/themes/{name}"

            generate_script(script_path, frame_count, image_dir)
            generate_plymouth(
                plymouth_path, name, image_dir, f"{image_dir}/{name}-plymouth.script"
            )
            update_progress(100, f"Listo! Archivos en: {out_dir}")

            set_buttons(convert=True, install=True, open_dir=True)
            set_status("Conversión completada")
            log("--- Conversión completada ---")

        except Exception as exc:
            set_buttons(convert=True, install=False, open_dir=False)
            set_status("Error en la conversión")
            log(f"ERROR: {exc}")
            notify(str(exc))

    def confirm_install() -> None:
        def do_install(_e: Any) -> None:
            page.pop_dialog()
            set_buttons(install=False)
            set_status("Instalando theme...")
            log("--- Instalando theme (requiere sudo) ---")
            page.run_thread(run_install)

        def cancel(_e: Any) -> None:
            page.pop_dialog()

        actions = cast(
            "list[ft.Control]",
            [
                ft.TextButton("Cancelar", on_click=cancel),
                ft.FilledButton("Continuar", on_click=do_install),
            ],
        )
        page.show_dialog(
            ft.AlertDialog(
                title=ft.Text("Confirmar instalación"),
                content=ft.Text(
                    "Se hará backup del tema actual y se instalará el nuevo.\n"
                    "El sistema pedirá contraseña de sudo.\n\n¿Continuar?"
                ),
                actions=actions,
            )
        )

    def run_install() -> None:
        from plymotion.installer import install_theme

        try:
            name = theme_name.value or "plymotion"
            src = output_dir["value"]
            if src is not None:
                install_theme(src, theme_name=name)
            set_status("Theme instalado! Reinicia para verlo.")
            log("--- Theme instalado ---")
            set_buttons(install=True)
            notify("Theme instalado correctamente. Reinicia para verlo.")
        except Exception as exc:
            set_status("Error en la instalación")
            log(f"ERROR: {exc}")
            set_buttons(install=True)
            notify(str(exc))

    def open_output_dir() -> None:
        src = output_dir["value"]
        if not src or not src.exists():
            notify("Primero convierte un video.")
            return
        try:
            if sys.platform == "darwin":
                subprocess.Popen(["open", str(src)])
            elif sys.platform.startswith("win"):
                subprocess.Popen(["explorer", str(src)])
            else:
                subprocess.Popen(["xdg-open", str(src)])
        except Exception as exc:
            notify(f"No se pudo abrir la carpeta:\n{exc}")

    video_row = cast(
        "list[ft.Control]",
        [
            video_path,
            ft.FilledButton("Examinar", icon=ft.Icons.VIDEO_FILE, on_click=on_pick_video),
        ],
    )
    options_row = cast("list[ft.Control]", [resolution, fps, theme_name])
    buttons_row = cast("list[ft.Control]", [convert_btn, install_btn, open_dir_btn])

    page.add(
        ft.Text("Plymotion - Video to Boot Splash", size=22, weight=ft.FontWeight.BOLD),
        ft.Row(video_row),
        ft.Row(options_row),
        progress,
        ft.Text("Registro:", weight=ft.FontWeight.W_500),
        log_container,
        ft.Row(buttons_row),
        status_text,
    )


def run(**kwargs: Any) -> None:
    """Launch the Flet app. Extra kwargs are forwarded to ft.run (e.g. view=...)."""
    ft.run(main, **kwargs)
