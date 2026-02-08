from __future__ import annotations

import asyncio
import time

from app.core.queue import Job
from app.core.queue import JobQueue
from app.core.worker import WorkerPool
from app.services.plugins.base import Plugin
from app.services.plugins.registry import PluginRegistry
from app.utils.dedup import Deduplicator
from app.utils.stats import StatsCollector


class _NoopPlugin(Plugin):
    name = "noop"

    async def handle(self, update: dict, context: dict) -> bool:
        return False


async def run_speed_check(samples: int = 200) -> dict[str, float]:
    stats = StatsCollector()
    registry = PluginRegistry([_NoopPlugin()])
    queue = JobQueue(max_size=1000, deduplicator=Deduplicator(60), stats=stats)

    async def _process(job: Job) -> None:
        await registry.dispatch(job.raw_payload or {}, {"stats": stats})

    worker = WorkerPool(queue, _process, concurrency=4, stats=stats)
    await worker.start()
    start = time.perf_counter()
    for idx in range(samples):
        job = Job.build(str(idx), chat_id=None, message_id=None, sender_id=None, update_type=None, text=None)
        await queue.enqueue(job)
    await queue.join()
    elapsed = time.perf_counter() - start
    await worker.stop()
    return {
        "samples": float(samples),
        "elapsed_s": elapsed,
        "avg_dispatch_ms": stats.average_dispatch_ms,
    }


def main() -> None:
    result = asyncio.run(run_speed_check())
    print(
        "SpeedCheck -> samples: {samples}, elapsed: {elapsed_s:.3f}s, avg_dispatch: {avg_dispatch_ms:.2f}ms".format(
            **result
        )
    )


if __name__ == "__main__":
    main()
