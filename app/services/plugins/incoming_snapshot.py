from __future__ import annotations

import json
import logging
from typing import Any

from .base import Plugin

LOGGER = logging.getLogger(__name__)


class IncomingSnapshotPlugin(Plugin):
    name = "incoming_snapshot"

    async def handle(self, update: dict[str, Any], context: dict[str, Any]) -> bool:
        settings = context.get("settings")
        if not settings or not settings.incoming_updates_enabled:
            return False
        repo = context["repo"]
        job = context.get("job")
        if not job:
            return False
        raw_payload = None
        if settings.incoming_updates_store_raw:
            try:
                raw_payload = json.dumps(update, ensure_ascii=False)
            except TypeError:
                raw_payload = None
        try:
            repo.save_incoming_update(
                job.job_id,
                job.received_at,
                job.chat_id,
                job.message_id,
                job.sender_id,
                job.update_type,
                job.text,
                raw_payload,
            )
        except Exception:  # noqa: BLE001
            LOGGER.exception("Failed to persist incoming update snapshot")
        return False
