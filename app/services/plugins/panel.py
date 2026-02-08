from __future__ import annotations

from typing import Any

from app.utils.message import extract_message, get_chat_id
from .base import Plugin


class PanelPlugin(Plugin):
    name = "panel"

    async def handle(self, update: dict[str, Any], context: dict[str, Any]) -> bool:
        client = context["client"]
        repo = context["repo"]
        message = extract_message(update)
        if not message:
            return False
        text = message.get("text") or ""
        if text.startswith("/panel"):
            chat_id = get_chat_id(message)
            if not chat_id:
                return True
            settings = repo.get_group(chat_id)
            keypad = {
                "rows": [
                    {
                        "buttons": [
                            {
                                "text": f"Anti Link: {'ON' if settings.anti_link else 'OFF'}",
                                "callback_data": "panel:anti_link",
                            },
                            {
                                "text": f"Anti Flood: {'ON' if settings.anti_flood else 'OFF'}",
                                "callback_data": "panel:anti_flood",
                            },
                        ]
                    },
                    {
                        "buttons": [
                            {"text": "Filters", "callback_data": "panel:filters"},
                            {"text": "Delete Tools", "callback_data": "panel:delete"},
                        ]
                    },
                ]
            }
            await client.send_message(chat_id, "پنل مدیریت", inline_keypad=keypad)
            return True
        callback = update.get("callback_query")
        if not callback:
            return False
        chat_id = callback.get("chat_id")
        data = callback.get("data")
        if not chat_id or not data or not data.startswith("panel:"):
            return False
        if data == "panel:anti_link":
            settings = repo.get_group(chat_id)
            repo.set_group_flag(chat_id, "anti_link", not settings.anti_link)
            await client.send_message(chat_id, "تنظیم Anti Link به‌روزرسانی شد.")
            return True
        if data == "panel:anti_flood":
            settings = repo.get_group(chat_id)
            repo.set_group_flag(chat_id, "anti_flood", not settings.anti_flood)
            await client.send_message(chat_id, "تنظیم Anti Flood به‌روزرسانی شد.")
            return True
        return False
