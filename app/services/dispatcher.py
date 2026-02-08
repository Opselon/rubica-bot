from __future__ import annotations

import asyncio
import logging
from typing import Any

from app.services.plugins.registry import PluginRegistry

LOGGER = logging.getLogger(__name__)


class Dispatcher:
    def __init__(self, registry: PluginRegistry, concurrency: int = 4) -> None:
        self.registry = registry
        self.queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self.concurrency = concurrency
        self._tasks: list[asyncio.Task] = []

    async def start(self) -> None:
        for _ in range(self.concurrency):
            self._tasks.append(asyncio.create_task(self._worker()))

    async def stop(self) -> None:
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)

    async def enqueue(self, update: dict[str, Any], context: dict[str, Any]) -> None:
        await self.queue.put({"update": update, "context": context})

    async def _worker(self) -> None:
        while True:
            item = await self.queue.get()
            update = item["update"]
            context = item["context"]
            try:
                await self.registry.dispatch(update, context)
            except Exception:  # noqa: BLE001
                LOGGER.exception("Unhandled error in dispatcher")
            finally:
                self.queue.task_done()
