import importlib
import sys

import pytest
from fastapi.testclient import TestClient


@pytest.mark.e2e
def test_app_health_endpoints(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("RUBIKA_BOT_TOKEN", "test-token")
    monkeypatch.setenv("RUBIKA_DB_URL", f"sqlite:///{tmp_path / 'bot.db'}")
    monkeypatch.setenv("RUBIKA_REGISTER_WEBHOOK", "false")

    if "app.config" in sys.modules:
        importlib.reload(sys.modules["app.config"])
    else:
        import app.config  # noqa: F401

    if "app.main" in sys.modules:
        importlib.reload(sys.modules["app.main"])
    else:
        import app.main  # noqa: F401

    app = sys.modules["app.main"].app

    with TestClient(app) as client:
        health = client.get("/health")
        assert health.status_code == 200
        assert health.json()["status"] == "ok"

        queue = client.get("/health/queue")
        assert queue.status_code == 200
        payload = queue.json()
        assert payload["queue"]["max_size"] > 0

        drained = client.post("/health/queue/drain")
        assert drained.status_code == 200
