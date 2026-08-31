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
    page.window.height = 700
    page.window.min_width = 560
    page.window.min_height = 560
    page.padding = 20
    page.spacing = 14

    output_dir: dict[str, Path | None] = {"value": None}

    video_path = ft.TextField(label="Video o GIF", read_only=True, expand=True)
    theme_name = ft.TextField(label="Nombre del theme", value="plymotion", width=180)
    resolution = ft.Dropdown(
        label="Resolución", value="1920x1080",
        options=dropdown_options(RESOLUTIONS), width=170,
    )
    fps = ft.Dropdown(
        label="FPS", value="30",
        options=dropdown_options(FPS_OPTIONS), width=100,
    )
    trim_start_field = ft.TextField(label="Inicio (s)", value="0", width=100)
    trim_duration_field = ft.TextField(
        label="Duración (s, vacío = hasta el final)", width=220,
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

    # FilePicker is a "Service" control: it auto-registers itself against
    # this page just by being constructed (Service.init() does that). It
    # must NOT be added to page.overlay — that list is for visual controls,
    # and the client renderer doesn't know a "FilePicker" widget, which
    # surfaces as a red "Unknown control: FilePicker" error banner.
    file_picker = ft.FilePicker()

    async def on_pick_video(_e: Any) -> None:
        files = await file_picker.pick_files(
            dialog_title="Selecciona un video o GIF",
            file_type=ft.FilePickerFileType.CUSTOM,
            allowed_extensions=["mp4", "mkv", "webm", "avi", "mov", "m4v", "gif"],
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
        log(
            "  Sugerencia: el arranque/apagado real suele durar solo unos "
            "segundos, así que recortar a un clip corto (Inicio/Duración "
            "abajo) suele ser mejor que convertir el archivo completo."
        )

    # --- Button availability -------------------------------------------------
    # `available`: business-logic gating (e.g. "Instalar" needs a finished
    # conversion). `busy`: true while any background/privileged action is
    # running, and disables every action button regardless of `available`,
    # so two privileged operations (each its own pkexec prompt) never overlap.
    available = {
        "convert": True,
        "install": False,
        "open_dir": False,
        "preview": True,
        "restore": True,
        "reset": True,
    }
    busy = {"value": False}

    def apply_button_states() -> None:
        convert_btn.disabled = not available["convert"] or busy["value"]
        install_btn.disabled = not available["install"] or busy["value"]
        open_dir_btn.disabled = not available["open_dir"] or busy["value"]
        preview_btn.disabled = not available["preview"] or busy["value"]
        restore_btn.disabled = not available["restore"] or busy["value"]
        reset_btn.disabled = not available["reset"] or busy["value"]
        page.update()

    def set_available(**kwargs: bool) -> None:
        available.update(kwargs)
        apply_button_states()

    def set_busy(value: bool) -> None:
        busy["value"] = value
        apply_button_states()

    # --- Convert --------------------------------------------------------------

    def start_convert() -> None:
        video = video_path.value
        if not video:
            notify("Selecciona un video primero.")
            return
        if not Path(video).is_file():
            notify(f"El archivo no existe:\n{video}")
            return

        try:
            trim_start_val = float(trim_start_field.value or "0")
        except ValueError:
            notify("Inicio de recorte inválido: debe ser un número de segundos.")
            return
        trim_duration_val: float | None = None
        if trim_duration_field.value:
            try:
                trim_duration_val = float(trim_duration_field.value)
            except ValueError:
                notify("Duración de recorte inválida: debe ser un número de segundos.")
                return

        set_busy(True)
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
            trim_start_val,
            trim_duration_val,
        )

    def update_progress(value: int, text: str) -> None:
        progress.value = value / 100
        set_status(text)
        log(text)

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

            out_dir = video.parent / f"plymotion-{name}"
            output_dir["value"] = out_dir

            # Frames are extracted directly into the theme dir (flat
            # layout), next to the .script/.plymouth files, so ImageDir
            # can point straight at the installed theme directory.
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
            script_path = out_dir / f"{name}-plymouth.script"
            plymouth_path = out_dir / f"{name}-plymouth.plymouth"
            image_dir = f"/usr/share/plymouth/themes/{name}"

            generate_script(script_path, frame_count, image_dir)
            generate_plymouth(
                plymouth_path, name, image_dir, f"{image_dir}/{name}-plymouth.script"
            )
            loop_seconds = estimate_loop_seconds(frame_count)
            update_progress(
                100,
                f"Listo! {frame_count} frames ≈ {loop_seconds:.1f}s de reproducción "
                f"en loop (Plymouth refresca a ~50Hz, tasa fija). Archivos en: {out_dir}",
            )

            set_status("Conversión completada")
            log("--- Conversión completada ---")
            set_available(install=True, open_dir=True)

        except Exception as exc:
            set_status("Error en la conversión")
            log(f"ERROR: {exc}")
            notify(str(exc))
        finally:
            set_busy(False)

    # --- Privileged actions (install / preview / restore / reset) -------------
    # Each shows a confirmation dialog explaining what will happen and that a
    # graphical sudo (pkexec) prompt will appear, then runs in a background
    # thread so the pkexec prompt doesn't block the UI.

    def confirm_action(title: str, message: str, confirm_label: str, on_confirm: Any) -> None:
        def do_action(_e: Any) -> None:
            page.pop_dialog()
            on_confirm()

        def cancel(_e: Any) -> None:
            page.pop_dialog()

        actions = cast(
            "list[ft.Control]",
            [
                ft.TextButton("Cancelar", on_click=cancel),
                ft.FilledButton(confirm_label, on_click=do_action),
            ],
        )
        page.show_dialog(
            ft.AlertDialog(title=ft.Text(title), content=ft.Text(message), actions=actions)
        )

    def start_install() -> None:
        set_busy(True)
        set_status("Instalando theme...")
        log("--- Instalando theme (pkexec) ---")
        page.run_thread(run_install)

    def confirm_install() -> None:
        confirm_action(
            "Confirmar instalación",
            "Se hará backup del tema actual con este nombre y se instalará el "
            "nuevo.\nEl sistema pedirá contraseña de administrador (pkexec).\n\n"
            "¿Continuar?",
            "Instalar",
            start_install,
        )

    def run_install() -> None:
        from plymotion.installer import install_theme

        try:
            name = theme_name.value or "plymotion"
            src = output_dir["value"]
            if src is None:
                notify("Primero convierte un video.")
                return
            install_theme(src, theme_name=name)
            set_status("Theme instalado! Puedes probarlo abajo o reiniciar.")
            log("--- Theme instalado ---")
            notify("Theme instalado correctamente.")
            refresh_installed_themes()
        except Exception as exc:
            set_status("Error en la instalación")
            log(f"ERROR: {exc}")
            notify(str(exc))
        finally:
            set_busy(False)

    def start_preview() -> None:
        set_busy(True)
        set_status("Mostrando splash instalado...")
        log("--- Probando theme instalado (pkexec) ---")
        page.run_thread(run_preview)

    def confirm_preview() -> None:
        confirm_action(
            "Probar boot splash",
            "Se mostrará el splash del theme instalado actualmente durante "
            "unos segundos, sobre tu sesión en curso (la pantalla puede "
            "parpadear brevemente).\nEl sistema pedirá contraseña de "
            "administrador (pkexec).\n\n¿Continuar?",
            "Probar",
            start_preview,
        )

    def run_preview() -> None:
        from plymotion.installer import preview_installed_theme

        try:
            preview_installed_theme(seconds=6)
            set_status("Prueba finalizada")
            log("--- Prueba finalizada ---")
        except Exception as exc:
            set_status("Error al probar el theme")
            log(f"ERROR: {exc}")
            notify(str(exc))
        finally:
            set_busy(False)

    def start_restore() -> None:
        set_busy(True)
        set_status("Restaurando backup...")
        log("--- Restaurando backup (pkexec) ---")
        page.run_thread(run_restore)

    def confirm_restore() -> None:
        confirm_action(
            "Restaurar backup",
            "Se restaurará la copia de seguridad del theme "
            f"'{theme_name.value or 'plymotion'}' (si existe) y se "
            "regenerará el initramfs.\nEl sistema pedirá contraseña de "
            "administrador (pkexec).\n\n¿Continuar?",
            "Restaurar",
            start_restore,
        )

    def run_restore() -> None:
        from plymotion.installer import restore_backup

        try:
            name = theme_name.value or "plymotion"
            restored = restore_backup(name)
            if restored:
                set_status("Backup restaurado")
                log("--- Backup restaurado ---")
                notify("Backup restaurado correctamente.")
                refresh_installed_themes()
            else:
                set_status("No había backup que restaurar")
                log(f"No hay backup guardado para '{name}'.")
                notify(f"No hay backup guardado para '{name}'.")
        except Exception as exc:
            set_status("Error al restaurar")
            log(f"ERROR: {exc}")
            notify(str(exc))
        finally:
            set_busy(False)

    def start_reset() -> None:
        set_busy(True)
        set_status("Volviendo a modo texto...")
        log("--- Reseteando a modo texto (pkexec) ---")
        page.run_thread(run_reset)

    def confirm_reset() -> None:
        confirm_action(
            "Volver a modo texto",
            "Esto pone el theme de arranque en modo texto plano (el "
            "fallback más seguro de Plymouth) y regenera el initramfs.\n"
            "El sistema pedirá contraseña de administrador (pkexec).\n\n"
            "¿Continuar?",
            "Volver a texto",
            start_reset,
        )

    def run_reset() -> None:
        from plymotion.installer import reset_to_default

        try:
            reset_to_default()
            set_status("De vuelta en modo texto")
            log("--- Modo texto restaurado ---")
            notify("Boot splash en modo texto.")
            refresh_installed_themes()
        except Exception as exc:
            set_status("Error al resetear")
            log(f"ERROR: {exc}")
            notify(str(exc))
        finally:
            set_busy(False)

    # --- Installed themes ------------------------------------------------------

    installed_themes_view = ft.ListView(spacing=6, height=140)

    def refresh_installed_themes() -> None:
        from plymotion.installer import list_installed_themes

        installed_themes_view.controls.clear()
        try:
            themes = list_installed_themes()
        except Exception as exc:
            installed_themes_view.controls.append(
                ft.Text(f"No se pudo leer la lista de temas: {exc}", size=12)
            )
            page.update()
            return

        if not themes:
            installed_themes_view.controls.append(
                ft.Text("No se encontraron temas instalados.", italic=True, size=12)
            )
        for theme in themes:
            label = f"{'★ ' if theme.is_default else ''}{theme.name}"
            installed_themes_view.controls.append(
                ft.Column(
                    [
                        ft.Text(
                            label,
                            size=13,
                            weight=ft.FontWeight.BOLD if theme.is_default else None,
                        ),
                        ft.Text(theme.description or theme.directory.name, size=11, italic=True),
                    ],
                    spacing=0,
                )
            )
        page.update()

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

    convert_btn = ft.FilledButton(
        "Convertir", icon=ft.Icons.PLAY_ARROW, on_click=lambda _e: start_convert()
    )
    install_btn = ft.OutlinedButton(
        "Instalar", icon=ft.Icons.INSTALL_DESKTOP, on_click=lambda _e: confirm_install()
    )
    open_dir_btn = ft.TextButton(
        "Abrir carpeta de salida", icon=ft.Icons.FOLDER_OPEN,
        on_click=lambda _e: open_output_dir(),
    )
    preview_btn = ft.OutlinedButton(
        "Probar theme instalado", icon=ft.Icons.PLAY_CIRCLE_OUTLINE,
        on_click=lambda _e: confirm_preview(),
    )
    restore_btn = ft.OutlinedButton(
        "Restaurar backup", icon=ft.Icons.SETTINGS_BACKUP_RESTORE,
        on_click=lambda _e: confirm_restore(),
    )
    reset_btn = ft.TextButton(
        "Volver a modo texto", icon=ft.Icons.WARNING_AMBER,
        on_click=lambda _e: confirm_reset(),
    )

    apply_button_states()
    refresh_installed_themes()

    video_row = cast(
        "list[ft.Control]",
        [
            video_path,
            ft.FilledButton("Examinar", icon=ft.Icons.VIDEO_FILE, on_click=on_pick_video),
        ],
    )
    options_row = cast(
        "list[ft.Control]",
        [resolution, fps, theme_name, trim_start_field, trim_duration_field],
    )
    convert_row = cast("list[ft.Control]", [convert_btn, install_btn, open_dir_btn])
    system_row = cast("list[ft.Control]", [preview_btn, restore_btn, reset_btn])

    page.add(
        ft.Text("Plymotion - Video to Boot Splash", size=22, weight=ft.FontWeight.BOLD),
        ft.Row(video_row),
        ft.Row(options_row),
        progress,
        ft.Text("Registro:", weight=ft.FontWeight.W_500),
        log_container,
        ft.Row(convert_row),
        ft.Divider(),
        ft.Text("Sistema (requiere administrador):", weight=ft.FontWeight.W_500),
        ft.Row(system_row, wrap=True),
        ft.Divider(),
        ft.Row(
            cast(
                "list[ft.Control]",
                [
                    ft.Text("Temas instalados en el sistema:", weight=ft.FontWeight.W_500),
                    ft.IconButton(
                        icon=ft.Icons.REFRESH,
                        tooltip="Actualizar lista",
                        on_click=lambda _e: refresh_installed_themes(),
                    ),
                ],
            )
        ),
        ft.Container(
            content=installed_themes_view,
            border=ft.Border.all(width=1, color=ft.Colors.OUTLINE),
            border_radius=8,
            padding=10,
        ),
        status_text,
    )


def run(**kwargs: Any) -> None:
    """Launch the Flet app. Extra kwargs are forwarded to ft.run (e.g. view=...)."""
    ft.run(main, **kwargs)
