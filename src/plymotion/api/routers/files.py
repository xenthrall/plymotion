"""Native file dialogs, local media streaming and "show in folder"."""

from __future__ import annotations

import asyncio
import shutil
import subprocess
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse

from plymotion.api.deps import ApiException, existing_file
from plymotion.api.schemas import PickRequest, PickResult
from plymotion.services.convert import VIDEO_EXTENSIONS
from plymotion.services.login_logo import IMAGE_EXTENSIONS

router = APIRouter(tags=["files"])

MEDIA_EXTENSIONS = VIDEO_EXTENSIONS + IMAGE_EXTENSIONS


@router.post("/dialogs/pick", response_model=PickResult)
async def pick(body: PickRequest, request: Request) -> PickResult:
    dialogs = request.app.state.dialogs
    if dialogs is None:
        raise ApiException(501, "no_dialogs", "No hay diálogo nativo disponible: escribe la ruta.")
    paths = await asyncio.to_thread(dialogs.pick, body.kind)
    return PickResult(paths=paths)


@router.get("/media", response_class=FileResponse)
def media(path: str) -> FileResponse:
    """Stream a local video/image the user picked (Range requests supported for <video>)."""
    return FileResponse(existing_file(path, MEDIA_EXTENSIONS, "vista previa"))


def reveal(path: Path) -> None:
    """Open `path` (a directory, or a file's directory) in the file manager."""
    target = path if path.is_dir() else path.parent
    opener = shutil.which("gio")
    cmd = [opener, "open", str(target)] if opener else ["xdg-open", str(target)]
    try:
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         start_new_session=True)
    except OSError as exc:
        raise ApiException(500, "reveal_failed", f"No se pudo abrir el gestor de archivos: {exc}")
