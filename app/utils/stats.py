from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class StatsCollector:
    started_at: float = field(default_factory=time.time)
    total_updates: int = 0
    total_errors: int = 0
    total_dispatch_ms: float = 0.0
    last_dispatch_ms: float = 0.0
    last_update_at: float | None = None
    last_enqueue_at: float | None = None
    last_queue_size: int = 0

    def record_enqueue(self, queue_size: int) -> None:
        self.last_enqueue_at = time.time()
        self.last_queue_size = queue_size

    def record_dispatch(self, duration_ms: float, error: bool = False) -> None:
        self.total_updates += 1
        self.total_dispatch_ms += duration_ms
        self.last_dispatch_ms = duration_ms
        self.last_update_at = time.time()
        if error:
            self.total_errors += 1

    @property
    def average_dispatch_ms(self) -> float:
        if self.total_updates == 0:
            return 0.0
        return self.total_dispatch_ms / self.total_updates

    @property
    def uptime_seconds(self) -> int:
        return int(time.time() - self.started_at)
