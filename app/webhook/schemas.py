from __future__ import annotations

from typing import Any


class WebhookUpdate(dict):
    @property
    def message(self) -> dict[str, Any] | None:
        return self.get("message") or self.get("data")

    @property
    def inline_message(self) -> dict[str, Any] | None:
        return self.get("inline_message")

    @property
    def update_id(self) -> str | None:
        return self.get("update_id") or self.get("message_id")
