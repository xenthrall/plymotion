"""In-process job manager.

Every long operation (conversion, pkexec actions, ffmpeg builds) runs in a
worker thread as a Job. State changes and log lines are published as events
to any number of async subscribers (the SSE endpoint), from whichever
thread produced them.

Jobs can declare a lock: at most one job per lock runs at a time, and a
second submit is refused with JobBusy instead of queueing. All pkexec
actions share the "system" lock, which replaces the Flet UI's single busy
gate — two concurrent `update-initramfs` runs, or two password prompts at
once, are never useful.
"""

from __future__ import annotations

import asyncio
import threading
import traceback
import uuid
from collections import OrderedDict
from collections.abc import AsyncGenerator, Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from plymotion.services.progress import Cancelled

MAX_FINISHED_JOBS = 50
MAX_LOG_LINES = 500


class JobState(str, Enum):
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobBusy(Exception):
    """Another job holding the same lock is still running."""

    def __init__(self, running: Job) -> None:
        super().__init__(f"'{running.title}' todavía está en curso.")
        self.running = running


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Job:
    id: str
    kind: str
    title: str
    lock: str | None
    cancellable: bool
    state: JobState = JobState.RUNNING
    progress: float | None = None
    stage: str | None = None
    result: Any = None
    error: str | None = None
    logs: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=_now)
    finished_at: str | None = None
    cancel_requested: threading.Event = field(default_factory=threading.Event, repr=False)

    @property
    def finished(self) -> bool:
        return self.state is not JobState.RUNNING

    def snapshot(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "title": self.title,
            "state": self.state.value,
            "progress": self.progress,
            "stage": self.stage,
            "result": self.result,
            "error": self.error,
            "cancellable": self.cancellable and not self.finished,
            "created_at": self.created_at,
            "finished_at": self.finished_at,
            "log_tail": self.logs[-5:],
        }


class _JobReporter:
    """The Reporter handed to a service while it runs inside a job."""

    def __init__(self, manager: JobManager, job: Job) -> None:
        self._manager = manager
        self._job = job

    def progress(self, percent: float | None, stage: str | None = None) -> None:
        self._job.progress = None if percent is None else round(max(0.0, min(percent, 100.0)), 1)
        if stage is not None:
            self._job.stage = stage
        self._manager._publish_job(self._job)

    def log(self, message: str) -> None:
        self._job.logs.append(message)
        del self._job.logs[:-MAX_LOG_LINES]
        self._manager._publish("log", {"job_id": self._job.id, "line": message})

    def check_cancelled(self) -> None:
        if self._job.cancel_requested.is_set():
            raise Cancelled()


JobFn = Callable[[_JobReporter], Any]
_Subscriber = tuple[asyncio.AbstractEventLoop, "asyncio.Queue[dict[str, Any]]"]


class JobManager:
    def __init__(self, max_workers: int = 4) -> None:
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="job")
        self._lock = threading.Lock()
        self._jobs: OrderedDict[str, Job] = OrderedDict()
        self._running_locks: dict[str, Job] = {}
        self._subscribers: list[_Subscriber] = []

    # -- submitting -------------------------------------------------------

    def submit(
        self,
        kind: str,
        title: str,
        fn: JobFn,
        *,
        lock: str | None = None,
        cancellable: bool = False,
    ) -> Job:
        job = Job(id=uuid.uuid4().hex[:12], kind=kind, title=title, lock=lock,
                  cancellable=cancellable)
        with self._lock:
            if lock is not None and lock in self._running_locks:
                raise JobBusy(self._running_locks[lock])
            if lock is not None:
                self._running_locks[lock] = job
            self._jobs[job.id] = job
            self._trim_finished()
        self._publish_job(job)
        self._executor.submit(self._run, job, fn)
        return job

    def _run(self, job: Job, fn: JobFn) -> None:
        reporter = _JobReporter(self, job)
        try:
            job.result = fn(reporter)
            job.state = JobState.SUCCEEDED
            job.progress = 100.0
        except Cancelled:
            job.state = JobState.CANCELLED
            job.stage = "Cancelado"
            reporter.log("Operación cancelada")
        except Exception as exc:  # noqa: BLE001 - surfaced to the client as the job's error
            job.state = JobState.FAILED
            job.error = str(exc) or exc.__class__.__name__
            job.stage = "Error"
            reporter.log(f"ERROR: {job.error}")
            traceback.print_exc()
        finally:
            job.finished_at = _now()
            with self._lock:
                if job.lock is not None and self._running_locks.get(job.lock) is job:
                    del self._running_locks[job.lock]
            self._publish_job(job)

    def _trim_finished(self) -> None:
        finished = [j for j in self._jobs.values() if j.finished]
        for job in finished[: max(0, len(finished) - MAX_FINISHED_JOBS)]:
            del self._jobs[job.id]

    # -- querying ---------------------------------------------------------

    def get(self, job_id: str) -> Job | None:
        return self._jobs.get(job_id)

    def list(self) -> list[Job]:
        with self._lock:
            return list(reversed(self._jobs.values()))

    def cancel(self, job_id: str) -> bool:
        """Request cancellation. Returns False if the job can't be cancelled."""
        job = self._jobs.get(job_id)
        if job is None or job.finished or not job.cancellable:
            return False
        job.cancel_requested.set()
        job.stage = "Cancelando..."
        self._publish_job(job)
        return True

    def busy_locks(self) -> dict[str, str]:
        with self._lock:
            return {lock: job.id for lock, job in self._running_locks.items()}

    def shutdown(self) -> None:
        for job in list(self._jobs.values()):
            job.cancel_requested.set()
        self._executor.shutdown(wait=False, cancel_futures=True)

    # -- events -----------------------------------------------------------

    def _publish_job(self, job: Job) -> None:
        self._publish("job", job.snapshot())

    def _publish(self, event: str, data: dict[str, Any]) -> None:
        message = {"event": event, "data": data}
        with self._lock:
            subscribers = list(self._subscribers)
        for loop, queue in subscribers:
            try:
                loop.call_soon_threadsafe(queue.put_nowait, message)
            except RuntimeError:  # loop already closed; unsubscribe will clean up
                pass

    async def subscribe(self) -> AsyncGenerator[dict[str, Any], None]:
        """Yield a snapshot of every job, then live events until the caller stops."""
        loop = asyncio.get_running_loop()
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        entry = (loop, queue)
        with self._lock:
            self._subscribers.append(entry)
            snapshot = [job.snapshot() for job in reversed(self._jobs.values())]
        try:
            yield {"event": "snapshot", "data": {"jobs": snapshot}}
            while True:
                yield await queue.get()
        finally:
            with self._lock:
                self._subscribers.remove(entry)
