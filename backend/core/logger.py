"""
XandriX Engineer - Structured Logger
"""
import asyncio
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Optional

from backend.config import LOGS_DIR


class LogBroadcaster:
    """Broadcasts log entries to WebSocket subscribers."""

    def __init__(self):
        self._subscribers: dict[str, list[Callable]] = {}  # task_id -> callbacks
        self._global_subscribers: list[Callable] = []

    def subscribe(self, callback: Callable, task_id: Optional[str] = None) -> None:
        if task_id:
            self._subscribers.setdefault(task_id, []).append(callback)
        else:
            self._global_subscribers.append(callback)

    def unsubscribe(self, callback: Callable, task_id: Optional[str] = None) -> None:
        if task_id and task_id in self._subscribers:
            self._subscribers[task_id] = [c for c in self._subscribers[task_id] if c != callback]
        elif callback in self._global_subscribers:
            self._global_subscribers.remove(callback)

    async def broadcast(self, entry: dict) -> None:
        task_id = entry.get("task_id")
        callbacks = list(self._global_subscribers)
        if task_id and task_id in self._subscribers:
            callbacks.extend(self._subscribers[task_id])
        for cb in callbacks:
            try:
                if asyncio.iscoroutinefunction(cb):
                    await cb(entry)
                else:
                    cb(entry)
            except Exception:
                pass


broadcaster = LogBroadcaster()


class XandriXLogger:
    """Structured logger with file output and WebSocket broadcasting."""

    def __init__(self, name: str, task_id: Optional[str] = None):
        self.name = name
        self.task_id = task_id
        self._file_logger = self._setup_file_logger(name)

    def _setup_file_logger(self, name: str) -> logging.Logger:
        logger = logging.getLogger(f"xandrix.{name}")
        if not logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            handler.setFormatter(logging.Formatter(
                "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
            ))
            logger.addHandler(handler)

            log_file = LOGS_DIR / f"{name}.log"
            file_handler = logging.FileHandler(str(log_file))
            file_handler.setFormatter(logging.Formatter(
                "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
            ))
            logger.addHandler(file_handler)
            logger.setLevel(logging.DEBUG)
        return logger

    def _emit(self, level: str, message: str, data: Any = None, source: str = None) -> None:
        entry = {
            "id": f"{datetime.utcnow().timestamp()}",
            "task_id": self.task_id,
            "timestamp": datetime.utcnow().isoformat(),
            "level": level,
            "source": source or self.name,
            "message": message,
            "data": data,
        }

        log_fn = getattr(self._file_logger, level if level != "success" else "info")
        log_fn(message)

        asyncio.get_event_loop().call_soon_threadsafe(
            lambda: asyncio.ensure_future(broadcaster.broadcast(entry))
        ) if asyncio.get_event_loop().is_running() else None

    def info(self, message: str, data: Any = None) -> None:
        self._emit("info", message, data)

    def success(self, message: str, data: Any = None) -> None:
        self._emit("success", message, data)

    def warning(self, message: str, data: Any = None) -> None:
        self._emit("warning", message, data)

    def error(self, message: str, data: Any = None) -> None:
        self._emit("error", message, data)

    def debug(self, message: str, data: Any = None) -> None:
        self._emit("debug", message, data)

    def agent(self, agent_type: str, action: str, data: Any = None) -> None:
        self._emit("info", f"[{agent_type.upper()}] {action}", data, source=agent_type)

    def tool(self, tool_name: str, action: str, data: Any = None) -> None:
        self._emit("debug", f"[TOOL:{tool_name}] {action}", data, source=f"tool.{tool_name}")

    def with_task(self, task_id: str) -> "XandriXLogger":
        child = XandriXLogger(self.name, task_id=task_id)
        return child


def get_logger(name: str, task_id: Optional[str] = None) -> XandriXLogger:
    return XandriXLogger(name, task_id=task_id)


system_logger = get_logger("system")
