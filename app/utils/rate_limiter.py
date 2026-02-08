from __future__ import annotations

import time
from collections import deque
from typing import Deque


class RateLimiter:
    def __init__(self, max_requests: int, window_seconds: int = 60) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._events: Deque[float] = deque()

    def allow(self) -> bool:
        now = time.monotonic()
        while self._events and now - self._events[0] > self.window_seconds:
            self._events.popleft()
        if len(self._events) >= self.max_requests:
            return False
        self._events.append(now)
        return True
