from __future__ import annotations

import asyncio
import logging
import random
import time
from collections import defaultdict
from typing import Any

import httpx

LOGGER = logging.getLogger(__name__)


class ApiRateLimiter:
    def __init__(self, rate_per_second: float, burst: int) -> None:
        self.rate_per_second = max(rate_per_second, 0.1)
        self.capacity = max(burst, 1)
        self._tokens = float(self.capacity)
        self._last_refill = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_refill
            self._tokens = min(self.capacity, self._tokens + elapsed * self.rate_per_second)
            self._last_refill = now
            if self._tokens < 1.0:
                wait_for = (1.0 - self._tokens) / self.rate_per_second
                await asyncio.sleep(max(wait_for, 0))
                self._tokens = 0.0
                self._last_refill = time.monotonic()
            self._tokens -= 1.0


class RubikaClient:
    def __init__(
        self,
        token: str,
        base_url: str | None = None,
        *,
        timeout_seconds: float = 10.0,
        retry_attempts: int = 3,
        retry_backoff: float = 0.5,
        rate_limit_per_second: int = 20,
    ) -> None:
        self.token = token
        self.base_url = base_url or "https://botapi.rubika.ir/v3"
        self.timeout_seconds = timeout_seconds
        self.retry_attempts = retry_attempts
        self.retry_backoff = retry_backoff
        self._client = httpx.AsyncClient(timeout=timeout_seconds)
        self._rate_limiters: dict[str, ApiRateLimiter] = defaultdict(
            lambda: ApiRateLimiter(rate_per_second=max(rate_limit_per_second, 1), burst=5)
        )

    async def api_call(self, method: str, payload: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.base_url}/{self.token}/{method}"
        attempt = 0
        while True:
            attempt += 1
            await self._rate_limiters[method].acquire()
            start = time.monotonic()
            try:
                response = await self._client.post(url, json=payload, timeout=self.timeout_seconds)
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                if attempt <= self.retry_attempts:
                    await self._sleep_before_retry(attempt, method, error=str(exc))
                    continue
                LOGGER.error("Rubika API transport error: %s", exc)
                return {"ok": False, "error": str(exc), "method": method}
            elapsed = (time.monotonic() - start) * 1000
            LOGGER.debug("Rubika API %s attempt %s in %.2fms", method, attempt, elapsed)
            if response.status_code in {408, 429} or response.status_code >= 500:
                if attempt <= self.retry_attempts:
                    await self._sleep_before_retry(
                        attempt,
                        method,
                        error=f"status {response.status_code}",
                    )
                    continue
            try:
                data = response.json()
            except ValueError:
                data = {"ok": False, "error": "invalid_json"}
            if not data.get("ok", True):
                LOGGER.warning("Rubika API error for %s: %s", method, data)
            return data

    async def _sleep_before_retry(self, attempt: int, method: str, error: str) -> None:
        backoff = self.retry_backoff * (2 ** (attempt - 1))
        jitter = random.uniform(0, self.retry_backoff)
        sleep_for = backoff + jitter
        LOGGER.warning("Retrying %s after error (%s). attempt=%s sleep=%.2fs", method, error, attempt, sleep_for)
        await asyncio.sleep(sleep_for)

    async def request(self, method: str, payload: dict[str, Any]) -> dict[str, Any]:
        return await self.api_call(method, payload)

    async def get_me(self) -> dict[str, Any]:
        return await self.request("getMe", {})

    async def send_message(
        self,
        chat_id: str,
        text: str,
        *,
        inline_keypad: dict | None = None,
        keypad: dict | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"chat_id": chat_id, "text": text}
        if inline_keypad:
            payload["inline_keypad"] = inline_keypad
        if keypad:
            payload["keypad"] = keypad
        return await self.request("sendMessage", payload)

    async def send_poll(self, chat_id: str, question: str, options: list[str]) -> dict[str, Any]:
        return await self.request("sendPoll", {"chat_id": chat_id, "question": question, "options": options})

    async def send_location(self, chat_id: str, latitude: float, longitude: float) -> dict[str, Any]:
        return await self.request("sendLocation", {"chat_id": chat_id, "latitude": latitude, "longitude": longitude})

    async def send_contact(self, chat_id: str, first_name: str, phone_number: str) -> dict[str, Any]:
        return await self.request(
            "sendContact",
            {"chat_id": chat_id, "first_name": first_name, "phone_number": phone_number},
        )

    async def get_chat(self, chat_id: str) -> dict[str, Any]:
        return await self.request("getChat", {"chat_id": chat_id})

    async def get_updates(self, offset: int | None = None, limit: int | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        if offset is not None:
            payload["offset"] = offset
        if limit is not None:
            payload["limit"] = limit
        return await self.request("getUpdates", payload)

    async def forward_message(self, chat_id: str, from_chat_id: str, message_id: str) -> dict[str, Any]:
        return await self.request(
            "forwardMessage",
            {"chat_id": chat_id, "from_chat_id": from_chat_id, "message_id": message_id},
        )

    async def edit_message_text(self, chat_id: str, message_id: str, text: str) -> dict[str, Any]:
        return await self.request("editMessageText", {"chat_id": chat_id, "message_id": message_id, "text": text})

    async def edit_inline_keypad(self, chat_id: str, message_id: str, inline_keypad: dict) -> dict[str, Any]:
        return await self.request(
            "editInlineKeypad",
            {"chat_id": chat_id, "message_id": message_id, "inline_keypad": inline_keypad},
        )

    async def edit_chat_keypad(self, chat_id: str, keypad: dict | None) -> dict[str, Any]:
        payload: dict[str, Any] = {"chat_id": chat_id}
        if keypad:
            payload["keypad"] = keypad
        else:
            payload["remove_keypad"] = True
        return await self.request("editChatKeypad", payload)

    async def delete_message(self, chat_id: str, message_id: str) -> dict[str, Any]:
        return await self.request("deleteMessage", {"chat_id": chat_id, "message_id": message_id})

    async def get_file(self, file_id: str) -> dict[str, Any]:
        return await self.request("getFile", {"file_id": file_id})

    async def request_send_file(self, file_id: str) -> dict[str, Any]:
        return await self.request("requestSendFile", {"file_id": file_id})

    async def send_file(self, chat_id: str, file_id: str, caption: str | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {"chat_id": chat_id, "file_id": file_id}
        if caption:
            payload["caption"] = caption
        return await self.request("sendFile", payload)

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
