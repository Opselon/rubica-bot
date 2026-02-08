import asyncio

from app.db import Repository, ensure_schema
from app.services.handlers import delete_handler


class DummyClient:
    def __init__(self) -> None:
        self.deleted: list[tuple[str, str]] = []
        self.messages: list[tuple[str, str]] = []

    async def delete_message(self, chat_id: str, message_id: str) -> dict[str, bool]:
        self.deleted.append((chat_id, message_id))
        return {"ok": True}

    async def send_message(self, chat_id: str, text: str, **kwargs) -> dict[str, bool]:
        self.messages.append((chat_id, text))
        return {"ok": True}


def test_delete_handler_deletes_recent_messages(tmp_path):
    db_path = tmp_path / "bot.db"
    ensure_schema(str(db_path))
    repo = Repository(str(db_path))
    repo.bulk_insert_messages(
        [
            ("chat-1", "m1", "u1", "one"),
            ("chat-1", "m2", "u1", "two"),
            ("chat-1", "m3", "u1", "three"),
        ]
    )
    client = DummyClient()
    message = {"chat": {"id": "chat-1"}, "message_id": "m10", "sender": {"id": "admin"}, "text": "/del 2"}
    context = {"repo": repo, "client": client}

    asyncio.run(delete_handler(message, context, ["2"]))

    assert len(client.deleted) == 2
    assert client.messages
    assert "حذف شد" in client.messages[-1][1]
