"""Job status, cancellation and the live event stream (SSE)."""

from __future__ import annotations

import asyncio
import contextlib
import json
from collections.abc import AsyncIterator
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from plymotion.api.deps import ApiException, jobs
from plymotion.api.schemas import JobDetail, JobInfo

router = APIRouter(tags=["jobs"])

HEARTBEAT_SECONDS = 15


@router.get("/jobs", response_model=list[JobInfo])
def list_jobs(request: Request) -> list[JobInfo]:
    return [JobInfo(**job.snapshot()) for job in jobs(request).list()]


@router.get("/jobs/{job_id}", response_model=JobDetail)
def get_job(job_id: str, request: Request) -> JobDetail:
    job = jobs(request).get(job_id)
    if job is None:
        raise ApiException(404, "job_not_found", "La tarea no existe.")
    return JobDetail(**job.snapshot(), logs=list(job.logs))


@router.delete("/jobs/{job_id}", status_code=202, response_model=JobInfo)
def cancel_job(job_id: str, request: Request) -> JobInfo:
    manager = jobs(request)
    job = manager.get(job_id)
    if job is None:
        raise ApiException(404, "job_not_found", "La tarea no existe.")
    if not manager.cancel(job_id):
        raise ApiException(409, "not_cancellable", "Esta tarea no se puede cancelar.")
    return JobInfo(**job.snapshot())


def _sse(event: str, data: Any) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


@router.get("/events", response_class=StreamingResponse)
async def events(request: Request) -> StreamingResponse:
    """One stream for everything: a `snapshot` of all jobs, then `job` and `log` events."""

    async def stream() -> AsyncIterator[str]:
        subscription = jobs(request).subscribe()
        next_event = asyncio.ensure_future(anext(subscription))
        try:
            while True:
                done, _ = await asyncio.wait({next_event}, timeout=HEARTBEAT_SECONDS)
                if await request.is_disconnected():
                    break
                if not done:
                    yield ": ping\n\n"
                    continue
                message = next_event.result()
                yield _sse(message["event"], message["data"])
                next_event = asyncio.ensure_future(anext(subscription))
        finally:
            next_event.cancel()
            with contextlib.suppress(asyncio.CancelledError, StopAsyncIteration):
                await next_event
            await subscription.aclose()

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
