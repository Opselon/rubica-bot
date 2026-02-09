import importlib
import sys
import time

import pytest
from fastapi.testclient import TestClient


class FakeRubikaClient:
    def __init__(self, *args, **kwargs) -> None:
        self.sent_messages: list[tuple[str, str]] = []
        self.deleted_messages: list[tuple[str, str]] = []
        self.banned_members: list[tuple[str, str]] = []

    async def send_message(self, chat_id: str, text: str, **kwargs) -> dict[str, object]:
        self.sent_messages.append((chat_id, text))
        return {"ok": True}

    async def delete_message(self, chat_id: str, message_id: str) -> dict[str, object]:
        self.deleted_messages.append((chat_id, message_id))
        return {"ok": True}

    async def ban_chat_member(self, chat_id: str, user_id: str) -> dict[str, object]:
        self.banned_members.append((chat_id, user_id))
        return {"ok": True}

    async def set_commands(self, commands: list[dict[str, str]]) -> dict[str, object]:
        return {"ok": True}

    async def update_bot_endpoints(self, urls: list[str]) -> dict[str, object]:
        return {"ok": True}

    async def close(self) -> None:
        return None


def _wait_for(condition, timeout: float = 0.5) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if condition():
            return
        time.sleep(0.01)
    assert condition()


def _load_app(tmp_path, monkeypatch) -> TestClient:
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
    return TestClient(app)


@pytest.mark.e2e
def test_moderation_anti_link_deletes_and_bans(tmp_path, monkeypatch) -> None:
    with _load_app(tmp_path, monkeypatch) as client:
        payload = {
            "update_id": "10",
            "message": {
                "message_id": "m10",
                "chat": {"id": "g1", "type": "Group"},
                "sender": {"id": "u10"},
                "text": "check https://example.com",
            },
        }
        response = client.post("/receiveUpdate", json=payload)
        assert response.status_code == 200
        fake_client = client.app.state.context["client"]
        _wait_for(lambda: len(fake_client.deleted_messages) == 1)
        _wait_for(lambda: len(fake_client.banned_members) == 1)
        assert fake_client.deleted_messages[-1] == ("g1", "m10")
        assert fake_client.banned_members[-1] == ("g1", "u10")


@pytest.mark.e2e
def test_moderation_anti_flood_bans(tmp_path, monkeypatch) -> None:
    with _load_app(tmp_path, monkeypatch) as client:
        repo = client.app.state.context["repo"]
        repo.upsert_group("g2", "Test Group")
        repo.set_group_flag("g2", "anti_flood", True)
        for index in range(8):
            payload = {
                "update_id": f"20-{index}",
                "message": {
                    "message_id": f"m20-{index}",
                    "chat": {"id": "g2", "type": "Group"},
                    "sender": {"id": "u20"},
                    "text": f"spam {index}",
                },
            }
            response = client.post("/receiveUpdate", json=payload)
            assert response.status_code == 200
        fake_client = client.app.state.context["client"]
        _wait_for(lambda: len(fake_client.banned_members) >= 1, timeout=1.0)
        assert ("g2", "u20") in fake_client.banned_members
