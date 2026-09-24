"""Shared helpers for routers."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from fastapi import Request

from plymotion.api.schemas import JobAccepted, JobInfo
from plymotion.jobs import JobManager
from plymotion.services.progress import Reporter


class ApiException(Exception):
    """Raised by routers to return {code, message} with a status."""

    def __init__(self, status: int, code: str, message: str, detail: Any = None) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.detail = detail


def jobs(request: Request) -> JobManager:
    return request.app.state.jobs


def submit(
    request: Request,
    kind: str,
    title: str,
    fn: Callable[[Reporter], Any],
    *,
    lock: str | None = None,
    cancellable: bool = False,
) -> JobAccepted:
    """Start a job and return the 202 body. JobBusy is mapped to 409 by the app."""
    job = jobs(request).submit(kind, title, fn, lock=lock, cancellable=cancellable)
    return JobAccepted(job=JobInfo(**job.snapshot()))


def existing_file(raw: str, extensions: list[str], what: str) -> Path:
    path = Path(raw).expanduser()
    if not path.is_file():
        raise ApiException(400, "file_not_found", f"El archivo no existe: {path}")
    if path.suffix.lower().lstrip(".") not in extensions:
        raise ApiException(
            400, "unsupported_file", f"Formato no soportado para {what}: {path.name}"
        )
    return path.resolve()


SYSTEM_LOCK = "system"
CONVERT_LOCK = "convert"
