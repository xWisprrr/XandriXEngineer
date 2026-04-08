import asyncio
from enum import Enum
from typing import Any, Callable, Dict, List
from utils.logger import get_logger

logger = get_logger(__name__)


class EventType(str, Enum):
    TASK_STARTED = "task_started"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    STEP_STARTED = "step_started"
    STEP_COMPLETED = "step_completed"
    AGENT_THINKING = "agent_thinking"
    CODE_GENERATED = "code_generated"
    EXECUTION_RESULT = "execution_result"
    LOG_MESSAGE = "log_message"
    TASK_PAUSED = "task_paused"
    TASK_RESUMED = "task_resumed"


class EventBus:
    def __init__(self) -> None:
        self._handlers: Dict[str, List[Callable]] = {}

    def subscribe(self, event_type: EventType | str, handler: Callable) -> None:
        key = event_type.value if isinstance(event_type, EventType) else event_type
        self._handlers.setdefault(key, [])
        if handler not in self._handlers[key]:
            self._handlers[key].append(handler)

    def unsubscribe(self, event_type: EventType | str, handler: Callable) -> None:
        key = event_type.value if isinstance(event_type, EventType) else event_type
        handlers = self._handlers.get(key, [])
        if handler in handlers:
            handlers.remove(handler)

    async def publish(self, event_type: EventType | str, data: Any = None) -> None:
        key = event_type.value if isinstance(event_type, EventType) else event_type
        handlers = self._handlers.get(key, [])
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event_type, data)
                else:
                    handler(event_type, data)
            except Exception as exc:
                logger.error(f"Error in event handler for {key}: {exc}")

    def clear(self) -> None:
        self._handlers.clear()


event_bus = EventBus()
