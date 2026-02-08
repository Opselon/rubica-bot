from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


def setup_logging(level: str = "INFO", log_file: str = "/var/log/rubika-bot/app.log") -> None:
    log_path = Path(log_file)
    fallback_path = Path("logs") / "rubica-bot.log"
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        handler_path = log_path
    except PermissionError:
        fallback_path.parent.mkdir(parents=True, exist_ok=True)
        handler_path = fallback_path
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            RotatingFileHandler(
                handler_path,
                maxBytes=5 * 1024 * 1024,
                backupCount=5,
            ),
            logging.StreamHandler(),
        ],
    )
