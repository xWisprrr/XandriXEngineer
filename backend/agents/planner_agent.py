"""
XandriX Engineer - Planner Agent
Handles analysis, research, and architectural decisions.
"""
from backend.agents.base_agent import BaseAgent
from backend.core.llm_client import LLMMessage
from backend.models.schemas import AgentType, Task, TaskStep, TaskStatus

PLANNER_SYSTEM = """You are the Planner/Analysis Agent for XandriX Engineer.

Your role is to analyze requirements, make architectural decisions, and research solutions.
When given a step, provide thorough analysis and concrete recommendations.

Return your analysis as a structured response including:
- Key findings or decisions
- Recommended approach
- Potential risks or edge cases
- Resources or references if applicable"""


class PlannerAgent(BaseAgent):
    """Handles analysis, research, and architectural decisions."""

    agent_type = AgentType.PLANNER

    async def execute(self, task: Task, step: TaskStep) -> TaskStep:
        self._create_activity(task.id)
        self._set_current_action(f"Analyzing: {step.title}")

        prompt = f"""Task: {task.title}
Description: {task.description}

Analysis Step: {step.title}
{step.description}

Completed context:
{self._get_completed_context(task)}

Provide a thorough analysis and actionable recommendations."""

        try:
            response = await self.llm.chat(
                messages=[LLMMessage("user", prompt)],
                system=PLANNER_SYSTEM,
                temperature=0.3,
            )
            step.output = response.content
            step.status = TaskStatus.COMPLETED

            # Store analysis in task context
            task.context["analysis"] = response.content[:1000]
            self.logger.success(f"Analysis complete for: {step.title}")

        except Exception as e:
            self.logger.error(f"Planner agent failed: {e}")
            step.error = str(e)
            step.status = TaskStatus.FAILED

        return step

    def _get_completed_context(self, task: Task) -> str:
        completed = [s for s in task.steps if s.status == TaskStatus.COMPLETED]
        if not completed:
            return "No steps completed yet."
        return "\n".join(
            f"- {s.title}: {(s.output or '')[:300]}"
            for s in completed[-5:]
        )
