from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

from core.agent_loop import agent_loop
from core.task_queue import Task, TaskStatus, task_queue
from utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/tasks", tags=["tasks"])


class CreateTaskRequest(BaseModel):
    title: str
    description: str
    priority: int = 5
    metadata: Dict[str, Any] = {}


class TaskResponse(BaseModel):
    id: str
    title: str
    description: str
    status: str
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    steps: List[Dict[str, Any]] = []
    current_step: int = 0
    error: Optional[str] = None
    result: Optional[str] = None
    priority: int = 5
    logs: List[str] = []


def _task_to_response(task: Task) -> Dict[str, Any]:
    return task.to_dict()


@router.post("", response_model=Dict[str, Any])
async def create_task(request: CreateTaskRequest, background_tasks: BackgroundTasks):
    task = Task(
        title=request.title,
        description=request.description,
        priority=request.priority,
        metadata=request.metadata,
    )
    task_queue.add_task(task)
    # Schedule immediate execution
    background_tasks.add_task(agent_loop.run_task, task)
    logger.info(f"Created task: {task.id} - {task.title}")
    return _task_to_response(task)


@router.get("", response_model=List[Dict[str, Any]])
async def list_tasks():
    return [_task_to_response(t) for t in task_queue.list_tasks()]


@router.get("/{task_id}", response_model=Dict[str, Any])
async def get_task(task_id: str):
    task = task_queue.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return _task_to_response(task)


@router.delete("/{task_id}")
async def delete_task(task_id: str):
    await agent_loop.stop_task(task_id)
    if not task_queue.delete_task(task_id):
        raise HTTPException(status_code=404, detail="Task not found")
    return {"message": "Task deleted", "id": task_id}


@router.post("/{task_id}/pause")
async def pause_task(task_id: str):
    task = task_queue.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    success = await agent_loop.pause_task(task_id)
    if not success:
        raise HTTPException(status_code=400, detail="Task cannot be paused in its current state")
    return {"message": "Task paused", "id": task_id}


@router.post("/{task_id}/resume")
async def resume_task(task_id: str):
    task = task_queue.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    success = await agent_loop.resume_task(task_id)
    if not success:
        raise HTTPException(status_code=400, detail="Task cannot be resumed in its current state")
    return {"message": "Task resumed", "id": task_id}


@router.post("/{task_id}/stop")
async def stop_task(task_id: str):
    task = task_queue.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    await agent_loop.stop_task(task_id)
    return {"message": "Task stopped", "id": task_id}


@router.get("/{task_id}/logs")
async def get_task_logs(task_id: str, limit: int = 100):
    task = task_queue.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"task_id": task_id, "logs": task.logs[-limit:]}
