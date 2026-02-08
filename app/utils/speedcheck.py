from __future__ import annotations

import asyncio
import time

from app.services.dispatcher import Dispatcher
from app.services.plugins.base import Plugin
from app.services.plugins.registry import PluginRegistry
from app.utils.stats import StatsCollector


class _NoopPlugin(Plugin):
    name = "noop"

    async def handle(self, update: dict, context: dict) -> bool:
        return False


async def run_speed_check(samples: int = 200) -> dict[str, float]:
    stats = StatsCollector()
    registry = PluginRegistry([_NoopPlugin()])
    dispatcher = Dispatcher(registry, concurrency=4, stats=stats)
    await dispatcher.start()
    start = time.perf_counter()
    for idx in range(samples):
        await dispatcher.enqueue({"update_id": idx}, {"stats": stats})
    await dispatcher.queue.join()
    elapsed = time.perf_counter() - start
    await dispatcher.stop()
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
