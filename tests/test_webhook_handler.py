from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.queue import JobQueue
from app.db import Repository, ensure_schema
from app.utils.dedup import Deduplicator
from app.utils.rate_limiter import RateLimiter
from app.webhook.router import build_router


class _Settings:
    webhook_secret = None


def test_webhook_handler_returns_200(tmp_path) -> None:
    db_path = tmp_path / "bot.db"
    ensure_schema(str(db_path))
    repo = Repository(str(db_path))
    queue = JobQueue(max_size=10, deduplicator=Deduplicator(60))
    app = FastAPI()
    app.state.context = {"repo": repo}
    app.state.queue = queue
    app.include_router(build_router(settings=_Settings(), rate_limiter=RateLimiter(1000)))
    client = TestClient(app)
    payload = {
        "update_id": "1",
        "message": {
            "message_id": "m1",
            "chat": {"id": "c1"},
            "sender": {"id": "u1"},
            "text": "hi",
        },
    }
    response = client.post("/receiveUpdate", json=payload)
    assert response.status_code == 200
    assert queue.size() == 1
