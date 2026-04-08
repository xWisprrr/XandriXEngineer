"""
XandriX Engineer - Task Planner
Decomposes high-level goals into concrete, ordered steps.
"""
import json
from typing import Optional

from backend.config import SUPPORTED_LANGUAGES
from backend.core.llm_client import LLMClient, LLMMessage, llm
from backend.core.logger import get_logger
from backend.models.schemas import AgentType, Task, TaskStep, TaskStatus

logger = get_logger("planner")

PLANNER_SYSTEM = """You are the Planning Agent for XandriX Engineer, an autonomous AI software engineering system.

Your job is to analyze a software engineering task and decompose it into a series of concrete, executable steps.

Each step must be assigned to one of these specialized agents:
- planner: Further analysis, research, or architectural decisions
- coder: Writing, editing, or generating code
- tester: Writing tests, running tests, validating outputs
- debugger: Fixing errors, analyzing stack traces, troubleshooting
- devops: Setting up environments, installing dependencies, deployment

Rules:
1. Keep steps atomic and focused (one clear action per step)
2. Order steps logically (dependencies first)
3. Include environment setup early if needed
4. Always include a testing/validation step
5. Limit to 10-15 steps for most tasks
6. Be specific about what code/files need to be created/modified

Return your response as a JSON object with this exact structure:
{
  "title": "Brief task title",
  "language": "primary language (python/javascript/typescript/go/rust/java/c/cpp/bash/sql)",
  "steps": [
    {
      "title": "Step title",
      "description": "Detailed description of what to do",
      "agent": "agent_type",
      "dependencies": []
    }
  ],
  "context": {
    "architecture": "brief architectural notes",
    "tech_stack": ["list", "of", "technologies"],
    "key_files": ["expected files to create/modify"]
  }
}"""


class TaskPlanner:
    """Decomposes natural language goals into executable task steps."""

    def __init__(self, llm_client: LLMClient = None):
        self.llm = llm_client or llm

    async def plan(self, task: Task) -> Task:
        """Generate a step-by-step plan for the given task."""
        logger.info(f"Planning task: {task.title}", {"task_id": task.id})

        task.status = TaskStatus.PLANNING

        try:
            plan_data = await self._generate_plan(task)
            task = self._apply_plan(task, plan_data)
            logger.success(f"Plan generated: {len(task.steps)} steps", {"task_id": task.id})
        except Exception as e:
            logger.error(f"Planning failed: {e}", {"task_id": task.id})
            task = self._fallback_plan(task)

        return task

    async def _generate_plan(self, task: Task) -> dict:
        """Call LLM to generate the plan."""
        prompt = f"""Task Title: {task.title}

Task Description:
{task.description}

{"Language preference: " + task.language if task.language else ""}

Please analyze this task and create a detailed execution plan."""

        response = await self.llm.chat(
            messages=[LLMMessage("user", prompt)],
            system=PLANNER_SYSTEM,
            temperature=0.2,
            json_mode=True,
        )

        plan_data = response.extract_json()
        if not plan_data:
            raise ValueError("Failed to parse plan JSON from LLM response")

        return plan_data

    def _apply_plan(self, task: Task, plan_data: dict) -> Task:
        """Apply the parsed plan data to the task."""
        if not task.language and "language" in plan_data:
            lang = plan_data["language"].lower()
            if lang in SUPPORTED_LANGUAGES:
                task.language = lang

        task.context.update(plan_data.get("context", {}))

        steps = []
        for i, step_data in enumerate(plan_data.get("steps", [])):
            agent_str = step_data.get("agent", "coder").lower()
            try:
                agent = AgentType(agent_str)
            except ValueError:
                agent = AgentType.CODER

            step = TaskStep(
                title=step_data.get("title", f"Step {i+1}"),
                description=step_data.get("description", ""),
                agent=agent,
                dependencies=step_data.get("dependencies", []),
            )
            steps.append(step)

        task.steps = steps
        return task

    def _fallback_plan(self, task: Task) -> Task:
        """Generate a basic plan when LLM planning fails."""
        logger.warning("Using fallback plan")

        task.steps = [
            TaskStep(
                title="Setup Environment",
                description="Set up the development environment and install required dependencies.",
                agent=AgentType.DEVOPS,
            ),
            TaskStep(
                title="Analyze Requirements",
                description=f"Analyze the task requirements: {task.description}",
                agent=AgentType.PLANNER,
            ),
            TaskStep(
                title="Implement Solution",
                description="Write the core implementation code.",
                agent=AgentType.CODER,
            ),
            TaskStep(
                title="Test Implementation",
                description="Test and validate the implementation.",
                agent=AgentType.TESTER,
            ),
            TaskStep(
                title="Debug and Refine",
                description="Fix any issues and refine the solution.",
                agent=AgentType.DEBUGGER,
            ),
        ]
        return task

    async def replan(self, task: Task, reason: str) -> Task:
        """Replan remaining steps after an error or changed context."""
        completed = [s for s in task.steps if s.status == TaskStatus.COMPLETED]
        remaining_count = len(task.steps) - len(completed)

        logger.info(f"Replanning task ({remaining_count} steps remaining): {reason}")

        prompt = f"""Task: {task.title}
Description: {task.description}

Completed steps so far:
{json.dumps([{"title": s.title, "output": s.output} for s in completed], indent=2)}

Issue encountered: {reason}

Current context:
{json.dumps(task.context, indent=2)}

Please generate revised remaining steps to complete the task, taking into account what has been done and the issue encountered."""

        try:
            response = await self.llm.chat(
                messages=[LLMMessage("user", prompt)],
                system=PLANNER_SYSTEM,
                temperature=0.3,
                json_mode=True,
            )
            plan_data = response.extract_json()
            if plan_data and "steps" in plan_data:
                new_steps = []
                for step_data in plan_data["steps"]:
                    agent_str = step_data.get("agent", "coder").lower()
                    try:
                        agent = AgentType(agent_str)
                    except ValueError:
                        agent = AgentType.CODER
                    new_steps.append(TaskStep(
                        title=step_data.get("title", "Step"),
                        description=step_data.get("description", ""),
                        agent=agent,
                    ))
                task.steps = completed + new_steps
                task.current_step = len(completed)
                return task
        except Exception as e:
            logger.error(f"Replan failed: {e}")

        return task
