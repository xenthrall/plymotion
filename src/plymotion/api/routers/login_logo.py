"""GDM login screen logo."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse

from plymotion.api.deps import SYSTEM_LOCK, ApiException, existing_file, submit
from plymotion.api.schemas import JobAccepted, LoginLogoState, LogoPreview, LogoPreviewRequest
from plymotion.core import login_logo
from plymotion.services import login_logo as logo_service
from plymotion.services.progress import Reporter

router = APIRouter(prefix="/login-logo", tags=["login-logo"])


@router.get("", response_model=LoginLogoState)
def state() -> LoginLogoState:
    current, custom = logo_service.current_logo()
    return LoginLogoState(
        gdm_available=login_logo.gdm_available(),
        custom_installed=custom,
        current_url="/api/login-logo/current" if current else None,
        default_height=login_logo.DEFAULT_LOGO_HEIGHT,
        max_width=login_logo.MAX_LOGO_WIDTH,
    )


@router.get("/current", response_class=FileResponse)
def current() -> FileResponse:
    path, _ = logo_service.current_logo()
    if path is None:
        raise ApiException(404, "no_logo", "No hay un logo configurado.")
    return FileResponse(path, headers={"Cache-Control": "no-cache"})


@router.post("/preview", response_model=LogoPreview)
def make_preview(body: LogoPreviewRequest) -> LogoPreview:
    source = existing_file(body.path, logo_service.IMAGE_EXTENSIONS, "logo")
    try:
        preview = logo_service.make_preview(source, body.max_height)
    except (ValueError, OSError) as exc:
        raise ApiException(400, "invalid_image", f"No se pudo procesar la imagen: {exc}")
    return LogoPreview(url=f"/api/login-logo/previews/{preview.id}",
                       width=preview.width, height=preview.height)


@router.get("/previews/{preview_id}", response_class=FileResponse)
def preview_file(preview_id: str) -> FileResponse:
    path = logo_service.preview_path(preview_id)
    if path is None:
        raise ApiException(404, "preview_not_found", "La vista previa ya no existe.")
    return FileResponse(path, media_type="image/png")


@router.post("/apply", status_code=202, response_model=JobAccepted)
def apply(body: LogoPreviewRequest, request: Request) -> JobAccepted:
    if not login_logo.gdm_available():
        raise ApiException(409, "no_gdm", "GDM no está disponible en este sistema.")
    source = existing_file(body.path, logo_service.IMAGE_EXTENSIONS, "logo")

    def run(reporter: Reporter) -> dict[str, int]:
        reporter.progress(None, "Esperando autorización (pkexec)")
        reporter.log(f"Aplicando {source.name} como logo del login ({body.max_height} px de alto)")
        width, height = login_logo.install_logo(source, max_height=body.max_height)
        reporter.log(f"Logo instalado ({width}x{height}). Se verá en el próximo login.")
        return {"width": width, "height": height}

    return submit(request, "login-logo", "Aplicar logo del login", run, lock=SYSTEM_LOCK)


@router.post("/restore", status_code=202, response_model=JobAccepted)
def restore(request: Request) -> JobAccepted:
    def run(reporter: Reporter) -> None:
        reporter.progress(None, "Esperando autorización (pkexec)")
        reporter.log("Quitando el logo de Plymotion; GDM vuelve al de la distro")
        login_logo.restore_default_logo()

    return submit(request, "login-logo-restore", "Restaurar logo de la distro", run,
                  lock=SYSTEM_LOCK)
