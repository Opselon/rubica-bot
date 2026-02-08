from __future__ import annotations

import sqlite3
import time
from dataclasses import dataclass
from typing import Iterable

from app.utils.cache import LruTtlCache


@dataclass
class GroupSettings:
    chat_id: str
    title: str | None
    anti_link: bool
    anti_flood: bool
    anti_spam: bool
    anti_badwords: bool
    anti_forward: bool
    flood_limit: int


class Repository:
    def __init__(self, db_path: str, *, cache_size: int = 1024, cache_ttl_seconds: int = 90) -> None:
        self.db_path = db_path
        self._group_cache = LruTtlCache[str, GroupSettings](cache_size, cache_ttl_seconds)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        self._apply_pragmas(conn)
        return conn

    def _apply_pragmas(self, conn: sqlite3.Connection) -> None:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("PRAGMA temp_store=MEMORY;")
        conn.execute("PRAGMA cache_size=-20000;")
        conn.execute("PRAGMA busy_timeout=3000;")
        conn.execute("PRAGMA foreign_keys=ON;")

    def upsert_group(self, chat_id: str, title: str | None) -> GroupSettings:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO groups (chat_id, title)
                VALUES (?, ?)
                ON CONFLICT(chat_id) DO UPDATE SET
                    title = excluded.title,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (chat_id, title),
            )
            conn.commit()
        self._group_cache.invalidate(chat_id)
        return self.get_group(chat_id)

    def get_group(self, chat_id: str) -> GroupSettings:
        cached = self._group_cache.get(chat_id)
        if cached:
            return cached
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM groups WHERE chat_id = ?;", (chat_id,)).fetchone()
            if row is None:
                settings = GroupSettings(
                    chat_id=chat_id,
                    title=None,
                    anti_link=True,
                    anti_flood=False,
                    anti_spam=False,
                    anti_badwords=False,
                    anti_forward=False,
                    flood_limit=6,
                )
                self._group_cache.set(chat_id, settings)
                return settings
            settings = GroupSettings(
                chat_id=row["chat_id"],
                title=row["title"],
                anti_link=bool(row["anti_link"]),
                anti_flood=bool(row["anti_flood"]),
                anti_spam=bool(row["anti_spam"]),
                anti_badwords=bool(row["anti_badwords"]),
                anti_forward=bool(row["anti_forward"]),
                flood_limit=int(row["flood_limit"]),
            )
            self._group_cache.set(chat_id, settings)
            return settings

    def set_group_flag(self, chat_id: str, key: str, value: bool) -> None:
        with self._connect() as conn:
            conn.execute(
                f"UPDATE groups SET {key} = ?, updated_at = CURRENT_TIMESTAMP WHERE chat_id = ?;",
                (1 if value else 0, chat_id),
            )
            conn.commit()
        self._group_cache.invalidate(chat_id)

    def add_admin(self, chat_id: str, user_id: str, role: str = "admin") -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO admins (chat_id, user_id, role)
                VALUES (?, ?, ?)
                ON CONFLICT(chat_id, user_id) DO UPDATE SET role = excluded.role
                """,
                (chat_id, user_id, role),
            )
            conn.commit()

    def is_admin(self, chat_id: str, user_id: str) -> bool:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM admins WHERE chat_id = ? AND user_id = ?;",
                (chat_id, user_id),
            ).fetchone()
            return row is not None

    def count_admins(self, chat_id: str) -> int:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT COUNT(1) AS total FROM admins WHERE chat_id = ?;",
                (chat_id,),
            ).fetchone()
            return int(row["total"] if row else 0)

    def add_filter(self, chat_id: str, word: str, is_whitelist: bool, regex_enabled: bool) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO filters (chat_id, word, is_whitelist, regex_enabled)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(chat_id, word) DO UPDATE SET
                    is_whitelist = excluded.is_whitelist,
                    regex_enabled = excluded.regex_enabled
                """,
                (chat_id, word, 1 if is_whitelist else 0, 1 if regex_enabled else 0),
            )
            conn.commit()

    def remove_filter(self, chat_id: str, word: str) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM filters WHERE chat_id = ? AND word = ?;", (chat_id, word))
            conn.commit()

    def list_filters(self, chat_id: str) -> list[tuple[str, bool, bool]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT word, is_whitelist, regex_enabled FROM filters WHERE chat_id = ? ORDER BY word;",
                (chat_id,),
            ).fetchall()
        return [(row["word"], bool(row["is_whitelist"]), bool(row["regex_enabled"])) for row in rows]

    def save_message(self, chat_id: str, message_id: str, sender_id: str | None, text: str | None) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO messages (chat_id, message_id, sender_id, text)
                VALUES (?, ?, ?, ?)
                """,
                (chat_id, message_id, sender_id, text),
            )
            conn.commit()

    def fetch_recent_message_ids(self, chat_id: str, limit: int) -> list[str]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT message_id FROM messages WHERE chat_id = ? ORDER BY id DESC LIMIT ?;",
                (chat_id, limit),
            ).fetchall()
        return [row["message_id"] for row in rows]

    def bulk_insert_messages(self, rows: Iterable[tuple[str, str, str | None, str | None]]) -> None:
        with self._connect() as conn:
            conn.executemany(
                "INSERT INTO messages (chat_id, message_id, sender_id, text) VALUES (?, ?, ?, ?);",
                list(rows),
            )
            conn.commit()

    def save_incoming_update(
        self,
        job_id: str,
        received_at: float,
        chat_id: str | None,
        message_id: str | None,
        sender_id: str | None,
        update_type: str | None,
        text: str | None,
        raw_payload: str | None,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO incoming_updates (
                    job_id, received_at, chat_id, message_id, sender_id, update_type, text, raw_payload
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (job_id, received_at, chat_id, message_id, sender_id, update_type, text, raw_payload),
            )
            conn.commit()

    def cleanup_incoming_updates(self, max_age_seconds: int) -> int:
        cutoff = time.time() - max_age_seconds
        with self._connect() as conn:
            cursor = conn.execute("DELETE FROM incoming_updates WHERE received_at < ?;", (cutoff,))
            conn.commit()
            return cursor.rowcount

    def trim_messages_per_chat(self, limit_per_chat: int) -> int:
        total_deleted = 0
        with self._connect() as conn:
            chat_rows = conn.execute("SELECT DISTINCT chat_id FROM messages;").fetchall()
            for row in chat_rows:
                chat_id = row["chat_id"]
                cursor = conn.execute(
                    """
                    DELETE FROM messages
                    WHERE chat_id = ?
                    AND id NOT IN (
                        SELECT id FROM messages WHERE chat_id = ? ORDER BY id DESC LIMIT ?
                    );
                    """,
                    (chat_id, chat_id, limit_per_chat),
                )
                total_deleted += cursor.rowcount
            conn.commit()
        return total_deleted

    def count_records(self, table: str) -> int:
        with self._connect() as conn:
            row = conn.execute(f"SELECT COUNT(1) AS total FROM {table};").fetchone()
            return int(row["total"] if row else 0)

    def fetch_latest_message(self) -> sqlite3.Row | None:
        with self._connect() as conn:
            return conn.execute("SELECT * FROM messages ORDER BY id DESC LIMIT 1;").fetchone()

    def set_setting(self, key: str, value: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO settings (key, value)
                VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value = excluded.value,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (key, value),
            )
            conn.commit()

    def get_setting(self, key: str) -> str | None:
        with self._connect() as conn:
            row = conn.execute("SELECT value FROM settings WHERE key = ?;", (key,)).fetchone()
            return str(row["value"]) if row else None
