"""Tests for the JobManager event stream."""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from plymotion.jobs import JobBusy, JobManager


async def _collect_until_done(manager: JobManager, job_id: str) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    async for message in manager.subscribe():
        events.append(message)
        data = message["data"]
        if message["event"] == "job" and data["id"] == job_id and data["state"] != "running":
            break
    return events


def test_subscribe_receives_snapshot_progress_and_logs() -> None:
    manager = JobManager()

    async def scenario() -> list[dict[str, Any]]:
        gate = asyncio.Event()
        loop = asyncio.get_running_loop()

        def work(reporter: Any) -> str:
            asyncio.run_coroutine_threadsafe(gate.wait(), loop).result(5)
            reporter.progress(50, "mitad")
            reporter.log("hola")
            return "ok"

        job = manager.submit("test", "Prueba", work)
        collector = asyncio.create_task(_collect_until_done(manager, job.id))
        await asyncio.sleep(0.05)
        gate.set()
        return await asyncio.wait_for(collector, 5)

    events = asyncio.run(scenario())
    manager.shutdown()

    assert events[0]["event"] == "snapshot"
    kinds = [(e["event"], e["data"].get("stage") or e["data"].get("line")) for e in events[1:]]
    assert ("job", "mitad") in kinds
    assert ("log", "hola") in kinds
    assert events[-1]["data"]["state"] == "succeeded"
    assert events[-1]["data"]["result"] == "ok"


def test_lock_rejects_second_job() -> None:
    import threading

    manager = JobManager()
    release = threading.Event()
    manager.submit("a", "A", lambda _r: release.wait(5), lock="system")
    with pytest.raises(JobBusy):
        manager.submit("b", "B", lambda _r: None, lock="system")
    manager.submit("c", "C", lambda _r: None, lock="other")
    release.set()
    manager.shutdown()
