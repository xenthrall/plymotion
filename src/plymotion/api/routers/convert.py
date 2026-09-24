"""Video inspection, estimates and conversion jobs."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, Request

from plymotion.api.deps import CONVERT_LOCK, ApiException, existing_file, submit
from plymotion.api.routers.library import to_library_theme
from plymotion.api.schemas import (
    ConvertRequest,
    Estimate,
    EstimateRequest,
    JobAccepted,
    PathRequest,
    VideoInfo,
)
from plymotion.core.video_extractor import get_video_info
from plymotion.services import convert as convert_service
from plymotion.services.progress import Reporter

router = APIRouter(tags=["convert"])


@router.post("/videos/inspect", response_model=VideoInfo)
def inspect_video(body: PathRequest) -> VideoInfo:
    path = existing_file(body.path, convert_service.VIDEO_EXTENSIONS, "video")
    try:
        info = get_video_info(path)
    except RuntimeError as exc:
        raise ApiException(422, "unreadable_video", f"No se pudo leer el video: {exc}")
    return VideoInfo(
        path=str(path), name=path.name, width=info.width, height=info.height,
        duration=info.duration, fps=info.fps, codec=info.codec, size_bytes=info.size_bytes,
        media_url=f"/api/media?path={quote(str(path))}",
    )


@router.post("/convert/estimate", response_model=Estimate)
def estimate(body: EstimateRequest) -> Estimate:
    result = convert_service.estimate(body.duration, body.fps, body.trim_start, body.trim_duration)
    return Estimate(**result.__dict__)


@router.post("/convert", status_code=202, response_model=JobAccepted)
def start_convert(body: ConvertRequest, request: Request) -> JobAccepted:
    path = existing_file(body.path, convert_service.VIDEO_EXTENSIONS, "video")
    opts = convert_service.ConvertOptions(
        video=Path(path), name=body.name.strip(), max_width=body.max_width,
        max_height=body.max_height, fps=body.fps, colors=body.colors,
        trim_start=body.trim_start, trim_duration=body.trim_duration,
    )
    try:
        opts.validate()
    except ValueError as exc:
        raise ApiException(400, "invalid_options", str(exc))

    def run(reporter: Reporter) -> dict[str, object]:
        theme = convert_service.convert_video(opts, reporter)
        return to_library_theme(theme, installed=False).model_dump()

    return submit(request, "convert", f"Convertir «{opts.name}»", run,
                  lock=CONVERT_LOCK, cancellable=True)
