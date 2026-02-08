from __future__ import annotations

import json
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Request, Response, status

from app.core.queue import Job
from app.utils.rate_limiter import RateLimiter
from app.utils.security import verify_signature
from app.utils.message import extract_message, get_chat_id, get_message_id, get_sender_id, get_text


def build_router(
    settings,
    rate_limiter: RateLimiter,
) -> APIRouter:
    router = APIRouter()
    admin_commands = {
        "ban",
        "unban",
        "del",
        "antilink",
        "filter",
        "settings",
        "admins",
        "setcmd",
        "panel",
    }

    async def handle_request(request: Request) -> Response:
        raw_body = await request.body()
        signature = request.headers.get("X-Rubika-Signature")
        if not verify_signature(raw_body, signature, settings.webhook_secret):
            return Response(status_code=status.HTTP_401_UNAUTHORIZED)
        if not rate_limiter.allow():
            return Response(status_code=status.HTTP_429_TOO_MANY_REQUESTS)
        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except json.JSONDecodeError:
            return Response(status_code=status.HTTP_400_BAD_REQUEST)
        message = extract_message(payload) or {}
        update_id = payload.get("update_id") or payload.get("message_id") or message.get("message_id")
        job_id = str(update_id) if update_id is not None else str(uuid4())
        update_type = payload.get("type")
        chat_id = get_chat_id(message)
        message_id = get_message_id(message)
        sender_id = get_sender_id(message)
        text = get_text(message)
        button_id = payload.get("button_id") or message.get("button_id")
        dedup_key = ":".join(
            [value for value in [chat_id, message_id, update_type, str(button_id) if button_id else None] if value]
        ) or job_id
        priority = "normal"
        if text:
            command = text.lstrip("/").split(maxsplit=1)[0].lower()
            if command in admin_commands:
                priority = "high"
            elif "http" in text or "t.me" in text or "rubika.ir" in text:
                priority = "high"
        job = Job.build(
            job_id,
            chat_id=chat_id,
            message_id=message_id,
            sender_id=sender_id,
            update_type=update_type,
            text=text,
            raw_payload=payload,
            dedup_key=dedup_key,
            priority=priority,
        )
        queue = request.app.state.queue
        decision = await queue.enqueue(job)
        if decision == "dropped":
            return Response(status_code=status.HTTP_503_SERVICE_UNAVAILABLE)
        if decision == "duplicate":
            return Response(status_code=status.HTTP_200_OK)
        return Response(status_code=status.HTTP_200_OK)

    @router.post("/receiveUpdate")
    async def receive_update(request: Request) -> Response:
        return await handle_request(request)

    @router.post("/receiveInlineMessage")
    async def receive_inline_message(request: Request) -> Response:
        return await handle_request(request)

    return router
