import importlib
import sys
import time

import pytest
from fastapi.testclient import TestClient


class FakeRubikaClient:
    def __init__(self, *args, **kwargs) -> None:
        self.sent_messages: list[tuple[str, str]] = []
        self.updated_urls: list[str] = []
        self.commands: list[dict[str, str]] = []

    async def send_message(self, chat_id: str, text: str, **kwargs) -> dict[str, object]:
        self.sent_messages.append((chat_id, text))
        return {"ok": True}

    async def update_bot_endpoints(self, urls: list[str]) -> dict[str, object]:
        self.updated_urls = urls
        return {"ok": True}

    async def set_commands(self, commands: list[dict[str, str]]) -> dict[str, object]:
        self.commands = commands
        return {"ok": True}

    async def close(self) -> None:
        return None


def _wait_for_messages(client: FakeRubikaClient, count: int, timeout: float = 0.5) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if len(client.sent_messages) >= count:
            return
        time.sleep(0.01)
    assert len(client.sent_messages) >= count


@pytest.mark.e2e
def test_api_models_command_sends_doc(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("RUBIKA_BOT_TOKEN", "test-token")
    monkeypatch.setenv("RUBIKA_DB_URL", f"sqlite:///{tmp_path / 'bot.db'}")
    monkeypatch.setenv("RUBIKA_REGISTER_WEBHOOK", "false")
    monkeypatch.setattr("app.core.rubika_client.RubikaClient", FakeRubikaClient)

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
        payload = {
            "update_id": "1",
            "message": {
                "message_id": "m1",
                "chat": {"id": "c1"},
                "sender": {"id": "u1"},
                "text": "/models",
            },
        }
        response = client.post("/receiveUpdate", json=payload)
        assert response.status_code == 200
        fake_client = app.state.context["client"]
        _wait_for_messages(fake_client, 1)
        assert fake_client.sent_messages[-1][0] == "c1"
        assert "مدل ها" in fake_client.sent_messages[-1][1]


@pytest.mark.e2e
def test_api_ping_command_sends_pong(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("RUBIKA_BOT_TOKEN", "test-token")
    monkeypatch.setenv("RUBIKA_DB_URL", f"sqlite:///{tmp_path / 'bot.db'}")
    monkeypatch.setenv("RUBIKA_REGISTER_WEBHOOK", "false")
    monkeypatch.setattr("app.core.rubika_client.RubikaClient", FakeRubikaClient)

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
        payload = {
            "update_id": "2",
            "message": {
                "message_id": "m2",
                "chat": {"id": "c2"},
                "sender": {"id": "u2"},
                "text": "/ping",
            },
        }
        response = client.post("/receiveUpdate", json=payload)
        assert response.status_code == 200
        fake_client = app.state.context["client"]
        _wait_for_messages(fake_client, 1)
        assert fake_client.sent_messages[-1] == ("c2", "pong")
