"""
XandriX Engineer - Tester Agent
Writes and runs tests, validates outputs.
"""
from pathlib import Path

from backend.agents.base_agent import BaseAgent
from backend.core.llm_client import LLMMessage
from backend.models.schemas import AgentType, ExecutionStatus, Task, TaskStep, TaskStatus
from backend.runtime.runtime_manager import RuntimeManager

TESTER_SYSTEM = """You are the Tester Agent for XandriX Engineer.

Your role is to:
1. Write comprehensive tests for the code that has been created
2. Run those tests and validate the output
3. Report any failures with clear descriptions

When writing tests, follow best practices:
- Use the appropriate testing framework for the language
- Cover happy path, edge cases, and error cases
- Keep tests independent and reproducible

Return a JSON with:
{
  "thoughts": "Testing strategy",
  "test_files": [
    {"path": "test_file.py", "content": "test code"}
  ],
  "run_command": "command to run tests",
  "summary": "What is being tested"
}"""


class TesterAgent(BaseAgent):
    """Writes and runs tests, validates code."""

    agent_type = AgentType.TESTER

    async def execute(self, task: Task, step: TaskStep) -> TaskStep:
        self._create_activity(task.id)
        self._set_current_action(f"Testing: {step.title}")

        fs = self._get_task_fs(task)
        terminal = self._get_task_terminal(task)
        runtime = RuntimeManager(terminal)
        project_dir = Path(task.project_dir) if task.project_dir else Path.cwd()

        # Get existing code context
        code_context = self._get_code_context(task, fs)

        prompt = f"""Task: {task.title}
Language: {task.language or "unknown"}

Step to test: {step.title}
{step.description}

Existing code:
{code_context}

Write comprehensive tests and provide the command to run them."""

        try:
            response = await self.llm.chat(
                messages=[LLMMessage("user", prompt)],
                system=TESTER_SYSTEM,
                temperature=0.2,
                json_mode=True,
            )

            result = response.extract_json()
            output_lines = []

            if result and "test_files" in result:
                for tf in result["test_files"]:
                    fs.write(tf["path"], tf["content"])
                    output_lines.append(f"Created test: {tf['path']}")
                    self._add_action(f"Created {tf['path']}")

                # Run the tests
                run_cmd = result.get("run_command")
                if run_cmd:
                    self._set_current_action(f"Running: {run_cmd}")
                    exec_result = await terminal.run(
                        run_cmd,
                        working_dir=project_dir,
                        timeout=120,
                    )

                    if exec_result.return_code == 0:
                        output_lines.append(f"\n✅ Tests PASSED:\n{exec_result.stdout[:1000]}")
                        step.status = TaskStatus.COMPLETED
                    else:
                        output_lines.append(f"\n❌ Tests FAILED:\n{exec_result.stderr[:1000] or exec_result.stdout[:1000]}")
                        step.error = exec_result.stderr or exec_result.stdout
                        step.status = TaskStatus.FAILED
                else:
                    step.status = TaskStatus.COMPLETED

                step.output = "\n".join(output_lines)
            else:
                # Run existing test files if any
                test_result = await self._run_existing_tests(task, terminal, project_dir)
                step.output = test_result
                step.status = TaskStatus.COMPLETED

        except Exception as e:
            self.logger.error(f"Tester agent failed: {e}")
            step.error = str(e)
            step.status = TaskStatus.FAILED

        return step

    def _get_code_context(self, task: Task, fs) -> str:
        """Get relevant code files for testing."""
        ctx = self.memory.get_task_context(task.id)
        files = ctx.get("files", [])
        context_parts = []
        for file_path in files[:5]:  # Limit to 5 files
            try:
                content = fs.read(file_path)
                context_parts.append(f"File: {file_path}\n```\n{content[:2000]}\n```")
            except Exception:
                pass
        return "\n\n".join(context_parts) if context_parts else "No code files found."

    async def _run_existing_tests(self, task: Task, terminal, project_dir: Path) -> str:
        """Try to run existing test files."""
        test_commands = {
            "python": "python3 -m pytest -v 2>&1 || python3 -m unittest discover -v 2>&1",
            "javascript": "npm test 2>&1",
            "typescript": "npm test 2>&1",
            "go": "go test ./... 2>&1",
            "rust": "cargo test 2>&1",
            "java": "mvn test 2>&1",
        }
        cmd = test_commands.get(task.language or "", "echo 'No test runner configured'")
        result = await terminal.run(cmd, working_dir=project_dir, timeout=120)
        return result.stdout + result.stderr
