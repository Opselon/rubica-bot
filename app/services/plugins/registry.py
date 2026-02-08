from __future__ import annotations

from typing import Iterable

from .base import Plugin


class PluginRegistry:
    def __init__(self, plugins: Iterable[Plugin]) -> None:
        self.plugins = list(plugins)

    async def dispatch(self, update: dict, context: dict) -> None:
        for plugin in self.plugins:
            handled = await plugin.handle(update, context)
            if handled:
                break
