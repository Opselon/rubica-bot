from __future__ import annotations

import logging
from typing import Any

import httpx

LOGGER = logging.getLogger(__name__)


class RubikaClient:
    def __init__(self, token: str, base_url: str | None = None) -> None:
        self.token = token
        self.base_url = base_url or "https://botapi.rubika.ir/v3"
        self._client = httpx.AsyncClient(timeout=10)

    async def request(self, method: str, payload: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.base_url}/{self.token}/{method}"
        response = await self._client.post(url, json=payload)
        response.raise_for_status()
        data = response.json()
        if not data.get("ok", True):
            LOGGER.warning("Rubika API error for %s: %s", method, data)
        return data

    async def send_message(self, chat_id: str, text: str, inline_keypad: dict | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {"chat_id": chat_id, "text": text}
        if inline_keypad:
            payload["inline_keypad"] = inline_keypad
        return await self.request("sendMessage", payload)

    async def delete_message(self, chat_id: str, message_id: str) -> dict[str, Any]:
        return await self.request("deleteMessage", {"chat_id": chat_id, "message_id": message_id})

    async def ban_chat_member(self, chat_id: str, user_id: str) -> dict[str, Any]:
        return await self.request("banChatMember", {"chat_id": chat_id, "user_id": user_id})

    async def unban_chat_member(self, chat_id: str, user_id: str) -> dict[str, Any]:
        return await self.request("unbanChatMember", {"chat_id": chat_id, "user_id": user_id})

    async def set_commands(self, commands: list[dict[str, str]]) -> dict[str, Any]:
        return await self.request("setCommands", {"commands": commands})

    async def update_bot_endpoint(self, url: str) -> dict[str, Any]:
        return await self.request("updateBotEndpoint", {"url": url})

    async def update_bot_endpoints(self, urls: list[str]) -> dict[str, Any]:
        return await self.request("updateBotEndpoints", {"urls": urls})

    async def close(self) -> None:
        await self._client.aclose()
