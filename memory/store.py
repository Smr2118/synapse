"""SQLite-backed conversation memory store.

Schema
------
sessions  — one row per conversation session (id, created_at)
messages  — ordered turns within a session (role, content, metadata JSON)

The DB file path defaults to synapse_memory.db at the project root but can be
overridden with the MEMORY_DB_PATH env var so a Render persistent-disk mount
works without code changes.
"""

from __future__ import annotations

import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(os.getenv("MEMORY_DB_PATH", str(Path(__file__).resolve().parent.parent / "synapse_memory.db")))

_DDL = """
CREATE TABLE IF NOT EXISTS sessions (
    id         TEXT PRIMARY KEY,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS messages (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT    NOT NULL,
    role       TEXT    NOT NULL,
    content    TEXT    NOT NULL,
    metadata   TEXT,
    created_at TEXT    NOT NULL,
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);
"""


def _conn() -> sqlite3.Connection:
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


def init_db() -> None:
    with _conn() as con:
        con.executescript(_DDL)


def create_session(session_id: str | None = None) -> str:
    sid = session_id or str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    with _conn() as con:
        con.execute(
            "INSERT OR IGNORE INTO sessions (id, created_at) VALUES (?, ?)",
            (sid, now),
        )
    return sid


def add_message(session_id: str, role: str, content: str, metadata: dict | None = None) -> None:
    now = datetime.now(timezone.utc).isoformat()
    with _conn() as con:
        con.execute(
            "INSERT INTO messages (session_id, role, content, metadata, created_at) VALUES (?, ?, ?, ?, ?)",
            (session_id, role, content, json.dumps(metadata) if metadata else None, now),
        )


def get_messages(session_id: str, limit: int = 20) -> list[dict]:
    with _conn() as con:
        rows = con.execute(
            "SELECT role, content, metadata, created_at FROM messages "
            "WHERE session_id = ? ORDER BY id DESC LIMIT ?",
            (session_id, limit),
        ).fetchall()
    messages = [dict(r) for r in reversed(rows)]
    for m in messages:
        if m["metadata"]:
            m["metadata"] = json.loads(m["metadata"])
    return messages


def delete_session(session_id: str) -> int:
    with _conn() as con:
        n = con.execute("DELETE FROM messages WHERE session_id = ?", (session_id,)).rowcount
        con.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
    return n


def list_sessions(limit: int = 50) -> list[dict]:
    with _conn() as con:
        rows = con.execute(
            "SELECT s.id, s.created_at, COUNT(m.id) AS message_count "
            "FROM sessions s LEFT JOIN messages m ON m.session_id = s.id "
            "GROUP BY s.id ORDER BY s.created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]
