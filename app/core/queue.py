from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Any, Literal

from app.utils.dedup import Deduplicator
from app.utils.stats import StatsCollector

QueueDecision = Literal["enqueued", "duplicate", "dropped"]
JobPriority = Literal["high", "normal"]


@dataclass
class Job:
    job_id: str
    received_at: float
    chat_id: str | None
    message_id: str | None
    sender_id: str | None
    update_type: str | None
    text: str | None
    raw_payload: dict[str, Any] | None = None
    dedup_key: str | None = None
    priority: JobPriority = "normal"

    @classmethod
    def build(
        cls,
        job_id: str,
        *,
        chat_id: str | None,
        message_id: str | None,
        sender_id: str | None,
        update_type: str | None,
        text: str | None,
        raw_payload: dict[str, Any] | None = None,
        dedup_key: str | None = None,
        priority: JobPriority = "normal",
    ) -> Job:
        return cls(
            job_id=job_id,
            received_at=time.time(),
            chat_id=chat_id,
            message_id=message_id,
            sender_id=sender_id,
            update_type=update_type,
            text=text,
            raw_payload=raw_payload,
            dedup_key=dedup_key,
            priority=priority,
        )


class JobQueue:
    def __init__(
        self,
        *,
        max_size: int,
        deduplicator: Deduplicator,
        full_policy: str = "reject",
        stats: StatsCollector | None = None,
    ) -> None:
        self.high_queue: asyncio.Queue[Job | None] = asyncio.Queue()
        self.normal_queue: asyncio.Queue[Job | None] = asyncio.Queue()
        self._size = 0
        self._lock = asyncio.Lock()
        self._max_size = max_size
        self.deduplicator = deduplicator
        self.full_policy = full_policy
        self.stats = stats

    @property
    def max_size(self) -> int:
        return self._max_size

    @max_size.setter
    def max_size(self, value: int) -> None:
        self._max_size = value

    def size(self) -> int:
        return self._size

    def size_by_priority(self) -> dict[str, int]:
        return {"high": self.high_queue.qsize(), "normal": self.normal_queue.qsize()}

    async def enqueue(self, job: Job) -> QueueDecision:
        if self.deduplicator.seen(job.dedup_key or job.job_id):
            if self.stats:
                self.stats.record_dedup()
            return "duplicate"
        async with self._lock:
            if self._size >= self.max_size:
                if self.full_policy == "drop_oldest":
                    await self._drop_oldest()
                else:
                    if self.stats:
                        self.stats.record_drop()
                    return "dropped"
            await self._put(job)
            self._size += 1
            if self.stats:
                self.stats.record_enqueue(self._size)
        return "enqueued"

    async def _drop_oldest(self) -> None:
        try:
            if not self.normal_queue.empty():
                self.normal_queue.get_nowait()
                self.normal_queue.task_done()
            else:
                self.high_queue.get_nowait()
                self.high_queue.task_done()
        except asyncio.QueueEmpty:
            return
        self._size = max(0, self._size - 1)
        if self.stats:
            self.stats.record_drop()

    async def get(self) -> Job | None:
        if not self.high_queue.empty():
            job = await self.high_queue.get()
        elif not self.normal_queue.empty():
            job = await self.normal_queue.get()
        else:
            high_task = asyncio.create_task(self.high_queue.get())
            normal_task = asyncio.create_task(self.normal_queue.get())
            done, pending = await asyncio.wait(
                {high_task, normal_task},
                return_when=asyncio.FIRST_COMPLETED,
            )
            for task in pending:
                task.cancel()
            job = next(iter(done)).result()
        self._size = max(0, self._size - 1)
        return job

    async def put_raw(self, job: Job | None) -> None:
        await self.high_queue.put(job)

    def task_done(self, job: Job | None) -> None:
        if job is None:
            self.high_queue.task_done()
            return
        if job.priority == "high":
            self.high_queue.task_done()
        else:
            self.normal_queue.task_done()

    async def join(self) -> None:
        await asyncio.gather(self.high_queue.join(), self.normal_queue.join())

    async def _put(self, job: Job) -> None:
        if job.priority == "high":
            await self.high_queue.put(job)
        else:
            await self.normal_queue.put(job)

    async def drain(self) -> dict[str, int]:
        drained_high = 0
        drained_normal = 0
        while not self.high_queue.empty():
            try:
                self.high_queue.get_nowait()
                self.high_queue.task_done()
                drained_high += 1
            except asyncio.QueueEmpty:
                break
        while not self.normal_queue.empty():
            try:
                self.normal_queue.get_nowait()
                self.normal_queue.task_done()
                drained_normal += 1
            except asyncio.QueueEmpty:
                break
        self._size = 0
        return {"high": drained_high, "normal": drained_normal}
