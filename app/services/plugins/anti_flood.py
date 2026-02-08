from __future__ import annotations

import time
from collections import defaultdict, deque
from typing import Any, Deque

from app.utils.message import extract_message, get_chat_id, get_sender_id
from .base import Plugin


class AntiFloodPlugin(Plugin):
    name = "anti_flood"

    def __init__(self, window_seconds: int = 8) -> None:
        self.window_seconds = window_seconds
        self._events: dict[str, Deque[float]] = defaultdict(deque)

    async def handle(self, update: dict[str, Any], context: dict[str, Any]) -> bool:
        repo = context["repo"]
        client = context["client"]
        message = extract_message(update)
        if not message:
            return False
        chat_id = get_chat_id(message)
        sender_id = get_sender_id(message)
        if not chat_id or not sender_id:
            return False
        settings = repo.get_group(chat_id)
        if not settings.anti_flood:
            return False
        if repo.is_admin(chat_id, sender_id):
            return False
        now = time.monotonic()
        key = f"{chat_id}:{sender_id}"
        events = self._events[key]
        while events and now - events[0] > self.window_seconds:
            events.popleft()
        events.append(now)
        if len(events) > settings.flood_limit:
            message_id = message.get("message_id") or message.get("id")
            if message_id:
                await client.delete_message(chat_id, message_id)
            await client.ban_chat_member(chat_id, sender_id)
            return True
        return False
