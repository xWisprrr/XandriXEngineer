"""
XandriX Engineer - Coder Agent
Generates, edits, and manages code across multiple languages.
"""
import json
from pathlib import Path
from typing import Optional

from backend.agents.base_agent import BaseAgent
from backend.core.llm_client import LLMMessage
from backend.models.schemas import AgentType, Task, TaskStep, TaskStatus

CODER_SYSTEM = """You are the Coder Agent for XandriX Engineer, an autonomous software engineering AI.

Your job is to write high-quality, production-ready code based on specifications.

Guidelines:
1. Write complete, working code - no placeholders or TODOs unless explicitly needed
2. Follow language-specific best practices and idioms
3. Include proper error handling
4. Add minimal but helpful comments for complex logic
5. Structure code clearly and maintainably
6. Consider edge cases

When asked to create or modify files, respond with a JSON object:
{
  "thoughts": "Brief reasoning about the implementation",
  "files": [
    {
      "path": "relative/path/to/file.ext",
      "action": "create|modify|delete",
      "content": "complete file content here"
    }
  ],
  "summary": "What was implemented",
  "next_steps": ["optional follow-up actions needed"]
}"""


class CoderAgent(BaseAgent):
    """Writes, edits, and manages code files."""

    agent_type = AgentType.CODER

    async def execute(self, task: Task, step: TaskStep) -> TaskStep:
        activity = self._create_activity(task.id)
        self._set_current_action(f"Implementing: {step.title}")

        fs = self._get_task_fs(task)
        project_dir = Path(task.project_dir) if task.project_dir else Path.cwd()

        # Build context for the LLM
        context = self._build_context(task, step, fs)

        prompt = f"""Task: {task.title}

Current Step: {step.title}
Description: {step.description}

Project Context:
{context}

Please implement the code for this step. Create or modify the necessary files."""

        try:
            response = await self.llm.chat(
                messages=[LLMMessage("user", prompt)],
                system=CODER_SYSTEM,
                temperature=0.2,
                json_mode=True,
            )

            result = response.extract_json()
            if result and "files" in result:
                written_files = []
                for file_info in result["files"]:
                    file_path = file_info.get("path", "")
                    action = file_info.get("action", "create")
                    content = file_info.get("content", "")

                    if not file_path:
                        continue

                    if action == "delete":
                        if fs.exists(file_path):
                            fs.delete(file_path)
                        self._add_action(f"Deleted {file_path}")
                    else:
                        fs.write(file_path, content)
                        self._add_action(f"{'Created' if action == 'create' else 'Modified'} {file_path}")
                        written_files.append(file_path)

                    # Track in memory
                    ctx = self.memory.get_task_context(task.id)
                    existing_files = ctx.get("files", [])
                    if file_path not in existing_files:
                        existing_files.append(file_path)
                    ctx.set("files", existing_files)

                summary = result.get("summary", f"Implemented {step.title}")
                step.output = f"{summary}\n\nFiles: {', '.join(written_files)}"
                step.status = TaskStatus.COMPLETED
                self.logger.success(f"Code written: {', '.join(written_files)}")

            else:
                # Fallback: try to extract raw code
                code = response.extract_code(task.language)
                if code and task.language:
                    filename = self._infer_filename(step.title, task.language)
                    fs.write(filename, code)
                    step.output = f"Created {filename}"
                    step.status = TaskStatus.COMPLETED
                else:
                    step.output = response.content
                    step.status = TaskStatus.COMPLETED

        except Exception as e:
            self.logger.error(f"Coder agent failed: {e}")
            step.error = str(e)
            step.status = TaskStatus.FAILED

        return step

    def _build_context(self, task: Task, step: TaskStep, fs) -> str:
        """Build context string for the LLM."""
        lines = []

        # Task metadata
        if task.language:
            lines.append(f"Language: {task.language}")

        # Existing files
        if task.project_dir:
            try:
                structure = fs.get_project_structure()
                if structure:
                    lines.append(f"\nProject Structure:\n{structure}")
            except Exception:
                pass

        # Previously completed steps
        completed = [s for s in task.steps if s.status == TaskStatus.COMPLETED]
        if completed:
            lines.append("\nCompleted Steps:")
            for s in completed[-3:]:  # Last 3 to keep context manageable
                lines.append(f"  - {s.title}: {(s.output or '')[:200]}")

        # Task-level context
        if task.context:
            arch = task.context.get("architecture", "")
            tech_stack = task.context.get("tech_stack", [])
            if arch:
                lines.append(f"\nArchitecture: {arch}")
            if tech_stack:
                lines.append(f"Tech Stack: {', '.join(tech_stack)}")

        # Short-term memory
        ctx = self.memory.get_task_context(task.id)
        existing_files = ctx.get("files", [])
        if existing_files:
            lines.append(f"\nFiles created so far: {', '.join(existing_files)}")

        return "\n".join(lines)

    def _infer_filename(self, title: str, language: str) -> str:
        """Infer a filename from the step title and language."""
        ext_map = {
            "python": ".py",
            "javascript": ".js",
            "typescript": ".ts",
            "go": ".go",
            "rust": ".rs",
            "c": ".c",
            "cpp": ".cpp",
            "java": ".java",
            "bash": ".sh",
            "sql": ".sql",
        }
        ext = ext_map.get(language, ".txt")
        name = title.lower().replace(" ", "_").replace("-", "_")
        # Remove non-alphanumeric chars
        import re
        name = re.sub(r"[^\w]", "", name)
        return f"{name}{ext}" if name else f"main{ext}"
