from __future__ import annotations

from typing import Any

from app.utils.message import extract_message, get_chat_id, get_message_id, get_sender_id, get_text
from app.utils.regex import contains_link
from .base import Plugin


class AntiLinkPlugin(Plugin):
    name = "anti_link"

    async def handle(self, update: dict[str, Any], context: dict[str, Any]) -> bool:
        repo = context["repo"]
        client = context["client"]
        message = extract_message(update)
        if not message:
            return False
        chat_id = get_chat_id(message)
        if not chat_id:
            return False
        chat = message.get("chat") or {}
        if chat.get("type") not in {"Group", "Supergroup", "channel", "Channel", "group"}:
            return False
        settings = repo.get_group(chat_id)
        if not settings.anti_link:
            return False
        sender_id = get_sender_id(message)
        if sender_id and repo.is_admin(chat_id, sender_id):
            return False
        text = get_text(message)
        if not contains_link(text):
            return False
        message_id = get_message_id(message)
        if message_id:
            await client.delete_message(chat_id, message_id)
        if sender_id:
            await client.ban_chat_member(chat_id, sender_id)
        if context.get("report_anti_actions"):
            await client.send_message(chat_id, "کاربر به دلیل ارسال لینک بن شد و پیام حذف شد.")
        return True
