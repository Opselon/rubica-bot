from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from app.services.plugins.registry import PluginRegistry
from app.utils.stats import StatsCollector

LOGGER = logging.getLogger(__name__)


class Dispatcher:
    def __init__(
        self,
        registry: PluginRegistry,
        concurrency: int = 4,
        stats: StatsCollector | None = None,
    ) -> None:
        self.registry = registry
        self.queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self.concurrency = concurrency
        self._tasks: list[asyncio.Task] = []
        self.stats = stats

    async def start(self) -> None:
        for _ in range(self.concurrency):
            self._tasks.append(asyncio.create_task(self._worker()))

    async def stop(self) -> None:
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)

    async def enqueue(self, update: dict[str, Any], context: dict[str, Any]) -> None:
        await self.queue.put({"update": update, "context": context})
        if self.stats:
            self.stats.record_enqueue(self.queue.qsize())

    async def _worker(self) -> None:
        while True:
            item = await self.queue.get()
            update = item["update"]
            context = item["context"]
            start = time.perf_counter()
            error = False
            try:
                await self.registry.dispatch(update, context)
            except Exception:  # noqa: BLE001
                error = True
                LOGGER.exception("Unhandled error in dispatcher")
            finally:
                if self.stats:
                    elapsed_ms = (time.perf_counter() - start) * 1000
                    self.stats.record_dispatch(elapsed_ms, error=error)
                self.queue.task_done()
