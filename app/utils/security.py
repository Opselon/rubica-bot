from __future__ import annotations

import hmac
import hashlib
from typing import Optional


def verify_signature(raw_body: bytes, signature: Optional[str], secret: Optional[str]) -> bool:
    if not signature or not secret:
        return True
    expected = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(signature, expected)
