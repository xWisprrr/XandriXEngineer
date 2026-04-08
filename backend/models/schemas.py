"""
XandriX Engineer - Data Models
"""
import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    PENDING = "pending"
    PLANNING = "planning"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentType(str, Enum):
    PLANNER = "planner"
    CODER = "coder"
    TESTER = "tester"
    DEBUGGER = "debugger"
    DEVOPS = "devops"
    REVIEWER = "reviewer"


class AgentStatus(str, Enum):
    IDLE = "idle"
    WORKING = "working"
    WAITING = "waiting"
    DONE = "done"
    ERROR = "error"


class ExecutionStatus(str, Enum):
    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"
    RUNNING = "running"


class TaskStep(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    description: str
    agent: AgentType
    status: TaskStatus = TaskStatus.PENDING
    output: Optional[str] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    dependencies: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class Task(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    description: str
    status: TaskStatus = TaskStatus.PENDING
    steps: list[TaskStep] = Field(default_factory=list)
    current_step: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    project_dir: Optional[str] = None
    language: Optional[str] = None
    context: dict[str, Any] = Field(default_factory=dict)
    iterations: int = 0
    error_count: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentActivity(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    task_id: str
    agent_type: AgentType
    status: AgentStatus = AgentStatus.IDLE
    current_action: Optional[str] = None
    started_at: Optional[datetime] = None
    thoughts: list[str] = Field(default_factory=list)
    actions: list[dict[str, Any]] = Field(default_factory=list)


class ExecutionResult(BaseModel):
    status: ExecutionStatus
    stdout: str = ""
    stderr: str = ""
    return_code: int = 0
    duration: float = 0.0
    language: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class LogEntry(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    task_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    level: str = "info"  # info | warning | error | debug | success
    source: str = "system"  # system | agent_type | tool_name
    message: str
    data: Optional[dict[str, Any]] = None


class FileNode(BaseModel):
    name: str
    path: str
    is_dir: bool
    size: Optional[int] = None
    modified: Optional[datetime] = None
    children: Optional[list["FileNode"]] = None
    language: Optional[str] = None


class CreateTaskRequest(BaseModel):
    title: str
    description: str
    language: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class TaskControlRequest(BaseModel):
    action: str  # start | stop | pause | resume | retry


class ChatMessage(BaseModel):
    role: str  # user | assistant
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    task_id: Optional[str] = None


FileNode.model_rebuild()
