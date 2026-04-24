"""
Chat API — conversation-driven task creation and project modification.

POST /api/chat
  Body: { message, project_id? }
  Returns: ConversationPlan + created task info

GET /api/chat/{project_id}/history
  Returns the conversation history for a project
"""

import os
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

from agents.conversation_controller import conversation_controller, ConversationPlan
from config import settings
from core.agent_loop import agent_loop
from core.task_queue import Task, task_queue
from tools.filesystem import FileSystemTool
from utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/chat", tags=["chat"])


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    message: str
    project_id: Optional[str] = None


class ActionItemResponse(BaseModel):
    type: str
    target: str = ""
    goal: str = ""


class ChatResponse(BaseModel):
    intent: str
    project_id: str
    summary: str
    task_id: Optional[str] = None
    task_title: str = ""
    actions: List[ActionItemResponse] = []
    affected_files: List[str] = []
    message: str = ""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_workspace_files(path: str = ".") -> List[str]:
    """Walk the workspace directory and return relative file paths."""
    try:
        fs = FileSystemTool(base_dir=settings.WORKSPACE_DIR)
        results: List[str] = []
        base = os.path.abspath(settings.WORKSPACE_DIR)
        for root, dirs, files in os.walk(base):
            dirs[:] = [d for d in dirs if not d.startswith(".") and d != "__pycache__"]
            for fname in files:
                full = os.path.join(root, fname)
                results.append(os.path.relpath(full, base))
        return results
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest, background_tasks: BackgroundTasks) -> ChatResponse:
    """
    Process a chat message and either create a new task or queue an incremental
    modification to an existing project.
    """
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    workspace_files = _get_workspace_files()

    try:
        plan: ConversationPlan = await conversation_controller.process_message(
            message=request.message,
            project_id=request.project_id,
            workspace_files=workspace_files,
        )
    except Exception as exc:
        logger.error(f"ConversationController error: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Planning failed: {exc}")

    # Create and enqueue a task
    task: Optional[Task] = None
    if plan.intent in ("new_project", "modification") and plan.task_description:
        task = Task(
            title=plan.task_title or request.message[:60],
            description=plan.task_description,
            metadata={
                "project_id": plan.project_id,
                "intent": plan.intent,
                "affected_files": plan.affected_files,
                "actions": [
                    {"type": a.type, "target": a.target, "goal": a.goal}
                    for a in plan.actions
                ],
                "conversation_summary": plan.summary,
            },
        )
        task_queue.add_task(task)
        background_tasks.add_task(agent_loop.run_task, task)
        conversation_controller.update_last_task(plan.project_id, task.id)
        logger.info(
            f"Chat created task {task.id} for project {plan.project_id} "
            f"(intent={plan.intent})"
        )

    return ChatResponse(
        intent=plan.intent,
        project_id=plan.project_id,
        summary=plan.summary,
        task_id=task.id if task else None,
        task_title=plan.task_title,
        actions=[
            ActionItemResponse(type=a.type, target=a.target, goal=a.goal)
            for a in plan.actions
        ],
        affected_files=plan.affected_files,
        message=plan.summary,
    )


@router.get("/{project_id}/history")
async def get_project_history(project_id: str) -> Dict[str, Any]:
    """Return the conversation history for a project."""
    state = conversation_controller.get_project(project_id)
    if not state:
        raise HTTPException(status_code=404, detail="Project not found")
    return {
        "project_id": project_id,
        "name": state.name,
        "description": state.description,
        "tech_stack": state.tech_stack,
        "files": state.files,
        "last_task_id": state.last_task_id,
        "history": state.conversation_history,
    }


@router.get("")
async def list_projects() -> List[Dict[str, Any]]:
    """List all active conversation projects."""
    projects = []
    for pid, state in conversation_controller._projects.items():
        projects.append({
            "project_id": pid,
            "description": state.description[:80] if state.description else "",
            "tech_stack": state.tech_stack,
            "file_count": len(state.files),
            "last_task_id": state.last_task_id,
            "turns": len(state.conversation_history),
        })
    return projects
