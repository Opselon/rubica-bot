import pytest

from app.services.handlers import models_handler
from app.utils.models_doc import MODELS_DOC


class DummyClient:
    def __init__(self) -> None:
        self.messages = []

    async def send_message(self, chat_id, text, inline_keypad=None):
        self.messages.append((chat_id, text, inline_keypad))
        return {"ok": True}


@pytest.mark.asyncio
async def test_models_handler_sends_full_doc():
    client = DummyClient()
    context = {"client": client}
    message = {"chat_id": "123"}

    await models_handler(message, context, [])

    assert client.messages == [("123", MODELS_DOC, None)]


def test_models_doc_has_expected_sections():
    assert MODELS_DOC.startswith("پرش به محتویات\nlogo\nبات روبیکا\nمدل ها\n\n\nبات روبیکا\nمعرفی\nمتد ها\nمدل ها\nگروه ها و کانال ها\nفهرست موضوعات\nChat\n")
    assert "Chat¶" in MODELS_DOC
    assert "BotCommand¶" in MODELS_DOC
    assert "UpdateEndpointTypeEnum¶" in MODELS_DOC
    assert MODELS_DOC.strip().endswith("بعدیگروه ها و کانال ها")
