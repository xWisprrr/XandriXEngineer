"""
XandriX Engineer - DevOps Agent
Handles environment setup, provisioning, and deployment.
"""
from pathlib import Path

from backend.agents.base_agent import BaseAgent
from backend.core.llm_client import LLMMessage
from backend.models.schemas import AgentType, Task, TaskStep, TaskStatus
from backend.runtime.environment_provisioner import EnvironmentProvisioner

DEVOPS_SYSTEM = """You are the DevOps Agent for XandriX Engineer.

Your role is to:
1. Set up development environments
2. Install dependencies and runtimes
3. Configure build systems
4. Handle deployment and containerization
5. Generate CI/CD configurations

Return a JSON with:
{
  "actions": [
    {"type": "install|configure|create_file|run_command", "description": "...", "command": "..."}
  ],
  "dependencies": ["list", "of", "deps"],
  "language": "detected language",
  "files_to_create": [
    {"path": "filename", "content": "content"}
  ],
  "summary": "What was set up"
}"""


class DevOpsAgent(BaseAgent):
    """Sets up environments and manages DevOps tasks."""

    agent_type = AgentType.DEVOPS

    async def execute(self, task: Task, step: TaskStep) -> TaskStep:
        self._create_activity(task.id)
        self._set_current_action(f"Setting up: {step.title}")

        project_dir = Path(task.project_dir) if task.project_dir else Path.cwd()
        terminal = self._get_task_terminal(task)
        provisioner = EnvironmentProvisioner(terminal)

        # Ask LLM what needs to be done
        prompt = f"""Task: {task.title}
Language: {task.language or "to be determined"}

DevOps Step: {step.title}
{step.description}

Project directory: {project_dir}

Determine what environment setup, installations, or configuration is needed."""

        try:
            response = await self.llm.chat(
                messages=[LLMMessage("user", prompt)],
                system=DEVOPS_SYSTEM,
                temperature=0.1,
                json_mode=True,
            )

            result = response.extract_json()
            output_lines = []

            if result:
                language = result.get("language", task.language)
                if language and not task.language:
                    task.language = language.lower()

                # Create any required files first
                fs = self._get_task_fs(task)
                for file_info in result.get("files_to_create", []):
                    fs.write(file_info["path"], file_info["content"])
                    output_lines.append(f"Created: {file_info['path']}")

                # Provision environment
                dependencies = result.get("dependencies", [])
                if task.language:
                    self._set_current_action(f"Provisioning {task.language} environment")
                    prov_result = await provisioner.provision(
                        project_dir, task.language, dependencies
                    )
                    output_lines.append(f"Environment: {prov_result.stdout or 'Ready'}")

                # Execute additional commands
                for action in result.get("actions", []):
                    cmd = action.get("command")
                    if cmd:
                        self._set_current_action(f"Running: {cmd[:60]}")
                        cmd_result = await terminal.run(cmd, working_dir=project_dir, timeout=300)
                        desc = action.get("description", cmd[:60])
                        if cmd_result.return_code == 0:
                            output_lines.append(f"✅ {desc}")
                        else:
                            output_lines.append(f"⚠️ {desc}: {(cmd_result.stderr or cmd_result.stdout)[:200]}")
                        self._add_action(desc, cmd_result.stdout[:200])

                summary = result.get("summary", f"Environment set up for {step.title}")
                step.output = "\n".join(output_lines) or summary
                step.status = TaskStatus.COMPLETED
                self.logger.success(f"DevOps step complete: {step.title}")

            else:
                # Fallback: basic provisioning
                if task.language:
                    prov_result = await provisioner.provision(project_dir, task.language)
                    step.output = prov_result.stdout or "Environment provisioned"
                else:
                    step.output = "Environment check complete"
                step.status = TaskStatus.COMPLETED

        except Exception as e:
            self.logger.error(f"DevOps agent failed: {e}")
            step.error = str(e)
            step.status = TaskStatus.FAILED

        return step
