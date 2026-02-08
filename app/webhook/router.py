from __future__ import annotations

import json
import logging
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Request, Response, status

from app.core.queue import Job
from app.utils.rate_limiter import RateLimiter
from app.utils.security import verify_signature
from app.utils.message import extract_message, get_chat_id, get_message_id, get_sender_id, get_text

LOGGER = logging.getLogger(__name__)


def build_router(
    settings,
    rate_limiter: RateLimiter,
) -> APIRouter:
    router = APIRouter()

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
        job = Job.build(
            job_id,
            chat_id=get_chat_id(message),
            message_id=get_message_id(message),
            sender_id=get_sender_id(message),
            update_type=payload.get("type"),
            text=get_text(message),
            raw_payload=payload,
        )
        context = request.app.state.context
        queue = request.app.state.queue
        try:
            context["repo"].save_incoming_update(
                job.job_id,
                job.received_at,
                job.chat_id,
                job.message_id,
                job.sender_id,
                job.update_type,
                job.text,
                json.dumps(payload, ensure_ascii=False),
            )
        except Exception:  # noqa: BLE001
            LOGGER.exception("Failed to persist incoming update snapshot")
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
