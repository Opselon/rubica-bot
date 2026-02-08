from __future__ import annotations

import time
from collections import OrderedDict
from typing import Generic, TypeVar

K = TypeVar("K")
V = TypeVar("V")


class LruTtlCache(Generic[K, V]):
    def __init__(self, max_size: int, ttl_seconds: int) -> None:
        self.max_size = max(1, max_size)
        self.ttl_seconds = max(1, ttl_seconds)
        self._data: OrderedDict[K, tuple[float, V]] = OrderedDict()

    def get(self, key: K) -> V | None:
        now = time.monotonic()
        item = self._data.get(key)
        if not item:
            return None
        ts, value = item
        if now - ts > self.ttl_seconds:
            self._data.pop(key, None)
            return None
        self._data.move_to_end(key)
        return value

    def set(self, key: K, value: V) -> None:
        self._data[key] = (time.monotonic(), value)
        self._data.move_to_end(key)
        while len(self._data) > self.max_size:
            self._data.popitem(last=False)

    def invalidate(self, key: K) -> None:
        self._data.pop(key, None)

    def clear(self) -> None:
        self._data.clear()
