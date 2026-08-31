"""Plymotion main GUI window."""

from __future__ import annotations

import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

from plymotion import __version__
from plymotion.ui.widgets import FilePicker, LabeledCombo, LogPanel, StatusBar

RESOLUTIONS = ["1920x1080", "1366x768", "1280x720", "2560x1440", "3840x2160"]
FPS_OPTIONS = ["15", "24", "30", "60"]


class PlymotionApp:
    """Main application window."""

    def __init__(self) -> None:
        self._root = tk.Tk()
        self._root.title(f"Plymotion v{__version__}")
        self._root.geometry("600x560")
        self._root.minsize(560, 480)
        self._root.protocol("WM_DELETE_WINDOW", self._on_close)

        self._converting = False
        self._output_dir: Path | None = None

        self._build_ui()

    def _build_ui(self) -> None:
        main = ttk.Frame(self._root, padding=15)
        main.pack(fill="both", expand=True)

        # Title
        ttk.Label(
            main,
            text="Plymotion - Video to Boot Splash",
            font=("sans-serif", 14, "bold"),
        ).pack(anchor="w", pady=(0, 10))

        # File picker
        self._file_picker = FilePicker(main, label="Video:", on_change=self._on_video_selected)
        self._file_picker.pack(fill="x", pady=(0, 10))

        # Options row
        opts = ttk.Frame(main)
        opts.pack(fill="x", pady=(0, 10))

        self._resolution = LabeledCombo(opts, "Resolución:", RESOLUTIONS, "1920x1080")
        self._resolution.pack(side="left", padx=(0, 15))

        self._fps = LabeledCombo(opts, "FPS:", FPS_OPTIONS, "30")
        self._fps.pack(side="left", padx=(0, 15))

        ttk.Label(opts, text="Nombre:").pack(side="left")
        self._theme_name = tk.StringVar(value="plymotion")
        ttk.Entry(opts, textvariable=self._theme_name, width=15).pack(side="left")

        # Progress
        self._progress = ttk.Progressbar(main, mode="determinate", length=400)
        self._progress.pack(fill="x", pady=(10, 5))

        # Log panel: step-by-step feedback (video info, conversion, install)
        ttk.Label(main, text="Registro:").pack(anchor="w")
        self._log = LogPanel(main, height=10)
        self._log.pack(fill="both", expand=True, pady=(2, 10))

        # Buttons
        btns = ttk.Frame(main)
        btns.pack(fill="x", pady=(0, 0))

        self._convert_btn = ttk.Button(
            btns, text="Convertir", command=self._on_convert
        )
        self._convert_btn.pack(side="left", padx=(0, 10))

        self._install_btn = ttk.Button(
            btns, text="Instalar", command=self._on_install, state="disabled"
        )
        self._install_btn.pack(side="left", padx=(0, 10))

        self._open_dir_btn = ttk.Button(
            btns, text="Abrir carpeta de salida", command=self._on_open_output_dir,
            state="disabled",
        )
        self._open_dir_btn.pack(side="left")

        # Status
        self._status = StatusBar(main)
        self._status.pack(fill="x", side="bottom", pady=(10, 0))

    def _on_video_selected(self, path: str) -> None:
        from plymotion.video_extractor import get_video_info

        self._log.append(f"Video seleccionado: {path}")
        try:
            info = get_video_info(Path(path))
            self._log.append(
                f"  Resolución original: {info['width']}x{info['height']}, "
                f"duración: {info['duration']}s"
            )
        except Exception as exc:
            self._log.append(f"  (No se pudo leer info del video: {exc})")

    def _on_convert(self) -> None:
        video = self._file_picker.get()
        if not video:
            messagebox.showwarning("Sin video", "Selecciona un archivo de video primero.")
            return

        if not Path(video).is_file():
            messagebox.showerror("Error", f"El archivo no existe:\n{video}")
            return

        self._converting = True
        self._convert_btn.configure(state="disabled")
        self._install_btn.configure(state="disabled")
        self._open_dir_btn.configure(state="disabled")
        self._progress["value"] = 0
        self._status.set("Iniciando conversión...")
        self._log.append("--- Iniciando conversión ---")

        thread = threading.Thread(target=self._run_convert, daemon=True)
        thread.start()

    def _run_convert(self) -> None:
        from plymotion.frame_processor import optimize_frames
        from plymotion.template_generator import generate_plymouth, generate_script
        from plymotion.video_extractor import extract_frames

        try:
            video = Path(self._file_picker.get())
            res = self._resolution.get()
            w, h = res.split("x")
            target_w, target_h = int(w), int(h)
            fps = int(self._fps.get())
            name = self._theme_name.get() or "plymotion"

            self._output_dir = video.parent / f"plymotion-{name}"

            # Frames are extracted directly into the theme dir (flat
            # layout), next to the .script/.plymouth files, so ImageDir
            # can point straight at the installed theme directory.
            # Step 1: Extract
            self._update_progress(0, "Extrayendo frames...")
            frame_count = extract_frames(video, self._output_dir, fps=fps)
            self._update_progress(33, f"Extraídos {frame_count} frames")

            # Step 2: Optimize
            self._update_progress(40, "Optimizando frames...")
            optimize_frames(self._output_dir, (target_w, target_h))
            self._update_progress(70, f"Optimizados a {target_w}x{target_h}")

            # Step 3: Generate theme files
            self._update_progress(80, "Generando archivos Plymouth...")
            script_path = self._output_dir / f"{name}-plymouth.script"
            plymouth_path = self._output_dir / f"{name}-plymouth.plymouth"
            image_dir = f"/usr/share/plymouth/themes/{name}"

            generate_script(script_path, frame_count, image_dir)
            generate_plymouth(plymouth_path, name, image_dir,
                              f"{image_dir}/{name}-plymouth.script")
            self._update_progress(100, f"Listo! Archivos en: {self._output_dir}")

            self._root.after(0, self._convert_done)

        except Exception as exc:
            msg = str(exc)
            self._root.after(0, lambda: self._convert_error(msg))

    def _update_progress(self, value: int, text: str) -> None:
        self._root.after(0, lambda: self._progress.configure(value=value))
        self._root.after(0, lambda: self._status.set(text))
        self._root.after(0, lambda: self._log.append(text))

    def _convert_done(self) -> None:
        self._converting = False
        self._convert_btn.configure(state="normal")
        self._install_btn.configure(state="normal")
        self._open_dir_btn.configure(state="normal")
        self._status.set("Conversión completada")
        self._log.append("--- Conversión completada ---")

    def _convert_error(self, msg: str) -> None:
        self._converting = False
        self._convert_btn.configure(state="normal")
        self._status.set("Error en la conversión")
        self._log.append(f"ERROR: {msg}")
        messagebox.showerror("Error", msg)

    def _on_install(self) -> None:
        if not self._output_dir or not self._output_dir.exists():
            messagebox.showwarning("Sin output", "Primero convierte un video.")
            return

        if not messagebox.askyesno(
            "Confirmar instalación",
            "Se hará backup del tema actual y se instalará el nuevo.\n"
            "El sistema pedirá contraseña de sudo.\n\n¿Continuar?",
        ):
            return

        self._install_btn.configure(state="disabled")
        self._status.set("Instalando theme...")
        self._log.append("--- Instalando theme (requiere sudo) ---")
        thread = threading.Thread(target=self._run_install, daemon=True)
        thread.start()

    def _run_install(self) -> None:
        from plymotion.installer import install_theme

        try:
            name = self._theme_name.get() or "plymotion"
            if self._output_dir is not None:
                install_theme(self._output_dir, theme_name=name)
            self._root.after(0, self._install_done)
        except Exception as exc:
            msg = str(exc)
            self._root.after(0, lambda: self._install_error(msg))

    def _install_done(self) -> None:
        self._install_btn.configure(state="normal")
        self._status.set("Theme instalado! Reinicia para verlo.")
        self._log.append("--- Theme instalado ---")
        messagebox.showinfo(
            "Instalado",
            "Theme instalado correctamente.\nReinicia el sistema para ver el nuevo boot splash.",
        )

    def _install_error(self, msg: str) -> None:
        self._install_btn.configure(state="normal")
        self._status.set("Error en la instalación")
        self._log.append(f"ERROR: {msg}")
        messagebox.showerror("Error de instalación", msg)

    def _on_open_output_dir(self) -> None:
        if not self._output_dir or not self._output_dir.exists():
            messagebox.showwarning("Sin output", "Primero convierte un video.")
            return

        try:
            if sys.platform == "darwin":
                subprocess.Popen(["open", str(self._output_dir)])
            elif sys.platform.startswith("win"):
                subprocess.Popen(["explorer", str(self._output_dir)])
            else:
                subprocess.Popen(["xdg-open", str(self._output_dir)])
        except Exception as exc:
            messagebox.showerror("Error", f"No se pudo abrir la carpeta:\n{exc}")

    def _on_close(self) -> None:
        if self._converting:
            if messagebox.askyesno("Salir", "Hay una conversión en curso. ¿Salir?"):
                self._root.destroy()
        else:
            self._root.destroy()

    def run(self) -> None:
        self._root.mainloop()
