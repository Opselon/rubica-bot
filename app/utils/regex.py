from __future__ import annotations

import re


LINK_PATTERN = re.compile(
    r"("
    r"(?:https?://|www\.)\S+"
    r"|"
    r"(?:t\.me|telegram\.me|rubika\.ir|rubika\.com|rbx\.ir|rbx\.im|s\.rubika\.ir)/\S+"
    r"|"
    r"\b(?:bit\.ly|t\.co|goo\.gl|is\.gd|tinyurl\.com|ow\.ly|cutt\.ly|rebrand\.ly|s\.id)\b/\S*"
    r"|"
    r"\b(?:[a-z0-9-]+\.)+(?:ir|com|net|org|io|me|co|app|dev|xyz|info|site|biz|tv|online|link|shop)\b"
    r"(?:/\S*)?"
    r")",
    re.IGNORECASE,
)


def contains_link(text: str | None) -> bool:
    if not text:
        return False
    return bool(LINK_PATTERN.search(text))
