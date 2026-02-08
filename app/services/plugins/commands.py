from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Awaitable

from app.utils.message import extract_message, get_chat_id, get_sender_id, get_text
from .base import Plugin

CommandHandler = Callable[[dict[str, Any], dict[str, Any], list[str]], Awaitable[None]]


@dataclass
class Command:
    name: str
    description: str
    handler: CommandHandler
    admin_only: bool = False


class CommandRegistry:
    def __init__(self) -> None:
        self._commands: dict[str, Command] = {}

    def register(self, command: Command) -> None:
        self._commands[command.name] = command

    def list_commands(self) -> list[dict[str, str]]:
        return [{"command": cmd.name, "description": cmd.description} for cmd in self._commands.values()]

    def get(self, name: str) -> Command | None:
        return self._commands.get(name)


class CommandsPlugin(Plugin):
    name = "commands"

    def __init__(self, registry: CommandRegistry) -> None:
        self.registry = registry

    async def handle(self, update: dict[str, Any], context: dict[str, Any]) -> bool:
        message = extract_message(update)
        if not message:
            return False
        text = get_text(message)
        if not text or not text.startswith("/"):
            return False
        parts = text.strip().split()
        cmd_name = parts[0].lstrip("/").lower()
        command = self.registry.get(cmd_name)
        if not command:
            return False
        chat_id = get_chat_id(message)
        sender_id = get_sender_id(message)
        if command.admin_only and chat_id and sender_id:
            repo = context["repo"]
            owner_id = context.get("owner_id")
            if sender_id != owner_id and not repo.is_admin(chat_id, sender_id):
                client = context["client"]
                await client.send_message(chat_id, "این دستور فقط برای ادمین‌هاست.")
                return True
        await command.handler(message, context, parts[1:])
        return True
