"""
XandriX Engineer - Main Agent Loop
Orchestrates multi-agent execution with retry, error recovery, and self-critique.
"""
import asyncio
import uuid
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

from backend.agents.coder_agent import CoderAgent
from backend.agents.debugger_agent import DebuggerAgent
from backend.agents.devops_agent import DevOpsAgent
from backend.agents.planner_agent import PlannerAgent
from backend.agents.tester_agent import TesterAgent
from backend.config import AGENT_TIMEOUT, MAX_ITERATIONS, MAX_RETRIES, PROJECTS_DIR
from backend.core.llm_client import LLMMessage, llm
from backend.core.logger import get_logger
from backend.core.memory_system import memory
from backend.core.task_planner import TaskPlanner
from backend.core.task_store import task_store
from backend.models.schemas import AgentType, Task, TaskStatus
from backend.tools.git_tool import GitTool
from backend.tools.terminal import Terminal

logger = get_logger("agent_loop")


class AgentLoop:
    """
    Central orchestration loop that runs tasks through the multi-agent pipeline.
    Handles planning, execution, debugging, retries, and checkpointing.
    """

    def __init__(self):
        self.planner = TaskPlanner()
        self.agents = {
            AgentType.PLANNER: PlannerAgent(),
            AgentType.CODER: CoderAgent(),
            AgentType.TESTER: TesterAgent(),
            AgentType.DEBUGGER: DebuggerAgent(),
            AgentType.DEVOPS: DevOpsAgent(),
        }
        self._running_tasks: dict[str, asyncio.Task] = {}
        self._stop_flags: dict[str, bool] = {}
        self._pause_flags: dict[str, bool] = {}
        self._callbacks: dict[str, list[Callable]] = {}

    def register_callback(self, task_id: str, callback: Callable) -> None:
        """Register a callback for task events."""
        self._callbacks.setdefault(task_id, []).append(callback)

    async def _emit(self, task_id: str, event: str, data: dict = None) -> None:
        """Emit a task event to all registered callbacks."""
        for cb in self._callbacks.get(task_id, []):
            try:
                if asyncio.iscoroutinefunction(cb):
                    await cb(event, data or {})
                else:
                    cb(event, data or {})
            except Exception as e:
                logger.error(f"Callback error: {e}")

    async def start(self, task: Task) -> Task:
        """Start executing a task in the background."""
        logger.info(f"Starting task: {task.title}", {"task_id": task.id})

        # Create project directory
        project_dir = PROJECTS_DIR / task.id
        project_dir.mkdir(parents=True, exist_ok=True)
        task.project_dir = str(project_dir)
        task.started_at = datetime.utcnow()
        task.status = TaskStatus.PLANNING

        task_store.save(task)

        self._stop_flags[task.id] = False
        self._pause_flags[task.id] = False

        # Run in background
        coro = self._run_task_loop(task)
        asyncio_task = asyncio.create_task(coro, name=f"task-{task.id}")
        self._running_tasks[task.id] = asyncio_task

        return task

    async def stop(self, task_id: str) -> None:
        """Stop a running task."""
        self._stop_flags[task_id] = True
        if task_id in self._running_tasks:
            self._running_tasks[task_id].cancel()
        task = task_store.get(task_id)
        if task:
            task.status = TaskStatus.CANCELLED
            task_store.save(task)

    async def pause(self, task_id: str) -> None:
        """Pause a running task."""
        self._pause_flags[task_id] = True
        task_store.update_status(task_id, TaskStatus.PAUSED)

    async def resume(self, task_id: str) -> None:
        """Resume a paused task."""
        self._pause_flags[task_id] = False
        task = task_store.get(task_id)
        if task and task.status == TaskStatus.PAUSED:
            task.status = TaskStatus.RUNNING
            task_store.save(task)

    async def _run_task_loop(self, task: Task) -> None:
        """Main execution loop for a task."""
        task_logger = logger.with_task(task.id)

        try:
            # Phase 1: Planning
            task_logger.info("Planning task...")
            await self._emit(task.id, "status_changed", {"status": "planning"})
            task = await self.planner.plan(task)
            task_store.save(task)
            await self._emit(task.id, "plan_created", {"steps": len(task.steps)})

            # Initialize git
            git = GitTool(Path(task.project_dir))
            await git.init()
            if task.language:
                await git.create_gitignore(task.language)
            await git.add_and_commit("Initial project setup")

            # Phase 2: Execution
            task.status = TaskStatus.RUNNING
            task_store.save(task)
            await self._emit(task.id, "status_changed", {"status": "running"})

            consecutive_failures = 0

            while task.current_step < len(task.steps):
                # Check stop/pause flags
                if self._stop_flags.get(task.id):
                    task_logger.info("Task stopped by user")
                    task.status = TaskStatus.CANCELLED
                    break

                while self._pause_flags.get(task.id):
                    await asyncio.sleep(1)

                if task.iterations >= MAX_ITERATIONS:
                    task_logger.error(f"Max iterations ({MAX_ITERATIONS}) reached")
                    break

                step = task.steps[task.current_step]
                step_logger = get_logger(f"step.{step.agent.value}")
                step_logger.info(f"Executing step {task.current_step + 1}/{len(task.steps)}: {step.title}")
                await self._emit(task.id, "step_started", {
                    "step_id": step.id,
                    "step_index": task.current_step,
                    "title": step.title,
                    "agent": step.agent.value,
                })

                # Execute the step
                agent = self.agents[step.agent]
                step.started_at = datetime.utcnow()
                task.iterations += 1

                try:
                    step = await asyncio.wait_for(
                        agent.execute(task, step),
                        timeout=AGENT_TIMEOUT,
                    )
                except asyncio.TimeoutError:
                    step.error = f"Step timed out after {AGENT_TIMEOUT}s"
                    step.status = TaskStatus.FAILED
                    task_logger.error(f"Step timeout: {step.title}")

                step.completed_at = datetime.utcnow()
                task.steps[task.current_step] = step

                if step.status == TaskStatus.COMPLETED:
                    consecutive_failures = 0
                    task.current_step += 1
                    task_store.save(task)

                    # Commit progress
                    await git.add_and_commit(f"Step {task.current_step}: {step.title}")
                    await self._emit(task.id, "step_completed", {
                        "step_id": step.id,
                        "output": step.output,
                    })

                elif step.status == TaskStatus.FAILED:
                    consecutive_failures += 1
                    task.error_count += 1
                    task.context["last_error"] = step.error or "Unknown error"

                    await self._emit(task.id, "step_failed", {
                        "step_id": step.id,
                        "error": step.error,
                    })

                    if consecutive_failures <= MAX_RETRIES:
                        task_logger.warning(f"Step failed (attempt {consecutive_failures}/{MAX_RETRIES}), retrying...")
                        # Insert a debug step before retrying
                        if consecutive_failures >= 2:
                            debug_step = await self._insert_debug_step(task)
                            task.steps.insert(task.current_step, debug_step)
                        task_store.save(task)
                    else:
                        task_logger.error(f"Step failed after {MAX_RETRIES} retries: {step.title}")
                        # Try replanning
                        if task.error_count <= 3:
                            task_logger.info("Attempting replan...")
                            task = await self.planner.replan(task, step.error or "Repeated failures")
                            consecutive_failures = 0
                        else:
                            break

                task_store.save(task)

            # Phase 3: Completion
            if not self._stop_flags.get(task.id):
                all_complete = all(s.status == TaskStatus.COMPLETED for s in task.steps)
                if all_complete or task.current_step >= len(task.steps):
                    task.status = TaskStatus.COMPLETED
                    task_logger.success("Task completed successfully!")

                    # Final commit
                    await git.add_and_commit(f"Task complete: {task.title}")

                    # Self-critique
                    critique = await self._self_critique(task)
                    if critique:
                        task.context["critique"] = critique
                else:
                    task.status = TaskStatus.FAILED
                    task_logger.error("Task failed")

            task.completed_at = datetime.utcnow()
            task_store.save(task)
            memory.save_task_result(task.id, {
                "status": task.status.value,
                "steps_completed": task.current_step,
                "total_steps": len(task.steps),
                "iterations": task.iterations,
            })

            await self._emit(task.id, "task_finished", {
                "status": task.status.value,
                "project_dir": task.project_dir,
            })

        except asyncio.CancelledError:
            task_logger.info("Task cancelled")
            task.status = TaskStatus.CANCELLED
            task.completed_at = datetime.utcnow()
            task_store.save(task)
        except Exception as e:
            task_logger.error(f"Unexpected error in agent loop: {e}", {"error": str(e)})
            task.status = TaskStatus.FAILED
            task.completed_at = datetime.utcnow()
            task_store.save(task)
            await self._emit(task.id, "task_error", {"error": str(e)})
        finally:
            self._running_tasks.pop(task.id, None)
            self._stop_flags.pop(task.id, None)
            self._pause_flags.pop(task.id, None)

    async def _insert_debug_step(self, task: Task):
        """Create an auto-inserted debug step."""
        from backend.models.schemas import TaskStep
        return TaskStep(
            title="Auto Debug",
            description=f"Automatically debug the error: {task.context.get('last_error', 'Unknown')}",
            agent=AgentType.DEBUGGER,
        )

    async def _self_critique(self, task: Task) -> str:
        """Evaluate the quality of the completed work."""
        try:
            completed = [s for s in task.steps if s.status == TaskStatus.COMPLETED]
            summary = "\n".join(f"- {s.title}: {(s.output or '')[:200]}" for s in completed)

            response = await llm.chat(
                messages=[LLMMessage("user", f"""Task: {task.title}

Completed steps:
{summary}

Evaluate the quality of work done. Identify any gaps or improvements needed.
Be concise (3-5 points max).""")],
                system="You are a senior software engineer reviewing work quality. Be constructive and specific.",
                temperature=0.3,
            )
            return response.content
        except Exception:
            return ""

    def get_running_tasks(self) -> list[str]:
        """Get IDs of currently running tasks."""
        return list(self._running_tasks.keys())

    def is_running(self, task_id: str) -> bool:
        return task_id in self._running_tasks


# Global agent loop instance
agent_loop = AgentLoop()
