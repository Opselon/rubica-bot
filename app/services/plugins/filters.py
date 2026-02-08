from __future__ import annotations

import re
from typing import Any

from app.utils.message import extract_message, get_chat_id, get_message_id, get_sender_id, get_text
from .base import Plugin


class FilterWordsPlugin(Plugin):
    name = "filters"

    async def handle(self, update: dict[str, Any], context: dict[str, Any]) -> bool:
        repo = context["repo"]
        client = context["client"]
        message = extract_message(update)
        if not message:
            return False
        chat_id = get_chat_id(message)
        if not chat_id:
            return False
        settings = repo.get_group(chat_id)
        if not settings.anti_badwords:
            return False
        sender_id = get_sender_id(message)
        if sender_id and repo.is_admin(chat_id, sender_id):
            return False
        text = get_text(message) or ""
        filters = repo.list_filters(chat_id)
        if not filters:
            return False
        matched_blacklist = False
        for word, is_whitelist, regex_enabled in filters:
            if is_whitelist:
                if (re.search(word, text) if regex_enabled else word in text):
                    return False
            else:
                if (re.search(word, text) if regex_enabled else word in text):
                    matched_blacklist = True
        if matched_blacklist:
            message_id = get_message_id(message)
            if message_id:
                await client.delete_message(chat_id, message_id)
            return True
        return False
