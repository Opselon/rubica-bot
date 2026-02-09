from __future__ import annotations

from importlib.util import find_spec

from pydantic import BaseSettings, Field

DOTENV_AVAILABLE = find_spec("dotenv") is not None


class Settings(BaseSettings):
    bot_token: str = Field(..., env="RUBIKA_BOT_TOKEN")
    owner_id: str | None = Field(default=None, env="RUBIKA_OWNER_ID")
    webhook_secret: str | None = Field(default=None, env="RUBIKA_WEBHOOK_SECRET")
    database_url: str = Field(default="sqlite:///data/bot.db", env="RUBIKA_DB_URL")
    api_base_url: str = Field(default="https://botapi.rubika.ir/v3", env="RUBIKA_API_BASE_URL")
    api_timeout_seconds: float = Field(default=10.0, env="RUBIKA_API_TIMEOUT_SECONDS")
    api_retry_attempts: int = Field(default=3, env="RUBIKA_API_RETRY_ATTEMPTS")
    api_retry_backoff: float = Field(default=0.5, env="RUBIKA_API_RETRY_BACKOFF")
    api_rate_limit_per_second: int = Field(default=20, env="RUBIKA_API_RATE_LIMIT_PER_SECOND")
    webhook_base_url: str | None = Field(default=None, env="RUBIKA_WEBHOOK_BASE_URL")
    log_level: str = Field(default="INFO", env="RUBIKA_LOG_LEVEL")
    log_file: str = Field(default="/var/log/rubika-bot/app.log", env="RUBIKA_LOG_FILE")
    worker_concurrency: int = Field(default=4, env="RUBIKA_WORKER_CONCURRENCY")
    queue_max_size: int = Field(default=1000, env="RUBIKA_QUEUE_MAX_SIZE")
    queue_full_policy: str = Field(default="reject", env="RUBIKA_QUEUE_FULL_POLICY")
    rate_limit_per_minute: int = Field(default=120, env="RUBIKA_RATE_LIMIT_PER_MINUTE")
    dedup_ttl_seconds: int = Field(default=120, env="RUBIKA_DEDUP_TTL_SECONDS")
    settings_cache_ttl_seconds: int = Field(default=90, env="RUBIKA_SETTINGS_CACHE_TTL_SECONDS")
    settings_cache_size: int = Field(default=1024, env="RUBIKA_SETTINGS_CACHE_SIZE")
    incoming_updates_enabled: bool = Field(default=True, env="RUBIKA_INCOMING_UPDATES_ENABLED")
    incoming_updates_store_raw: bool = Field(default=False, env="RUBIKA_INCOMING_UPDATES_STORE_RAW")
    incoming_updates_retention_hours: int = Field(default=48, env="RUBIKA_INCOMING_UPDATES_RETENTION_HOURS")
    messages_keep_per_chat: int = Field(default=10000, env="RUBIKA_MESSAGES_KEEP_PER_CHAT")
    register_webhook: bool = Field(default=True, env="RUBIKA_REGISTER_WEBHOOK")
    panel_enabled: bool = Field(default=True, env="RUBIKA_PANEL_ENABLED")

    class Config:
        env_file = ".env" if DOTENV_AVAILABLE else None
        case_sensitive = False


settings = Settings()
