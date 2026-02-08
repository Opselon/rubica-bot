from __future__ import annotations


def mask_secret(value: str, visible: int = 4) -> str:
    if not value:
        return ""
    if len(value) <= visible * 2:
        return "*" * len(value)
    return f"{value[:visible]}...{value[-visible:]}"


def parse_sqlite_path(db_url: str) -> str:
    if db_url.startswith("sqlite:///"):
        return db_url.replace("sqlite:///", "", 1)
    return db_url
