from __future__ import annotations

from typing import Any

from app.utils.message import extract_message, get_chat_id
from .base import Plugin


class PanelPlugin(Plugin):
    name = "panel"

    def _build_keypad(self, settings) -> dict[str, Any]:
        return {
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
            await client.send_message(chat_id, "پنل مدیریت", inline_keypad=self._build_keypad(settings))
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
            await self._refresh_panel(client, repo, chat_id, callback)
            return True
        if data == "panel:anti_flood":
            settings = repo.get_group(chat_id)
            repo.set_group_flag(chat_id, "anti_flood", not settings.anti_flood)
            await client.send_message(chat_id, "تنظیم Anti Flood به‌روزرسانی شد.")
            await self._refresh_panel(client, repo, chat_id, callback)
            return True
        if data == "panel:filters":
            filters = repo.list_filters(chat_id)
            if not filters:
                await client.send_message(chat_id, "لیست فیلتر خالی است. با /filter add <word> اضافه کنید.")
                return True
            text = "\n".join(
                [f"{word} ({'whitelist' if is_whitelist else 'blacklist'})" for word, is_whitelist, _ in filters]
            )
            await client.send_message(chat_id, f"فیلترها:\n{text}")
            return True
        if data == "panel:delete":
            await client.send_message(chat_id, "برای حذف انبوه از /del <n> استفاده کنید.")
            return True
        return False

    async def _refresh_panel(self, client: Any, repo: Any, chat_id: str, callback: dict[str, Any]) -> None:
        message_id = callback.get("message_id")
        if not message_id:
            return
        settings = repo.get_group(chat_id)
        await client.edit_inline_keypad(chat_id, message_id, self._build_keypad(settings))
