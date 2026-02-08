from __future__ import annotations

from typing import Any


def extract_message(update: dict[str, Any]) -> dict[str, Any] | None:
    return update.get("message") or update.get("data") or update.get("inline_message")


def get_text(message: dict[str, Any] | None) -> str | None:
    if not message:
        return None
    return message.get("text") or message.get("body")


def get_chat_id(message: dict[str, Any] | None) -> str | None:
    if not message:
        return None
    chat = message.get("chat") or {}
    return chat.get("id") or message.get("chat_id")


def get_message_id(message: dict[str, Any] | None) -> str | None:
    if not message:
        return None
    return message.get("message_id") or message.get("id")


def get_sender_id(message: dict[str, Any] | None) -> str | None:
    if not message:
        return None
    sender = message.get("sender") or {}
    return sender.get("id") or message.get("sender_id")
