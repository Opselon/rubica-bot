from app.cli.doctor_utils import mask_secret, parse_sqlite_path


def test_mask_secret() -> None:
    assert mask_secret("abcd1234", visible=2) == "ab...34"
    assert mask_secret("short", visible=4) == "*****"


def test_parse_sqlite_path() -> None:
    assert parse_sqlite_path("sqlite:///data/bot.db") == "data/bot.db"
    assert parse_sqlite_path("/tmp/test.db") == "/tmp/test.db"
