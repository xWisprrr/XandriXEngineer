import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from agents.planner import PlannerAgent, Step
from agents.coder import CoderAgent
from agents.tester import TesterAgent
from agents.debugger import DebuggerAgent
from agents.reviewer import ReviewerAgent
from core.event_bus import EventType, event_bus
from core.task_queue import Task, TaskStep
from config import settings
from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class StepResult:
    step_id: str
    success: bool
    output: str = ""
    error: Optional[str] = None
    duration: float = 0.0
    agent: str = ""


class AgentOrchestrator:
    def __init__(self) -> None:
        self.planner = PlannerAgent()
        self.coder = CoderAgent()
        self.tester = TesterAgent()
        self.debugger = DebuggerAgent()
        self.reviewer = ReviewerAgent()
        self._agents = {
            "planner": self.planner,
            "coder": self.coder,
            "tester": self.tester,
            "debugger": self.debugger,
            "reviewer": self.reviewer,
        }
        self._context: Dict[str, Any] = {}

    def get_all_agents(self) -> Dict[str, Any]:
        return {
            name: {"name": name, "status": agent.status, "current_action": agent.current_action}
            for name, agent in self._agents.items()
        }

    def route_task_to_agent(self, step: Step) -> Any:
        desc_lower = (step.description + " " + step.name).lower()

        if any(kw in desc_lower for kw in ["test", "verify", "check quality"]):
            return self.tester
        elif any(kw in desc_lower for kw in ["debug", "fix error", "analyze error"]):
            return self.debugger
        elif any(kw in desc_lower for kw in ["review", "critique"]):
            return self.reviewer
        elif any(kw in desc_lower for kw in ["generate code", "write code", "implement", "create"]):
            return self.coder
        else:
            return self.coder

    async def execute_task(self, task: Task) -> str:
        self._context = {"task_id": task.id, "task_title": task.title}
        task.logs.append(f"[INFO] Starting orchestration for: {task.title}")

        # Planning phase
        await event_bus.publish(EventType.AGENT_THINKING, {
            "agent": "planner",
            "message": f"Planning task: {task.title}",
            "task_id": task.id,
        })

        steps = await self.planner.analyze_task(task.description)
        task.logs.append(f"[INFO] Planner created {len(steps)} steps")

        # Create TaskStep objects
        task_steps: List[TaskStep] = []
        for s in steps:
            ts = TaskStep(id=s.id, name=s.name, description=s.description)
            task_steps.append(ts)
        task.steps = task_steps

        # Execution phase
        results: List[str] = []
        failed = False

        for i, (step, task_step) in enumerate(zip(steps, task_steps)):
            if task.status.value in ("cancelled", "paused"):
                break

            task.current_step = i
            task_step.status = "running"
            task_step.started_at = datetime.now(timezone.utc)

            await event_bus.publish(EventType.STEP_STARTED, {
                "step": task_step.name,
                "step_id": task_step.id,
                "task_id": task.id,
                "index": i,
                "total": len(steps),
            })
            task.logs.append(f"[STEP {i+1}/{len(steps)}] {task_step.name}: {task_step.description}")

            step_result = await self._execute_step(step, task)

            if step_result.success:
                task_step.status = "completed"
                task_step.result = step_result.output[:500] if step_result.output else "Done"
                results.append(f"Step {i+1} ({step.name}): {step_result.output[:200]}")
                task.logs.append(f"[OK] {task_step.name} completed in {step_result.duration:.1f}s")
            else:
                task_step.status = "failed"
                task_step.error = step_result.error

                # Attempt auto-debug
                if step_result.error:
                    task.logs.append(f"[DEBUG] Attempting to debug error: {step_result.error[:100]}")
                    debug_result = await self.debugger.analyze_error(
                        step_result.error,
                        self._context.get("last_code", ""),
                    )
                    task.logs.append(
                        f"[DEBUG] Root cause: {debug_result.root_cause}. "
                        f"Fix: {debug_result.suggested_fix}"
                    )

                if not step.parameters.get("optional", False):
                    failed = True
                    task.logs.append(f"[ERROR] Critical step failed: {step.name}")
                    break
                else:
                    task.logs.append(f"[WARN] Optional step failed, continuing: {step.name}")

            task_step.completed_at = datetime.now(timezone.utc)
            await event_bus.publish(EventType.STEP_COMPLETED, {
                "step": task_step.name,
                "step_id": task_step.id,
                "task_id": task.id,
                "success": step_result.success,
            })

        if failed:
            raise RuntimeError(f"Task failed at step: {task_steps[task.current_step].name}")

        summary = f"Task completed: {task.title}. Executed {len(results)} steps."
        task.logs.append(f"[DONE] {summary}")
        return summary

    async def _execute_step(self, step: Step, task: Task) -> StepResult:
        from tools.registry import tool_registry
        from tools.terminal import TerminalTool
        from tools.filesystem import FileSystemTool

        start = datetime.now(timezone.utc)
        agent = self.route_task_to_agent(step)

        await event_bus.publish(EventType.AGENT_THINKING, {
            "agent": agent.name,
            "message": f"Working on: {step.name}",
            "task_id": task.id,
        })

        try:
            if step.tool == "terminal":
                tool: TerminalTool = tool_registry.get("terminal")
                cmd = step.parameters.get("command", "echo 'No command specified'")
                cwd = step.parameters.get("cwd", settings.WORKSPACE_DIR)
                result = await tool.execute(cmd, cwd=cwd, timeout=60)
                output = result.stdout or result.stderr
                success = result.exit_code == 0
                if not success:
                    task.logs.append(f"[WARN] Command exit code {result.exit_code}: {result.stderr[:200]}")
                return StepResult(
                    step_id=step.id,
                    success=success,
                    output=output,
                    error=result.stderr if not success else None,
                    duration=(datetime.now(timezone.utc) - start).total_seconds(),
                    agent=agent.name,
                )

            elif step.tool == "filesystem":
                fs: FileSystemTool = tool_registry.get("filesystem")
                action = step.parameters.get("action", "list")
                if action == "write_file":
                    path = step.parameters.get("path", "output.txt")
                    content = step.parameters.get("content", "")

                    if not content:
                        # Generate code for this step
                        lang = self.coder.detect_language(task.description)
                        content = await self.coder.generate_code(
                            requirements=step.description,
                            language=lang,
                            context=task.description,
                        )
                        self._context["last_code"] = content
                        await event_bus.publish(EventType.CODE_GENERATED, {
                            "language": lang,
                            "path": path,
                            "task_id": task.id,
                        })
                    await fs.write_file(path, content)
                    return StepResult(
                        step_id=step.id,
                        success=True,
                        output=f"Written {path}",
                        duration=(datetime.now(timezone.utc) - start).total_seconds(),
                        agent=agent.name,
                    )
                elif action == "create_directory":
                    path = step.parameters.get("path", "project")
                    fs.create_directory(path)
                    return StepResult(
                        step_id=step.id,
                        success=True,
                        output=f"Created directory {path}",
                        duration=(datetime.now(timezone.utc) - start).total_seconds(),
                        agent=agent.name,
                    )
                else:
                    files = fs.list_directory(step.parameters.get("path", "."))
                    return StepResult(
                        step_id=step.id,
                        success=True,
                        output=str([f.name for f in files]),
                        duration=(datetime.now(timezone.utc) - start).total_seconds(),
                        agent=agent.name,
                    )

            elif step.tool == "browser":
                browser = tool_registry.get("browser")
                action = step.parameters.get("action", "search")
                if action == "search":
                    query = step.parameters.get("query", step.description)
                    results = await browser.search(query, num_results=3)
                    output = "\n".join(f"- {r.title}: {r.url}" for r in results) if results else "No results found"
                    return StepResult(
                        step_id=step.id,
                        success=True,
                        output=output,
                        duration=(datetime.now(timezone.utc) - start).total_seconds(),
                        agent=agent.name,
                    )
                elif action == "fetch":
                    url = step.parameters.get("url", "")
                    content = await browser.fetch_url(url) if url else "No URL provided"
                    return StepResult(
                        step_id=step.id,
                        success=bool(url),
                        output=content[:1000],
                        duration=(datetime.now(timezone.utc) - start).total_seconds(),
                        agent=agent.name,
                    )

            # Default: use coder agent to generate code
            lang = self.coder.detect_language(task.description)
            code = await self.coder.generate_code(
                requirements=step.description,
                language=lang,
                context=task.description,
            )
            self._context["last_code"] = code
            await event_bus.publish(EventType.CODE_GENERATED, {
                "language": lang,
                "task_id": task.id,
            })
            return StepResult(
                step_id=step.id,
                success=True,
                output=f"Generated {lang} code ({len(code)} chars)",
                duration=(datetime.now(timezone.utc) - start).total_seconds(),
                agent=agent.name,
            )

        except Exception as exc:
            logger.error(f"Step execution error: {exc}", exc_info=True)
            return StepResult(
                step_id=step.id,
                success=False,
                error=str(exc),
                duration=(datetime.now(timezone.utc) - start).total_seconds(),
                agent=agent.name,
            )

    def handle_agent_failure(self, agent: Any, error: Exception, context: Dict[str, Any]) -> str:
        logger.error(f"Agent {getattr(agent, 'name', 'unknown')} failed: {error}")
        if hasattr(agent, 'name') and agent.name in ("coder", "tester"):
            return "retry"
        return "skip"
