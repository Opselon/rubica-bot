from __future__ import annotations

import re


LINK_PATTERN = re.compile(
    r"(?:https?://|www\.|t\.me/|telegram\.me/|rubika\.ir/|\b[A-Za-z0-9.-]+\.(?:ir|com|net|org|io|me|co|app|dev))",
    re.IGNORECASE,
)


def contains_link(text: str | None) -> bool:
    if not text:
        return False
    return bool(LINK_PATTERN.search(text))
