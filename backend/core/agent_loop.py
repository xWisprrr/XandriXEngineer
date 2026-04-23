import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Set

from config import settings
from core.event_bus import EventType, event_bus
from core.task_queue import Task, TaskQueue, TaskStatus, task_queue
from utils.logger import get_logger

logger = get_logger(__name__)


class AgentLoop:
    def __init__(self, queue: TaskQueue | None = None) -> None:
        self._queue = queue or task_queue
        self._running = False
        self._active_tasks: Dict[str, asyncio.Task] = {}
        self._paused_tasks: Set[str] = set()
        self._cancelled_tasks: Set[str] = set()
        self._loop_task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        self._running = True
        logger.info("AgentLoop started")
        self._loop_task = asyncio.create_task(self._main_loop())

    async def stop(self) -> None:
        self._running = False
        for task_id, asyncio_task in list(self._active_tasks.items()):
            asyncio_task.cancel()
            try:
                await asyncio_task
            except asyncio.CancelledError:
                pass
        self._active_tasks.clear()
        if self._loop_task and not self._loop_task.done():
            self._loop_task.cancel()
            try:
                await self._loop_task
            except asyncio.CancelledError:
                pass
        logger.info("AgentLoop stopped")

    async def _main_loop(self) -> None:
        while self._running:
            active_count = len([t for t in self._active_tasks.values() if not t.done()])
            if active_count < settings.MAX_CONCURRENT_TASKS:
                task = self._queue.get_next_pending()
                if task:
                    asyncio_task = asyncio.create_task(self._execute_task(task))
                    self._active_tasks[task.id] = asyncio_task
            # Clean up finished tasks
            done_ids = [tid for tid, t in self._active_tasks.items() if t.done()]
            for tid in done_ids:
                del self._active_tasks[tid]
            await asyncio.sleep(1.0)

    async def _execute_task(self, task: Task) -> None:
        from agents.orchestrator import AgentOrchestrator
        orchestrator = AgentOrchestrator()

        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now(timezone.utc)
        self._queue.update_task(task.id, status=TaskStatus.RUNNING, started_at=task.started_at)

        await event_bus.publish(EventType.TASK_STARTED, task.to_dict())
        task.logs.append(f"[{datetime.now(timezone.utc).isoformat()}] Task started: {task.title}")

        try:
            result = await asyncio.wait_for(
                orchestrator.execute_task(task),
                timeout=settings.TASK_TIMEOUT,
            )
            if task.id not in self._cancelled_tasks:
                task.status = TaskStatus.COMPLETED
                task.result = str(result) if result else "Task completed successfully."
                task.completed_at = datetime.now(timezone.utc)
                task.logs.append(f"[{datetime.now(timezone.utc).isoformat()}] Task completed.")
                await event_bus.publish(EventType.TASK_COMPLETED, task.to_dict())
                logger.info(f"Task {task.id} completed.")
        except asyncio.CancelledError:
            task.status = TaskStatus.CANCELLED
            task.logs.append(f"[{datetime.now(timezone.utc).isoformat()}] Task cancelled.")
            await event_bus.publish(EventType.TASK_FAILED, task.to_dict())
        except asyncio.TimeoutError:
            task.status = TaskStatus.FAILED
            task.error = f"Task timed out after {settings.TASK_TIMEOUT}s."
            task.logs.append(f"[{datetime.now(timezone.utc).isoformat()}] Task timed out.")
            await event_bus.publish(EventType.TASK_FAILED, task.to_dict())
            logger.error(f"Task {task.id} timed out.")
        except Exception as exc:
            task.status = TaskStatus.FAILED
            task.error = str(exc)
            task.logs.append(f"[{datetime.now(timezone.utc).isoformat()}] Task failed: {exc}")
            await event_bus.publish(EventType.TASK_FAILED, task.to_dict())
            logger.error(f"Task {task.id} failed: {exc}", exc_info=True)

        self._queue.update_task(
            task.id,
            status=task.status,
            result=task.result,
            error=task.error,
            completed_at=task.completed_at,
        )

    async def run_task(self, task: Task) -> None:
        if task.id not in self._active_tasks or self._active_tasks[task.id].done():
            asyncio_task = asyncio.create_task(self._execute_task(task))
            self._active_tasks[task.id] = asyncio_task

    async def stop_task(self, task_id: str) -> bool:
        self._cancelled_tasks.add(task_id)
        if task_id in self._active_tasks:
            self._active_tasks[task_id].cancel()
            return True
        return self._queue.cancel_task(task_id)

    async def pause_task(self, task_id: str) -> bool:
        self._paused_tasks.add(task_id)
        return self._queue.pause_task(task_id)

    async def resume_task(self, task_id: str) -> bool:
        self._paused_tasks.discard(task_id)
        return self._queue.resume_task(task_id)


agent_loop = AgentLoop()
