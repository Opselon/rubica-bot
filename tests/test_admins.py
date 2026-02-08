import tempfile

from app.db import Repository, ensure_schema


def test_admin_roundtrip():
    with tempfile.TemporaryDirectory() as tmp:
        db_path = f"{tmp}/bot.db"
        ensure_schema(db_path)
        repo = Repository(db_path)
        assert not repo.has_admins("chat1")
        repo.add_admin("chat1", "user1")
        assert repo.is_admin("chat1", "user1")
        assert repo.has_admins("chat1")
        admins = repo.list_admins("chat1")
        assert admins[0][0] == "user1"
        repo.remove_admin("chat1", "user1")
        assert not repo.is_admin("chat1", "user1")
