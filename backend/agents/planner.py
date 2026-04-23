import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from config import settings
from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class Step:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    tool: str = "terminal"
    parameters: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    status: str = "pending"
    result: Optional[str] = None


class PlannerAgent:
    name = "planner"

    def __init__(self) -> None:
        self.status = "idle"
        self.current_action = ""

    async def analyze_task(self, task_description: str) -> List[Step]:
        self.status = "active"
        self.current_action = "Analyzing task and creating plan"
        logger.info(f"PlannerAgent: analyzing task: {task_description[:80]}...")

        if settings.OPENAI_API_KEY or settings.ANTHROPIC_API_KEY:
            try:
                steps = await self._llm_plan(task_description)
                if steps:
                    self.status = "idle"
                    return steps
            except Exception as exc:
                logger.warning(f"LLM planning failed, using rule-based fallback: {exc}")

        steps = self._rule_based_plan(task_description)
        self.status = "idle"
        self.current_action = ""
        return steps

    async def _llm_plan(self, task_description: str) -> List[Step]:
        prompt = f"""You are a software engineering planner. Break the following task into concrete steps.
Return a JSON array of steps, each with: name, description, tool (one of: terminal, filesystem, browser, git), parameters (dict).

Task: {task_description}

Return ONLY valid JSON array, no explanation."""

        response_text = await self._call_llm(prompt)
        import json, re
        match = re.search(r'\[.*\]', response_text, re.DOTALL)
        if not match:
            return []
        raw_steps = json.loads(match.group(0))
        steps = []
        for i, s in enumerate(raw_steps):
            steps.append(Step(
                name=s.get("name", f"Step {i+1}"),
                description=s.get("description", ""),
                tool=s.get("tool", "terminal"),
                parameters=s.get("parameters", {}),
            ))
        return steps

    def _rule_based_plan(self, task_description: str) -> List[Step]:
        desc_lower = task_description.lower()
        steps: List[Step] = []

        if any(kw in desc_lower for kw in ["create", "build", "write", "implement", "generate"]):
            steps.append(Step(
                name="Understand Requirements",
                description=f"Analyze and understand: {task_description[:100]}",
                tool="browser",
                parameters={"action": "search", "query": task_description[:80]},
            ))
            steps.append(Step(
                name="Create Project Structure",
                description="Set up project directories and files",
                tool="filesystem",
                parameters={"action": "create_directory", "path": "project"},
            ))
            steps.append(Step(
                name="Generate Code",
                description="Write the implementation code",
                tool="filesystem",
                parameters={"action": "write_file", "path": "project/main.py"},
                dependencies=[steps[1].id] if len(steps) > 1 else [],
            ))
            steps.append(Step(
                name="Run and Test",
                description="Execute and verify the implementation",
                tool="terminal",
                parameters={"command": "python3 project/main.py"},
                dependencies=[steps[2].id] if len(steps) > 2 else [],
            ))
        elif any(kw in desc_lower for kw in ["fix", "debug", "repair", "solve"]):
            steps.append(Step(
                name="Analyze Error",
                description="Identify the root cause of the issue",
                tool="terminal",
                parameters={"command": "echo 'Analyzing error...'"},
            ))
            steps.append(Step(
                name="Apply Fix",
                description="Implement the fix",
                tool="filesystem",
                parameters={"action": "edit"},
            ))
            steps.append(Step(
                name="Verify Fix",
                description="Run tests to confirm fix",
                tool="terminal",
                parameters={"command": "echo 'Verifying...'"},
                dependencies=[steps[1].id] if len(steps) > 1 else [],
            ))
        elif any(kw in desc_lower for kw in ["test", "check", "verify"]):
            steps.append(Step(
                name="Run Tests",
                description="Execute test suite",
                tool="terminal",
                parameters={"command": "python3 -m pytest -v"},
            ))
        else:
            steps.append(Step(
                name="Execute Task",
                description=task_description,
                tool="terminal",
                parameters={"command": f"echo 'Task: {task_description[:50]}'"},
            ))

        return steps

    async def _call_llm(self, prompt: str) -> str:
        if settings.MODEL_PROVIDER == "anthropic" and settings.ANTHROPIC_API_KEY:
            import anthropic
            client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
            msg = await client.messages.create(
                model=settings.DEFAULT_MODEL or "claude-3-opus-20240229",
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}],
            )
            return msg.content[0].text
        elif settings.OPENAI_API_KEY:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            response = await client.chat.completions.create(
                model=settings.DEFAULT_MODEL or "gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2000,
            )
            return response.choices[0].message.content or ""
        raise ValueError("No LLM API key configured")
