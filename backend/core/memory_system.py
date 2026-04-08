"""
XandriX Engineer - Memory System
Provides short-term (in-memory) and long-term (SQLite + embeddings) memory.
"""
import json
import sqlite3
import threading
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from backend.config import MEMORY_DB_PATH


class ShortTermMemory:
    """In-process memory for active task context."""

    def __init__(self, maxlen: int = 200):
        self._store: dict[str, Any] = {}
        self._history: deque = deque(maxlen=maxlen)
        self._lock = threading.Lock()

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            self._store[key] = value
            self._history.append({"key": key, "value": value, "ts": datetime.utcnow().isoformat()})

    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            return self._store.get(key, default)

    def update(self, data: dict[str, Any]) -> None:
        with self._lock:
            self._store.update(data)

    def delete(self, key: str) -> None:
        with self._lock:
            self._store.pop(key, None)

    def all(self) -> dict[str, Any]:
        with self._lock:
            return dict(self._store)

    def history(self) -> list[dict]:
        with self._lock:
            return list(self._history)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()
            self._history.clear()


class LongTermMemory:
    """Persistent memory backed by SQLite for cross-session recall."""

    def __init__(self, db_path: Path = MEMORY_DB_PATH):
        self._db_path = db_path
        self._local = threading.local()
        self._init_db()

    def _conn(self) -> sqlite3.Connection:
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._local.conn = sqlite3.connect(str(self._db_path), check_same_thread=False)
            self._local.conn.row_factory = sqlite3.Row
        return self._local.conn

    def _init_db(self) -> None:
        conn = sqlite3.connect(str(self._db_path))
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT,
                category TEXT NOT NULL,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_memories_category ON memories(category);
            CREATE INDEX IF NOT EXISTS idx_memories_task ON memories(task_id);

            CREATE TABLE IF NOT EXISTS facts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                tags TEXT,
                source TEXT,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS code_snippets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                language TEXT NOT NULL,
                code TEXT NOT NULL,
                description TEXT,
                tags TEXT,
                created_at TEXT NOT NULL
            );
        """)
        conn.commit()
        conn.close()

    def store(self, category: str, key: str, value: Any, task_id: Optional[str] = None) -> None:
        now = datetime.utcnow().isoformat()
        serialized = json.dumps(value)
        conn = self._conn()
        existing = conn.execute(
            "SELECT id FROM memories WHERE category=? AND key=? AND (task_id=? OR task_id IS NULL)",
            (category, key, task_id),
        ).fetchone()
        if existing:
            conn.execute(
                "UPDATE memories SET value=?, updated_at=? WHERE id=?",
                (serialized, now, existing["id"]),
            )
        else:
            conn.execute(
                "INSERT INTO memories (task_id, category, key, value, created_at, updated_at) VALUES (?,?,?,?,?,?)",
                (task_id, category, key, serialized, now, now),
            )
        conn.commit()

    def retrieve(self, category: str, key: str, task_id: Optional[str] = None) -> Any:
        conn = self._conn()
        row = conn.execute(
            "SELECT value FROM memories WHERE category=? AND key=? ORDER BY updated_at DESC LIMIT 1",
            (category, key),
        ).fetchone()
        if row:
            return json.loads(row["value"])
        return None

    def retrieve_all(self, category: str, task_id: Optional[str] = None) -> dict[str, Any]:
        conn = self._conn()
        if task_id:
            rows = conn.execute(
                "SELECT key, value FROM memories WHERE category=? AND task_id=?",
                (category, task_id),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT key, value FROM memories WHERE category=?",
                (category,),
            ).fetchall()
        return {r["key"]: json.loads(r["value"]) for r in rows}

    def store_fact(self, content: str, tags: list[str] = None, source: str = "") -> int:
        now = datetime.utcnow().isoformat()
        tags_str = json.dumps(tags or [])
        conn = self._conn()
        cur = conn.execute(
            "INSERT INTO facts (content, tags, source, created_at) VALUES (?,?,?,?)",
            (content, tags_str, source, now),
        )
        conn.commit()
        return cur.lastrowid

    def search_facts(self, query: str, limit: int = 10) -> list[dict]:
        conn = self._conn()
        rows = conn.execute(
            "SELECT * FROM facts WHERE content LIKE ? ORDER BY created_at DESC LIMIT ?",
            (f"%{query}%", limit),
        ).fetchall()
        return [dict(r) for r in rows]

    def store_snippet(self, title: str, language: str, code: str,
                      description: str = "", tags: list[str] = None) -> int:
        now = datetime.utcnow().isoformat()
        tags_str = json.dumps(tags or [])
        conn = self._conn()
        cur = conn.execute(
            "INSERT INTO code_snippets (title, language, code, description, tags, created_at) VALUES (?,?,?,?,?,?)",
            (title, language, code, description, tags_str, now),
        )
        conn.commit()
        return cur.lastrowid

    def search_snippets(self, query: str, language: str = None, limit: int = 10) -> list[dict]:
        conn = self._conn()
        if language:
            rows = conn.execute(
                "SELECT * FROM code_snippets WHERE language=? AND (title LIKE ? OR description LIKE ?) LIMIT ?",
                (language, f"%{query}%", f"%{query}%", limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM code_snippets WHERE title LIKE ? OR description LIKE ? LIMIT ?",
                (f"%{query}%", f"%{query}%", limit),
            ).fetchall()
        return [dict(r) for r in rows]


class MemorySystem:
    """Unified memory interface combining short-term and long-term memory."""

    def __init__(self):
        self.short_term = ShortTermMemory()
        self.long_term = LongTermMemory()
        self._task_contexts: dict[str, ShortTermMemory] = {}

    def get_task_context(self, task_id: str) -> ShortTermMemory:
        if task_id not in self._task_contexts:
            self._task_contexts[task_id] = ShortTermMemory()
        return self._task_contexts[task_id]

    def clear_task_context(self, task_id: str) -> None:
        if task_id in self._task_contexts:
            self._task_contexts[task_id].clear()
            del self._task_contexts[task_id]

    def save_task_result(self, task_id: str, result: Any) -> None:
        self.long_term.store("task_results", task_id, result, task_id=task_id)

    def load_task_result(self, task_id: str) -> Any:
        return self.long_term.retrieve("task_results", task_id, task_id=task_id)


# Global memory instance
memory = MemorySystem()
