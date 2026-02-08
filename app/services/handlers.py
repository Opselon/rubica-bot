from __future__ import annotations

import asyncio
import logging
from typing import Any

from app.utils.message import get_chat_id, get_message_id, get_sender_id

LOGGER = logging.getLogger(__name__)


async def help_handler(message: dict[str, Any], context: dict[str, Any], args: list[str]) -> None:
    chat_id = get_chat_id(message)
    if not chat_id:
        return
    registry = context["command_registry"]
    lines = ["راهنما:"]
    for command in registry.list_commands():
        lines.append(f"/{command['command']} - {command['description']}")
    await context["client"].send_message(chat_id, "\n".join(lines))


async def setcmd_handler(message: dict[str, Any], context: dict[str, Any], args: list[str]) -> None:
    registry = context["command_registry"]
    await context["client"].set_commands(registry.list_commands())


async def ping_handler(message: dict[str, Any], context: dict[str, Any], args: list[str]) -> None:
    chat_id = get_chat_id(message)
    if chat_id:
        await context["client"].send_message(chat_id, "pong")


async def coin_handler(message: dict[str, Any], context: dict[str, Any], args: list[str]) -> None:
    chat_id = get_chat_id(message)
    if not chat_id:
        return
    import random

    await context["client"].send_message(chat_id, random.choice(["شیر", "خط"]))


async def roll_handler(message: dict[str, Any], context: dict[str, Any], args: list[str]) -> None:
    chat_id = get_chat_id(message)
    if not chat_id:
        return
    import random

    await context["client"].send_message(chat_id, f"🎲 {random.randint(1, 6)}")


async def joke_handler(message: dict[str, Any], context: dict[str, Any], args: list[str]) -> None:
    chat_id = get_chat_id(message)
    if not chat_id:
        return
    jokes = [
        "ربات: چرا کامپیوتر سردش بود؟ چون همیشه پنجره‌ها باز بود.",
        "برنامه‌نویس: قهوه بدون کد؟ هرگز!",
        "وقتی دیباگ می‌کنی، باگ هم زمان یاد می‌گیره!",
    ]
    import random

    await context["client"].send_message(chat_id, random.choice(jokes))


async def antilink_handler(message: dict[str, Any], context: dict[str, Any], args: list[str]) -> None:
    chat_id = get_chat_id(message)
    if not chat_id or not args:
        return
    repo = context["repo"]
    value = args[0].lower() == "on"
    repo.set_group_flag(chat_id, "anti_link", value)
    await context["client"].send_message(chat_id, f"Anti Link {'ON' if value else 'OFF'}")


async def filter_handler(message: dict[str, Any], context: dict[str, Any], args: list[str]) -> None:
    chat_id = get_chat_id(message)
    if not chat_id:
        return
    repo = context["repo"]
    if not args:
        await context["client"].send_message(chat_id, "استفاده: /filter add|del|list <word>")
        return
    action = args[0].lower()
    if action == "list":
        filters = repo.list_filters(chat_id)
        if not filters:
            await context["client"].send_message(chat_id, "فیلتر خالی است.")
            return
        text = "\n".join(
            [f"{word} ({'whitelist' if is_whitelist else 'blacklist'})" for word, is_whitelist, _ in filters]
        )
        await context["client"].send_message(chat_id, text)
        return
    if len(args) < 2:
        await context["client"].send_message(chat_id, "کلمه را وارد کنید.")
        return
    word = args[1]
    if action == "add":
        repo.add_filter(chat_id, word, is_whitelist=False, regex_enabled=False)
        await context["client"].send_message(chat_id, f"{word} به لیست سیاه اضافه شد.")
    elif action == "del":
        repo.remove_filter(chat_id, word)
        await context["client"].send_message(chat_id, f"{word} حذف شد.")


async def delete_handler(message: dict[str, Any], context: dict[str, Any], args: list[str]) -> None:
    chat_id = get_chat_id(message)
    if not chat_id:
        return
    repo = context["repo"]
    client = context["client"]
    limit = int(args[0]) if args else 100
    limit = min(limit, 10000)
    message_ids = repo.fetch_recent_message_ids(chat_id, limit)
    for idx, message_id in enumerate(message_ids, start=1):
        try:
            await client.delete_message(chat_id, message_id)
        except Exception:  # noqa: BLE001
            LOGGER.exception("Failed to delete message %s", message_id)
        if idx % 20 == 0:
            await asyncio.sleep(0.2)


async def ban_handler(message: dict[str, Any], context: dict[str, Any], args: list[str]) -> None:
    chat_id = get_chat_id(message)
    if not chat_id:
        return
    client = context["client"]
    target_id = None
    if args:
        target_id = args[0]
    elif reply := message.get("reply_to_message"):
        target_id = get_sender_id(reply)
    if target_id:
        await client.ban_chat_member(chat_id, target_id)


async def unban_handler(message: dict[str, Any], context: dict[str, Any], args: list[str]) -> None:
    chat_id = get_chat_id(message)
    if not chat_id:
        return
    client = context["client"]
    if args:
        await client.unban_chat_member(chat_id, args[0])
