"""
XandriX Engineer - FastAPI Application
"""
import asyncio
import json
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.config import API_HOST, API_PORT, CORS_ORIGINS
from backend.core.agent_loop import agent_loop
from backend.core.logger import broadcaster, get_logger, system_logger
from backend.core.task_store import task_store
from backend.models.schemas import (
    ChatMessage, CreateTaskRequest, Task, TaskControlRequest, TaskStatus,
)

logger = get_logger("api")

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self._connections: dict[str, list[WebSocket]] = {}
        self._global: list[WebSocket] = []

    async def connect(self, ws: WebSocket, task_id: str = None) -> None:
        await ws.accept()
        if task_id:
            self._connections.setdefault(task_id, []).append(ws)
        else:
            self._global.append(ws)

    def disconnect(self, ws: WebSocket, task_id: str = None) -> None:
        if task_id and task_id in self._connections:
            self._connections[task_id] = [w for w in self._connections[task_id] if w != ws]
        elif ws in self._global:
            self._global.remove(ws)

    async def broadcast(self, message: dict, task_id: str = None) -> None:
        targets = list(self._global)
        if task_id and task_id in self._connections:
            targets.extend(self._connections[task_id])
        dead = []
        for ws in targets:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)
            if task_id:
                self.disconnect(ws, task_id)


ws_manager = ConnectionManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Wire log broadcaster to WebSocket manager
    async def log_to_ws(entry: dict):
        await ws_manager.broadcast({"type": "log", "data": entry}, entry.get("task_id"))

    broadcaster.subscribe(log_to_ws)
    system_logger.info("XandriX Engineer API started")
    yield
    system_logger.info("XandriX Engineer API shutting down")


app = FastAPI(
    title="XandriX Engineer API",
    description="Autonomous AI Software Engineer",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Task Endpoints ────────────────────────────────────────────────────────────

@app.post("/api/tasks", response_model=Task)
async def create_task(req: CreateTaskRequest):
    """Create and start a new task."""
    task = Task(
        title=req.title,
        description=req.description,
        language=req.language,
        metadata=req.metadata,
    )
    task_store.save(task)

    # Start the agent loop
    task = await agent_loop.start(task)

    # Register WS callback for live updates
    async def task_event_callback(event: str, data: dict):
        await ws_manager.broadcast(
            {"type": "task_event", "event": event, "task_id": task.id, "data": data},
            task_id=task.id,
        )

    agent_loop.register_callback(task.id, task_event_callback)

    return task


@app.get("/api/tasks", response_model=list[Task])
async def list_tasks():
    """List all tasks."""
    return task_store.list_all()


@app.get("/api/tasks/{task_id}", response_model=Task)
async def get_task(task_id: str):
    """Get a specific task by ID."""
    task = task_store.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@app.delete("/api/tasks/{task_id}")
async def delete_task(task_id: str):
    """Delete a task."""
    task = task_store.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if agent_loop.is_running(task_id):
        await agent_loop.stop(task_id)
    task_store.delete(task_id)
    return {"message": "Task deleted"}


@app.post("/api/tasks/{task_id}/control")
async def control_task(task_id: str, req: TaskControlRequest):
    """Control task execution: start, stop, pause, resume, retry."""
    task = task_store.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if req.action == "stop":
        await agent_loop.stop(task_id)
    elif req.action == "pause":
        await agent_loop.pause(task_id)
    elif req.action == "resume":
        await agent_loop.resume(task_id)
    elif req.action == "retry":
        await agent_loop.stop(task_id)
        task.status = TaskStatus.PENDING
        task.current_step = 0
        task.steps = []
        task.error_count = 0
        task.iterations = 0
        task_store.save(task)
        task = await agent_loop.start(task)
    else:
        raise HTTPException(status_code=400, detail=f"Unknown action: {req.action}")

    return {"message": f"Action '{req.action}' applied to task {task_id}"}


# ─── File Endpoints ─────────────────────────────────────────────────────────

@app.get("/api/tasks/{task_id}/files")
async def get_task_files(task_id: str):
    """Get file tree for a task's project directory."""
    task = task_store.get(task_id)
    if not task or not task.project_dir:
        raise HTTPException(status_code=404, detail="Task or project not found")

    from backend.tools.filesystem import FileSystem
    fs = FileSystem(Path(task.project_dir))
    tree = fs.tree(".")
    return tree


@app.get("/api/tasks/{task_id}/files/content")
async def get_file_content(task_id: str, path: str):
    """Read a file from the task's project directory."""
    task = task_store.get(task_id)
    if not task or not task.project_dir:
        raise HTTPException(status_code=404, detail="Task not found")

    from backend.tools.filesystem import FileSystem
    fs = FileSystem(Path(task.project_dir))
    try:
        content = fs.read(path)
        language = fs.detect_language(path)
        return {"path": path, "content": content, "language": language}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found")


# ─── System Endpoints ─────────────────────────────────────────────────────────

@app.get("/api/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "ok",
        "running_tasks": len(agent_loop.get_running_tasks()),
        "version": "1.0.0",
    }


@app.get("/api/system/info")
async def system_info():
    """Get system configuration info."""
    from backend.config import LLM_MODEL, LLM_PROVIDER, SUPPORTED_LANGUAGES
    return {
        "llm_provider": LLM_PROVIDER,
        "llm_model": LLM_MODEL,
        "supported_languages": list(SUPPORTED_LANGUAGES.keys()),
        "running_tasks": agent_loop.get_running_tasks(),
    }


# ─── Chat Endpoint ─────────────────────────────────────────────────────────

@app.post("/api/chat")
async def chat(message: ChatMessage):
    """Chat with the agent about a task."""
    from backend.core.llm_client import LLMMessage, llm

    context = ""
    if message.task_id:
        task = task_store.get(message.task_id)
        if task:
            context = f"Current task: {task.title}\nStatus: {task.status.value}\nSteps completed: {task.current_step}/{len(task.steps)}"

    response = await llm.chat(
        messages=[LLMMessage("user", message.content)],
        system=f"You are XandriX Engineer, an autonomous AI software engineer. {context}",
    )
    return {"response": response.content, "task_id": message.task_id}


# ─── WebSocket ─────────────────────────────────────────────────────────────

@app.websocket("/ws")
async def websocket_global(ws: WebSocket):
    """Global WebSocket for all updates."""
    await ws_manager.connect(ws)
    try:
        while True:
            data = await ws.receive_text()
            # Handle pings
            if data == "ping":
                await ws.send_text("pong")
    except WebSocketDisconnect:
        ws_manager.disconnect(ws)


@app.websocket("/ws/{task_id}")
async def websocket_task(ws: WebSocket, task_id: str):
    """Task-specific WebSocket for targeted updates."""
    await ws_manager.connect(ws, task_id=task_id)
    try:
        # Send current task state immediately on connect
        task = task_store.get(task_id)
        if task:
            await ws.send_json({"type": "task_state", "data": task.model_dump(mode="json")})
        while True:
            data = await ws.receive_text()
            if data == "ping":
                await ws.send_text("pong")
    except WebSocketDisconnect:
        ws_manager.disconnect(ws, task_id=task_id)
