import tempfile

from app.db import Repository, ensure_schema


def test_repository_filters():
    with tempfile.TemporaryDirectory() as tmp:
        db_path = f"{tmp}/bot.db"
        ensure_schema(db_path)
        repo = Repository(db_path)
        repo.add_filter("chat1", "bad", is_whitelist=False, regex_enabled=False)
        filters = repo.list_filters("chat1")
        assert filters[0][0] == "bad"
