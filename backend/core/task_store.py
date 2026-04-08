"""
XandriX Engineer - Task Store
Persistent in-memory task registry backed by SQLite.
"""
import json
import sqlite3
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional

from backend.config import TASKS_DB_PATH
from backend.models.schemas import Task, TaskStatus


class TaskStore:
    """Thread-safe task storage with SQLite persistence."""

    def __init__(self, db_path: Path = TASKS_DB_PATH):
        self._db_path = db_path
        self._local = threading.local()
        self._cache: dict[str, Task] = {}
        self._lock = threading.Lock()
        self._init_db()

    def _conn(self) -> sqlite3.Connection:
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._local.conn = sqlite3.connect(str(self._db_path), check_same_thread=False)
            self._local.conn.row_factory = sqlite3.Row
        return self._local.conn

    def _init_db(self) -> None:
        conn = sqlite3.connect(str(self._db_path))
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                data TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_created ON tasks(created_at)")
        conn.commit()
        conn.close()

        # Load existing tasks into cache
        conn = sqlite3.connect(str(self._db_path))
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT id, data FROM tasks ORDER BY created_at DESC LIMIT 100").fetchall()
        for row in rows:
            try:
                task = Task.model_validate_json(row["data"])
                self._cache[task.id] = task
            except Exception:
                pass
        conn.close()

    def save(self, task: Task) -> None:
        """Save or update a task."""
        now = datetime.utcnow().isoformat()
        serialized = task.model_dump_json()
        with self._lock:
            self._cache[task.id] = task
        conn = self._conn()
        conn.execute(
            """INSERT INTO tasks (id, data, created_at, updated_at) VALUES (?, ?, ?, ?)
               ON CONFLICT(id) DO UPDATE SET data=excluded.data, updated_at=excluded.updated_at""",
            (task.id, serialized, now, now),
        )
        conn.commit()

    def get(self, task_id: str) -> Optional[Task]:
        """Get a task by ID."""
        with self._lock:
            if task_id in self._cache:
                return self._cache[task_id]
        conn = self._conn()
        row = conn.execute("SELECT data FROM tasks WHERE id=?", (task_id,)).fetchone()
        if row:
            task = Task.model_validate_json(row["data"])
            with self._lock:
                self._cache[task.id] = task
            return task
        return None

    def list_all(self, limit: int = 50) -> list[Task]:
        """List all tasks, newest first."""
        conn = self._conn()
        rows = conn.execute(
            "SELECT data FROM tasks ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
        tasks = []
        for row in rows:
            try:
                task = Task.model_validate_json(row["data"])
                tasks.append(task)
            except Exception:
                pass
        return tasks

    def delete(self, task_id: str) -> None:
        """Delete a task."""
        with self._lock:
            self._cache.pop(task_id, None)
        conn = self._conn()
        conn.execute("DELETE FROM tasks WHERE id=?", (task_id,))
        conn.commit()

    def update_status(self, task_id: str, status: TaskStatus) -> None:
        """Quick status update."""
        task = self.get(task_id)
        if task:
            task.status = status
            self.save(task)

    def list_by_status(self, status: TaskStatus) -> list[Task]:
        """Get tasks by status from cache."""
        with self._lock:
            return [t for t in self._cache.values() if t.status == status]


# Global task store instance
task_store = TaskStore()
