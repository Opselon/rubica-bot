from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Any, Literal

from app.utils.dedup import Deduplicator
from app.utils.stats import StatsCollector

QueueDecision = Literal["enqueued", "duplicate", "dropped"]


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
        self.queue: asyncio.Queue[Job | None] = asyncio.Queue(maxsize=max_size)
        self.deduplicator = deduplicator
        self.full_policy = full_policy
        self.stats = stats

    @property
    def max_size(self) -> int:
        return self.queue.maxsize

    def size(self) -> int:
        return self.queue.qsize()

    async def enqueue(self, job: Job) -> QueueDecision:
        if self.deduplicator.seen(job.job_id):
            if self.stats:
                self.stats.record_dedup()
            return "duplicate"
        if self.queue.full():
            if self.full_policy == "drop_oldest":
                await self._drop_oldest()
            else:
                if self.stats:
                    self.stats.record_drop()
                return "dropped"
        await self.queue.put(job)
        if self.stats:
            self.stats.record_enqueue(self.queue.qsize())
        return "enqueued"

    async def _drop_oldest(self) -> None:
        try:
            self.queue.get_nowait()
            self.queue.task_done()
        except asyncio.QueueEmpty:
            return
        if self.stats:
            self.stats.record_drop()

    async def get(self) -> Job | None:
        return await self.queue.get()

    async def put_raw(self, job: Job | None) -> None:
        await self.queue.put(job)

    def task_done(self) -> None:
        self.queue.task_done()

    async def join(self) -> None:
        await self.queue.join()
