"""
XandriX Engineer - Debugger Agent
Analyzes errors, fixes code, and iterates until resolution.
"""
from pathlib import Path

from backend.agents.base_agent import BaseAgent
from backend.core.llm_client import LLMMessage
from backend.models.schemas import AgentType, Task, TaskStep, TaskStatus
from backend.runtime.runtime_manager import RuntimeManager

DEBUGGER_SYSTEM = """You are the Debugger Agent for XandriX Engineer.

Your role is to analyze errors, identify root causes, and fix code.

Debugging approach:
1. Read the error message carefully
2. Identify the root cause (not just symptoms)
3. Look at the relevant code
4. Apply the minimal fix
5. Verify the fix makes logical sense

Return a JSON with:
{
  "analysis": "Root cause analysis",
  "root_cause": "The core issue",
  "fixes": [
    {
      "file": "path/to/file",
      "description": "What was changed",
      "content": "complete new file content"
    }
  ],
  "verification": "How to verify the fix works",
  "summary": "Summary of the fix"
}"""


class DebuggerAgent(BaseAgent):
    """Analyzes errors and fixes code autonomously."""

    agent_type = AgentType.DEBUGGER

    async def execute(self, task: Task, step: TaskStep) -> TaskStep:
        self._create_activity(task.id)
        self._set_current_action(f"Debugging: {step.title}")

        fs = self._get_task_fs(task)
        terminal = self._get_task_terminal(task)
        runtime = RuntimeManager(terminal)
        project_dir = Path(task.project_dir) if task.project_dir else Path.cwd()

        # Collect error context
        error_context = self._collect_error_context(task, step)
        code_context = self._get_code_context(task, fs)

        prompt = f"""Task: {task.title}
Language: {task.language or "unknown"}

Debug Step: {step.title}
{step.description}

Error Information:
{error_context}

Relevant Code:
{code_context}

Analyze the error, identify the root cause, and provide fixes."""

        try:
            response = await self.llm.chat(
                messages=[LLMMessage("user", prompt)],
                system=DEBUGGER_SYSTEM,
                temperature=0.2,
                json_mode=True,
            )

            result = response.extract_json()
            output_lines = []

            if result and "fixes" in result:
                analysis = result.get("analysis", "")
                root_cause = result.get("root_cause", "")
                output_lines.append(f"Root Cause: {root_cause}")
                output_lines.append(f"Analysis: {analysis}")

                for fix in result["fixes"]:
                    file_path = fix.get("file", "")
                    content = fix.get("content", "")
                    description = fix.get("description", "")

                    if file_path and content:
                        fs.write(file_path, content)
                        output_lines.append(f"\nFixed: {file_path}")
                        output_lines.append(f"Change: {description}")
                        self._add_action(f"Fixed {file_path}: {description}")

                # Attempt to re-run and verify
                verify_result = await self._verify_fix(task, runtime, project_dir)
                if verify_result:
                    output_lines.append(f"\nVerification: {verify_result}")

                step.output = "\n".join(output_lines)
                step.status = TaskStatus.COMPLETED
                step.error = None
                self.logger.success(f"Debug complete: {root_cause}")

            else:
                # Fallback: provide raw analysis
                step.output = response.content
                step.status = TaskStatus.COMPLETED

        except Exception as e:
            self.logger.error(f"Debugger agent failed: {e}")
            step.error = str(e)
            step.status = TaskStatus.FAILED

        return step

    def _collect_error_context(self, task: Task, step: TaskStep) -> str:
        """Collect error information from task history."""
        lines = []

        # Current step error
        if step.error:
            lines.append(f"Current error: {step.error}")

        # Previous failed steps
        failed = [s for s in task.steps if s.status == TaskStatus.FAILED and s.id != step.id]
        for fs_step in failed[-3:]:
            if fs_step.error:
                lines.append(f"Previous error in '{fs_step.title}': {fs_step.error[:500]}")

        # Task context errors
        if "last_error" in task.context:
            lines.append(f"Last error: {task.context['last_error'][:500]}")

        return "\n".join(lines) if lines else "No specific error information available."

    def _get_code_context(self, task: Task, fs) -> str:
        """Get relevant code for debugging."""
        ctx = self.memory.get_task_context(task.id)
        files = ctx.get("files", [])
        context_parts = []
        for file_path in files:
            try:
                content = fs.read(file_path)
                context_parts.append(f"### {file_path}\n```\n{content[:3000]}\n```")
            except Exception:
                pass
        return "\n\n".join(context_parts) if context_parts else "No code context available."

    async def _verify_fix(self, task: Task, runtime: RuntimeManager, project_dir: Path) -> str:
        """Try to re-run the code to verify the fix."""
        if not task.language:
            return ""

        run_commands = {
            "python": "python3 -m pytest -x -q 2>&1 || python3 main.py 2>&1",
            "javascript": "node index.js 2>&1",
            "typescript": "ts-node src/index.ts 2>&1",
            "go": "go build ./... 2>&1",
            "rust": "cargo build 2>&1",
            "java": "javac *.java 2>&1",
        }

        cmd = run_commands.get(task.language)
        if not cmd:
            return ""

        terminal = self._get_task_terminal(task)
        result = await terminal.run(cmd, working_dir=project_dir, timeout=60)
        if result.return_code == 0:
            return f"✅ Verification passed"
        return f"⚠️ Still has issues: {(result.stderr or result.stdout)[:300]}"
