from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from fastapi import FastAPI

from app.config import settings
from app.db import Repository, ensure_schema
from app.logging_config import setup_logging
from app.services.api_client import RubikaClient
from app.services.dispatcher import Dispatcher
from app.services.handlers import (
    antilink_handler,
    ban_handler,
    coin_handler,
    delete_handler,
    filter_handler,
    help_handler,
    joke_handler,
    ping_handler,
    roll_handler,
    setcmd_handler,
    unban_handler,
)
from app.services.plugins.anti_flood import AntiFloodPlugin
from app.services.plugins.anti_link import AntiLinkPlugin
from app.services.plugins.commands import Command, CommandRegistry, CommandsPlugin
from app.services.plugins.filters import FilterWordsPlugin
from app.services.plugins.logging import MessageLoggingPlugin
from app.services.plugins.panel import PanelPlugin
from app.services.plugins.registry import PluginRegistry
from app.utils.dedup import Deduplicator
from app.utils.rate_limiter import RateLimiter
from app.webhook.router import build_router

setup_logging(settings.log_level)
LOGGER = logging.getLogger(__name__)

app = FastAPI(title="Rubika Bot API v3")


def _resolve_db_path(url: str) -> str:
    if url.startswith("sqlite:///"):
        return url.replace("sqlite:///", "", 1)
    return url


@app.on_event("startup")
async def startup() -> None:
    db_path = _resolve_db_path(settings.database_url)
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    ensure_schema(db_path)
    repo = Repository(db_path)
    client = RubikaClient(settings.bot_token, settings.api_base_url)
    command_registry = CommandRegistry()
    command_registry.register(Command("help", "نمایش راهنما", help_handler))
    command_registry.register(Command("setcmd", "ثبت دستورات", setcmd_handler, admin_only=True))
    command_registry.register(Command("ping", "تست سرعت", ping_handler))
    command_registry.register(Command("coin", "شیر یا خط", coin_handler))
    command_registry.register(Command("roll", "تاس", roll_handler))
    command_registry.register(Command("joke", "جوک کوتاه", joke_handler))
    command_registry.register(Command("antilink", "تنظیم ضد لینک", antilink_handler, admin_only=True))
    command_registry.register(Command("filter", "مدیریت فیلتر", filter_handler, admin_only=True))
    command_registry.register(Command("del", "حذف انبوه", delete_handler, admin_only=True))
    command_registry.register(Command("ban", "بن کاربر", ban_handler, admin_only=True))
    command_registry.register(Command("unban", "رفع بن", unban_handler, admin_only=True))

    registry = PluginRegistry(
        [
            MessageLoggingPlugin(),
            AntiLinkPlugin(),
            AntiFloodPlugin(),
            FilterWordsPlugin(),
            CommandsPlugin(command_registry),
            PanelPlugin(),
        ]
    )
    dispatcher = Dispatcher(registry, settings.worker_concurrency)
    await dispatcher.start()
    app.state.context = {
        "repo": repo,
        "client": client,
        "command_registry": command_registry,
        "report_anti_actions": True,
    }
    app.state.dispatcher = dispatcher

    if settings.register_webhook and settings.webhook_base_url:
        webhook_base = settings.webhook_base_url.rstrip("/")
        await client.update_bot_endpoints(
            [
                f"{webhook_base}/receiveUpdate",
                f"{webhook_base}/receiveInlineMessage",
            ]
        )
        await client.set_commands(command_registry.list_commands())


@app.on_event("shutdown")
async def shutdown() -> None:
    dispatcher = app.state.dispatcher
    await dispatcher.stop()
    await app.state.context["client"].close()


rate_limiter = RateLimiter(settings.rate_limit_per_minute)
app.include_router(
    build_router(
        settings=settings,
        rate_limiter=rate_limiter,
        deduplicator=Deduplicator(settings.dedup_ttl_seconds),
    )
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
