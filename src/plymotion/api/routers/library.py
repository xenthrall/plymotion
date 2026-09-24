"""Local theme library (gallery)."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse

from plymotion.api.deps import SYSTEM_LOCK, ApiException, submit
from plymotion.api.routers.files import reveal
from plymotion.api.schemas import BootLogoRequest, JobAccepted, LibraryTheme
from plymotion.core import library
from plymotion.core.template_generator import WATERMARK_FILENAME
from plymotion.services import boot_logo, themes
from plymotion.services.progress import Reporter

router = APIRouter(tags=["library"])


def to_library_theme(theme: library.LibraryTheme, installed: bool) -> LibraryTheme:
    base = f"/api/library/{theme.slug}/frames"
    return LibraryTheme(
        slug=theme.slug, name=theme.name, frame_count=theme.frame_count,
        width=theme.resolution[0], height=theme.resolution[1], fps=theme.fps,
        colors=theme.colors, loop_seconds=theme.loop_seconds, total_bytes=theme.total_bytes,
        source_video=theme.source_video, created_at=theme.created_at, installed=installed,
        thumbnail_url=f"{base}/1" if theme.thumbnail else None,
        frame_url_template=f"{base}/{{n}}",
        boot_logo=theme.boot_logo,
        watermark_url=f"/api/library/{theme.slug}/watermark" if theme.boot_logo else None,
    )


def _require(slug: str) -> library.LibraryTheme:
    try:
        return themes.require_library_theme(slug)
    except themes.NotFound as exc:
        raise ApiException(404, "theme_not_found", str(exc))


@router.get("/library", response_model=list[LibraryTheme])
def list_library() -> list[LibraryTheme]:
    installed = themes.installed_slugs()
    items = sorted(library.list_library_themes(), key=lambda t: t.created_at, reverse=True)
    return [to_library_theme(t, t.slug in installed) for t in items]


@router.get("/library/{slug}", response_model=LibraryTheme)
def get_library_theme(slug: str) -> LibraryTheme:
    theme = _require(slug)
    return to_library_theme(theme, theme.slug in themes.installed_slugs())


@router.delete("/library/{slug}", status_code=204)
def delete_library_theme(slug: str) -> None:
    library.delete_library_theme(_require(slug).slug)


@router.get("/library/{slug}/frames/{index}", response_class=FileResponse)
def library_frame(slug: str, index: int) -> FileResponse:
    theme = _require(slug)
    try:
        path = themes.frame_path(theme.directory, index)
    except themes.NotFound as exc:
        raise ApiException(404, "frame_not_found", str(exc))
    # Frames never change once a theme is generated (a re-conversion gets a
    # new slug), so the client can cache them hard.
    return FileResponse(path, media_type="image/png",
                        headers={"Cache-Control": "private, max-age=86400, immutable"})


@router.get("/library/{slug}/watermark", response_class=FileResponse)
def library_watermark(slug: str) -> FileResponse:
    path = _require(slug).directory / WATERMARK_FILENAME
    if not path.is_file():
        raise ApiException(404, "no_boot_logo", "Este tema no tiene logo de arranque.")
    return FileResponse(path, media_type="image/png", headers={"Cache-Control": "no-cache"})


@router.post("/library/{slug}/boot-logo", response_model=LibraryTheme)
def set_boot_logo(slug: str, body: BootLogoRequest) -> LibraryTheme:
    """Add the current login logo to a theme's boot splash, or remove it (library copy only)."""
    theme = _require(slug)
    try:
        updated = boot_logo.set_library_boot_logo(theme.slug, body.enabled)
    except ValueError as exc:
        raise ApiException(409, "no_login_logo", str(exc))
    return to_library_theme(updated, updated.slug in themes.installed_slugs())


@router.post("/library/{slug}/install", status_code=202, response_model=JobAccepted)
def install(slug: str, request: Request) -> JobAccepted:
    theme = _require(slug)

    def run(reporter: Reporter) -> None:
        themes.install_from_library(theme.slug, reporter)

    return submit(request, "install", f"Instalar «{theme.name}»", run, lock=SYSTEM_LOCK)


@router.post("/library/{slug}/reveal", status_code=204)
def reveal_theme(slug: str) -> None:
    reveal(_require(slug).directory)
