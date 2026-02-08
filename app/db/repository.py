from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Iterable


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
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

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
        return self.get_group(chat_id)

    def get_group(self, chat_id: str) -> GroupSettings:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM groups WHERE chat_id = ?;", (chat_id,)).fetchone()
            if row is None:
                return GroupSettings(
                    chat_id=chat_id,
                    title=None,
                    anti_link=True,
                    anti_flood=False,
                    anti_spam=False,
                    anti_badwords=False,
                    anti_forward=False,
                    flood_limit=6,
                )
            return GroupSettings(
                chat_id=row["chat_id"],
                title=row["title"],
                anti_link=bool(row["anti_link"]),
                anti_flood=bool(row["anti_flood"]),
                anti_spam=bool(row["anti_spam"]),
                anti_badwords=bool(row["anti_badwords"]),
                anti_forward=bool(row["anti_forward"]),
                flood_limit=int(row["flood_limit"]),
            )

    def set_group_flag(self, chat_id: str, key: str, value: bool) -> None:
        with self._connect() as conn:
            conn.execute(
                f"UPDATE groups SET {key} = ?, updated_at = CURRENT_TIMESTAMP WHERE chat_id = ?;",
                (1 if value else 0, chat_id),
            )
            conn.commit()

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
