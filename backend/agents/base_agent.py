"""
XandriX Engineer - Base Agent
"""
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Optional

from backend.core.llm_client import LLMClient, LLMMessage, llm
from backend.core.logger import XandriXLogger, get_logger
from backend.core.memory_system import MemorySystem, memory
from backend.models.schemas import AgentActivity, AgentStatus, AgentType, Task, TaskStep, TaskStatus
from backend.tools.filesystem import FileSystem
from backend.tools.terminal import Terminal


class BaseAgent(ABC):
    """Abstract base class for all XandriX Engineer agents."""

    agent_type: AgentType = AgentType.CODER

    def __init__(
        self,
        llm_client: LLMClient = None,
        memory_system: MemorySystem = None,
    ):
        self.llm = llm_client or llm
        self.memory = memory_system or memory
        self.logger = get_logger(f"agent.{self.agent_type.value}")
        self.activity: Optional[AgentActivity] = None

    def _create_activity(self, task_id: str) -> AgentActivity:
        self.activity = AgentActivity(
            task_id=task_id,
            agent_type=self.agent_type,
            status=AgentStatus.WORKING,
            started_at=datetime.utcnow(),
        )
        return self.activity

    def _add_thought(self, thought: str) -> None:
        if self.activity:
            self.activity.thoughts.append(thought)
        self.logger.debug(f"Thought: {thought}")

    def _add_action(self, action: str, result: Any = None) -> None:
        if self.activity:
            self.activity.actions.append({
                "action": action,
                "result": str(result)[:500] if result else None,
                "timestamp": datetime.utcnow().isoformat(),
            })

    def _set_current_action(self, action: str) -> None:
        if self.activity:
            self.activity.current_action = action
        self.logger.agent(self.agent_type.value, action)

    @abstractmethod
    async def execute(self, task: Task, step: TaskStep) -> TaskStep:
        """Execute a task step and return the updated step."""
        ...

    async def _think(self, prompt: str, system: str, context: dict = None) -> str:
        """Use LLM to reason about a problem."""
        messages = [LLMMessage("user", prompt)]
        if context:
            context_str = "\n".join(f"{k}: {v}" for k, v in context.items())
            messages.insert(0, LLMMessage("system", f"Context:\n{context_str}"))
        response = await self.llm.chat(messages=messages, system=system)
        return response.content

    def _get_task_fs(self, task: Task) -> FileSystem:
        """Get a FileSystem scoped to the task's project directory."""
        from pathlib import Path
        project_dir = Path(task.project_dir) if task.project_dir else Path.cwd()
        return FileSystem(base_dir=project_dir)

    def _get_task_terminal(self, task: Task) -> Terminal:
        """Get a Terminal scoped to the task's project directory."""
        from pathlib import Path
        project_dir = Path(task.project_dir) if task.project_dir else Path.cwd()
        return Terminal(working_dir=project_dir)
