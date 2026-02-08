from __future__ import annotations

from typing import Any

from app.utils.message import extract_message, get_chat_id, get_message_id, get_sender_id, get_text
from .base import Plugin


class MessageLoggingPlugin(Plugin):
    name = "logging"

    async def handle(self, update: dict[str, Any], context: dict[str, Any]) -> bool:
        repo = context["repo"]
        message = extract_message(update)
        if not message:
            return False
        chat_id = get_chat_id(message)
        message_id = get_message_id(message)
        if not chat_id or not message_id:
            return False
        chat = message.get("chat") or {}
        repo.upsert_group(chat_id, chat.get("title"))
        repo.save_message(chat_id, message_id, get_sender_id(message), get_text(message))
        return False
