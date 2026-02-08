import tempfile

from app.db import Repository, ensure_schema


def test_settings_roundtrip():
    with tempfile.TemporaryDirectory() as tmp:
        db_path = f"{tmp}/bot.db"
        ensure_schema(db_path)
        repo = Repository(db_path)
        repo.set_setting("bot_token", "abc")
        assert repo.get_setting("bot_token") == "abc"
