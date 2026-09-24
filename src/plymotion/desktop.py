"""`plymotion` entry point: the API server plus a native window around the web client.

    plymotion              native window (pywebview, WebKitGTK)
    plymotion --browser    same server, opened in the default browser instead
    plymotion --dev        API only on :8765, for `npm run dev` in frontend/

The server listens on 127.0.0.1 only, on a free port, with a fresh session
token per launch (see plymotion/api/security.py). The window opens
/auth?token=..., which trades the token for an HttpOnly cookie.
"""

from __future__ import annotations

import argparse
import json
import socket
import sys
import threading
import time
import webbrowser
from pathlib import Path
from typing import Any

import uvicorn

from plymotion import __version__
from plymotion.api import ApiConfig, create_app
from plymotion.api.config import VITE_DEV_PORT
from plymotion.api.dialogs import default_dialogs, extensions_for

DEV_PORT = 8765
WINDOW_SIZE = (1320, 860)
MIN_SIZE = (960, 640)
# Matches the client's dark --background token, so the window doesn't flash white.
BACKGROUND = "#18181c"


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _ensure_system_gi() -> None:
    """Make the distro's PyGObject importable from the virtualenv.

    pywebview's GTK backend needs `gi`, which is normally installed by the
    distro (python3-gi) rather than pip, since building it needs the GTK dev
    headers. The venv doesn't see system site-packages, so append the
    distro's dist-packages last: venv packages still take precedence.
    """
    try:
        import gi  # noqa: F401  # pyright: ignore[reportMissingImports]

        return
    except ImportError:
        pass
    for candidate in (Path("/usr/lib/python3/dist-packages"),
                      Path(f"/usr/lib/python3.{sys.version_info.minor}/site-packages"),
                      Path(f"/usr/lib64/python3.{sys.version_info.minor}/site-packages")):
        if (candidate / "gi").is_dir():
            sys.path.append(str(candidate))
            return


class WebviewDialogs:
    """Native GTK file dialogs through the pywebview window."""

    def __init__(self) -> None:
        self.window: Any = None

    def pick(self, kind: str) -> list[str]:
        import webview

        if self.window is None:
            return []
        patterns = ";".join(f"*.{ext}" for ext in extensions_for(kind))
        label = "Videos y GIF" if kind == "video" else "Imágenes"
        result = self.window.create_file_dialog(
            webview.FileDialog.OPEN,
            allow_multiple=kind == "images",
            file_types=(f"{label} ({patterns})", "Todos los archivos (*.*)"),
        )
        return [str(p) for p in result or []]


class _Server:
    def __init__(self, config: ApiConfig, app: Any) -> None:
        self.server = uvicorn.Server(uvicorn.Config(
            app, host="127.0.0.1", port=config.port, log_level="warning", access_log=False,
        ))
        self.thread = threading.Thread(target=self.server.run, name="api", daemon=True)

    def start(self) -> None:
        self.thread.start()
        deadline = time.monotonic() + 10
        while not self.server.started:
            if not self.thread.is_alive() or time.monotonic() > deadline:
                raise RuntimeError("El servidor interno no pudo arrancar.")
            time.sleep(0.02)

    def stop(self) -> None:
        self.server.should_exit = True
        self.thread.join(timeout=5)


def _install_drop_bridge(window: Any) -> None:
    """Forward files dropped on the window to the client with their real paths.

    Page JS only ever sees a dropped file's name; pywebview's DOM events
    expose the full path (pywebviewFullPath), which is re-dispatched as the
    `plymotion:drop` event the client listens for (see frontend/src/lib/desktop.ts).
    """
    from webview.dom import DOMEventHandler

    def on_drop(event: dict[str, Any]) -> None:
        files = event.get("dataTransfer", {}).get("files", []) or []
        paths = [f["pywebviewFullPath"] for f in files if f.get("pywebviewFullPath")]
        if paths:
            detail = json.dumps(paths)
            window.evaluate_js(
                f"window.dispatchEvent(new CustomEvent('plymotion:drop', {{detail: {detail}}}))"
            )

    document = window.dom.document
    document.events.dragover += DOMEventHandler(lambda _e: None, prevent_default=True)
    document.events.drop += DOMEventHandler(on_drop, prevent_default=True)


def run_desktop(debug: bool = False) -> int:
    _ensure_system_gi()
    try:
        import webview
    except ImportError as exc:
        print(f"pywebview no está disponible ({exc}); abriendo en el navegador.", file=sys.stderr)
        return run_browser()

    dialogs = WebviewDialogs()
    config = ApiConfig(port=_free_port())
    server = _Server(config, create_app(config, dialogs=dialogs, desktop=True))
    server.start()

    window = webview.create_window(
        "Plymotion", config.auth_url(), width=WINDOW_SIZE[0], height=WINDOW_SIZE[1],
        min_size=MIN_SIZE, background_color=BACKGROUND, text_select=True,
    )
    if window is None:
        server.stop()
        return 1
    dialogs.window = window
    window.events.loaded += lambda: _install_drop_bridge(window)
    try:
        icon = Path(__file__).resolve().parent / "assets" / "plymotion.svg"
        webview.start(gui="gtk", debug=debug, icon=str(icon))
    except Exception as exc:  # noqa: BLE001 - e.g. WebKitGTK missing at runtime
        print(f"No se pudo abrir la ventana nativa ({exc}); usa `plymotion --browser`.",
              file=sys.stderr)
        server.stop()
        return 1
    server.stop()
    return 0


def run_browser() -> int:
    config = ApiConfig(port=_free_port())
    server = _Server(config, create_app(config, dialogs=default_dialogs()))
    server.start()
    url = config.auth_url()
    print(f"Plymotion en {url}\nCtrl+C para salir.")
    webbrowser.open(url)
    try:
        server.thread.join()
    except KeyboardInterrupt:
        server.stop()
    return 0


def run_dev() -> int:
    config = ApiConfig(port=DEV_PORT, dev=True, static_dir=None)
    app = create_app(config, dialogs=default_dialogs())
    print(
        "API de desarrollo en http://127.0.0.1:8765 (docs en /api/docs)\n"
        "1. En otra terminal: npm --prefix frontend run dev\n"
        f"2. Abre: {config.auth_url(f'http://localhost:{VITE_DEV_PORT}')}\n"
    )
    uvicorn.run(app, host="127.0.0.1", port=DEV_PORT, log_level="info")
    return 0


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="plymotion", description="Plymotion: animaciones de arranque a partir de videos."
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--browser", action="store_true", help="abrir en el navegador")
    mode.add_argument("--dev", action="store_true", help="solo la API, para el dev server de Vite")
    parser.add_argument("--debug", action="store_true", help="habilitar el inspector web")
    parser.add_argument("--version", action="version", version=f"plymotion {__version__}")
    args = parser.parse_args(argv)

    if args.dev:
        sys.exit(run_dev())
    if args.browser:
        sys.exit(run_browser())
    sys.exit(run_desktop(debug=args.debug))


if __name__ == "__main__":
    main()
