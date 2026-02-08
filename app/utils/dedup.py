from __future__ import annotations

import time


class Deduplicator:
    def __init__(self, ttl_seconds: int) -> None:
        self.ttl_seconds = ttl_seconds
        self._cache: dict[str, float] = {}

    def seen(self, key: str | None) -> bool:
        if key is None:
            return False
        now = time.monotonic()
        expired = [k for k, v in self._cache.items() if now - v > self.ttl_seconds]
        for k in expired:
            self._cache.pop(k, None)
        if key in self._cache:
            return True
        self._cache[key] = now
        return False
