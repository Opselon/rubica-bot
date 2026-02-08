from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class Plugin(ABC):
    name: str

    @abstractmethod
    async def handle(self, update: dict[str, Any], context: dict[str, Any]) -> bool:
        """Return True if handled and no further processing should happen."""
