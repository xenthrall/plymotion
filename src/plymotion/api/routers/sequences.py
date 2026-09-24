"""Image sequence -> video/GIF ("Restaurar")."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse

from plymotion.api.deps import ApiException, existing_file, submit
from plymotion.api.routers.files import reveal
from plymotion.api.schemas import JobAccepted, SequenceOutput, SequenceRequest
from plymotion.core import image_sequence
from plymotion.services import sequence
from plymotion.services.progress import Reporter

router = APIRouter(prefix="/sequences", tags=["sequences"])


def _to_schema(path: Path) -> SequenceOutput:
    stat = path.stat()
    return SequenceOutput(
        filename=path.name, path=str(path), size_bytes=stat.st_size,
        created_at=datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
        url=f"/api/sequences/outputs/{path.name}",
    )


@router.post("", status_code=202, response_model=JobAccepted)
def build(body: SequenceRequest, request: Request) -> JobAccepted:
    images = [existing_file(p, sequence.IMAGE_EXTENSIONS, "imagen") for p in body.images]
    opts = sequence.SequenceOptions(images=images, name=body.name, output_format=body.format,
                                    fps=body.fps, max_width=body.max_width)
    try:
        opts.validate()
    except ValueError as exc:
        raise ApiException(400, "invalid_options", str(exc))

    def run(reporter: Reporter) -> dict[str, object]:
        return _to_schema(sequence.build(opts, reporter)).model_dump()

    return submit(request, "sequence", f"Crear {body.format.upper()} «{body.name}»", run)


@router.get("/outputs", response_model=list[SequenceOutput])
def list_outputs() -> list[SequenceOutput]:
    return [_to_schema(p) for p in sequence.list_outputs()]


def _output(filename: str) -> Path:
    path = sequence.output_path(filename)
    if path is None:
        raise ApiException(404, "output_not_found", "El archivo ya no existe.")
    return path


@router.get("/outputs/{filename}", response_class=FileResponse)
def get_output(filename: str) -> FileResponse:
    return FileResponse(_output(filename))


@router.delete("/outputs/{filename}", status_code=204)
def delete_output(filename: str) -> None:
    _output(filename).unlink()


@router.post("/outputs/reveal", status_code=204)
def reveal_outputs() -> None:
    image_sequence.RESTORED_DIR.mkdir(parents=True, exist_ok=True)
    reveal(image_sequence.RESTORED_DIR)
