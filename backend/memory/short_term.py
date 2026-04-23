import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class Message:
    role: str
    content: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    task_id: Optional[str] = None


class ShortTermMemory:
    def __init__(self) -> None:
        self._store: Dict[str, Dict[str, Any]] = {}

    def add(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        expiry = time.time() + ttl_seconds if ttl_seconds else None
        self._store[key] = {"value": value, "expiry": expiry}

    def get(self, key: str) -> Optional[Any]:
        entry = self._store.get(key)
        if not entry:
            return None
        if entry["expiry"] and time.time() > entry["expiry"]:
            del self._store[key]
            return None
        return entry["value"]

    def clear(self, task_id: Optional[str] = None) -> None:
        if task_id:
            keys_to_delete = [k for k in self._store if k.startswith(f"{task_id}:")]
            for k in keys_to_delete:
                del self._store[k]
        else:
            self._store.clear()

    def all_keys(self) -> List[str]:
        return list(self._store.keys())


class ConversationMemory:
    def __init__(self, max_messages: int = 100) -> None:
        self._messages: Dict[str, List[Message]] = {}
        self.max_messages = max_messages

    def add_message(self, role: str, content: str, task_id: str = "default") -> None:
        if task_id not in self._messages:
            self._messages[task_id] = []
        msg = Message(role=role, content=content, task_id=task_id)
        self._messages[task_id].append(msg)
        # Trim if over limit
        if len(self._messages[task_id]) > self.max_messages:
            self._messages[task_id] = self._messages[task_id][-self.max_messages:]

    def get_messages(self, task_id: str = "default", limit: int = 50) -> List[Message]:
        messages = self._messages.get(task_id, [])
        return messages[-limit:]

    def get_messages_as_dicts(self, task_id: str = "default", limit: int = 50) -> List[Dict[str, str]]:
        return [{"role": m.role, "content": m.content} for m in self.get_messages(task_id, limit)]

    def clear(self, task_id: Optional[str] = None) -> None:
        if task_id:
            self._messages.pop(task_id, None)
        else:
            self._messages.clear()


short_term_memory = ShortTermMemory()
conversation_memory = ConversationMemory()
