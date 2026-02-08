from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

LOGGER = logging.getLogger(__name__)

SCHEMA_VERSION = 3


INITIAL_SCHEMA = [
    """
    CREATE TABLE IF NOT EXISTS schema_version (
        version INTEGER NOT NULL
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS groups (
        chat_id TEXT PRIMARY KEY,
        title TEXT,
        anti_link INTEGER DEFAULT 1,
        anti_flood INTEGER DEFAULT 0,
        anti_spam INTEGER DEFAULT 0,
        anti_badwords INTEGER DEFAULT 0,
        anti_forward INTEGER DEFAULT 0,
        flood_limit INTEGER DEFAULT 6,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS admins (
        chat_id TEXT NOT NULL,
        user_id TEXT NOT NULL,
        role TEXT DEFAULT 'admin',
        PRIMARY KEY (chat_id, user_id)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS filters (
        chat_id TEXT NOT NULL,
        word TEXT NOT NULL,
        is_whitelist INTEGER DEFAULT 0,
        regex_enabled INTEGER DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (chat_id, word)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chat_id TEXT NOT NULL,
        message_id TEXT NOT NULL,
        sender_id TEXT,
        text TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_messages_chat_created
        ON messages (chat_id, id DESC);
    """,
    """
    CREATE TABLE IF NOT EXISTS anti_state (
        chat_id TEXT NOT NULL,
        key TEXT NOT NULL,
        value TEXT NOT NULL,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (chat_id, key)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS incoming_updates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        job_id TEXT NOT NULL,
        received_at REAL NOT NULL,
        chat_id TEXT,
        message_id TEXT,
        sender_id TEXT,
        update_type TEXT,
        text TEXT,
        raw_payload TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_incoming_updates_job
        ON incoming_updates (job_id);
    """,
]


MIGRATIONS = {
    1: [],
    2: [
        """
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        """,
    ],
    3: [
        """
        CREATE TABLE IF NOT EXISTS incoming_updates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id TEXT NOT NULL,
            received_at REAL NOT NULL,
            chat_id TEXT,
            message_id TEXT,
            sender_id TEXT,
            update_type TEXT,
            text TEXT,
            raw_payload TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        """,
        """
        CREATE INDEX IF NOT EXISTS idx_incoming_updates_job
            ON incoming_updates (job_id);
        """,
    ],
}


def ensure_schema(db_path: str) -> None:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        for statement in INITIAL_SCHEMA:
            cursor.execute(statement)
        conn.commit()
        cursor.execute("SELECT version FROM schema_version LIMIT 1;")
        row = cursor.fetchone()
        if row is None:
            cursor.execute("INSERT INTO schema_version (version) VALUES (?);", (SCHEMA_VERSION,))
            conn.commit()
            return
        current_version = int(row["version"])
        if current_version < SCHEMA_VERSION:
            for version in range(current_version + 1, SCHEMA_VERSION + 1):
                for statement in MIGRATIONS.get(version, []):
                    cursor.execute(statement)
            cursor.execute("UPDATE schema_version SET version = ?;", (SCHEMA_VERSION,))
            conn.commit()
            LOGGER.info("Migrated schema from %s to %s", current_version, SCHEMA_VERSION)
