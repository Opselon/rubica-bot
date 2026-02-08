from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Awaitable, Callable

from app.core.queue import Job, JobQueue
from app.utils.stats import StatsCollector

LOGGER = logging.getLogger(__name__)


@dataclass
class WorkerStatus:
    worker_id: int
    started_at: float = field(default_factory=time.time)
    last_job_at: float | None = None
    last_error_at: float | None = None
    last_error: str | None = None
    processed: int = 0
    alive: bool = True


class WorkerPool:
    def __init__(
        self,
        queue: JobQueue,
        handler: Callable[[Job], Awaitable[None]],
        *,
        concurrency: int = 4,
        stats: StatsCollector | None = None,
    ) -> None:
        self.queue = queue
        self.handler = handler
        self.concurrency = max(1, concurrency)
        self.stats = stats
        self._tasks: list[asyncio.Task] = []
        self._statuses: dict[int, WorkerStatus] = {}
        self._stop_event = asyncio.Event()

    async def start(self) -> None:
        for idx in range(self.concurrency):
            status = WorkerStatus(worker_id=idx)
            self._statuses[idx] = status
            self._tasks.append(asyncio.create_task(self._worker_loop(status)))

    async def stop(self) -> None:
        self._stop_event.set()
        for _ in self._tasks:
            await self.queue.put_raw(None)
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()

    def statuses(self) -> list[WorkerStatus]:
        return list(self._statuses.values())

    async def _worker_loop(self, status: WorkerStatus) -> None:
        while True:
            job = await self.queue.get()
            if job is None:
                self.queue.task_done()
                status.alive = False
                break
            start = time.perf_counter()
            error = False
            try:
                await self.handler(job)
            except Exception as exc:  # noqa: BLE001
                error = True
                status.last_error = str(exc)
                status.last_error_at = time.time()
                LOGGER.exception("Unhandled error while processing job %s", job.job_id)
            finally:
                status.processed += 1
                status.last_job_at = time.time()
                if self.stats:
                    elapsed_ms = (time.perf_counter() - start) * 1000
                    self.stats.record_dispatch(elapsed_ms, error=error)
                self.queue.task_done()
