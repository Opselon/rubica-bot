from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import APIRouter, Request, Response, status

from app.utils.dedup import Deduplicator
from app.utils.rate_limiter import RateLimiter
from app.utils.security import verify_signature

LOGGER = logging.getLogger(__name__)


def build_router(
    settings,
    rate_limiter: RateLimiter,
    deduplicator: Deduplicator,
) -> APIRouter:
    router = APIRouter()

    async def handle_request(request: Request) -> Response:
        raw_body = await request.body()
        signature = request.headers.get("X-Rubika-Signature")
        context = request.app.state.context
        webhook_secret = context.get("webhook_secret") or settings.webhook_secret
        if not verify_signature(raw_body, signature, webhook_secret):
            return Response(status_code=status.HTTP_401_UNAUTHORIZED)
        if not rate_limiter.allow():
            return Response(status_code=status.HTTP_429_TOO_MANY_REQUESTS)
        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except json.JSONDecodeError:
            LOGGER.warning("Invalid JSON payload")
            return Response(status_code=status.HTTP_400_BAD_REQUEST)
        update_id = payload.get("update_id") or payload.get("message_id")
        if deduplicator.seen(str(update_id)):
            return Response(status_code=status.HTTP_200_OK)
        dispatcher = request.app.state.dispatcher
        await dispatcher.enqueue(payload, context)
        return Response(status_code=status.HTTP_200_OK)

    @router.post("/receiveUpdate")
    async def receive_update(request: Request) -> Response:
        return await handle_request(request)

    @router.post("/receiveInlineMessage")
    async def receive_inline_message(request: Request) -> Response:
        return await handle_request(request)

    return router
