import asyncio
import os
import subprocess
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from utils.logger import get_logger

logger = get_logger(__name__)

ALLOWED_COMMANDS = {
    "python", "python3", "node", "npm", "npx", "go", "cargo", "rustc",
    "javac", "java", "gcc", "g++", "make", "bash", "sh", "ls", "cat",
    "mkdir", "cp", "mv", "rm", "echo", "pwd", "cd", "git", "pip", "pip3",
    "curl", "wget", "find", "grep", "sed", "awk", "sort", "uniq", "head",
    "tail", "wc", "diff", "patch", "tar", "zip", "unzip",
}


@dataclass
class ExecutionResult:
    stdout: str
    stderr: str
    exit_code: int
    duration: float
    command: str = ""


class TerminalTool:
    name = "terminal"

    def __init__(self, default_cwd: Optional[str] = None) -> None:
        self.default_cwd = default_cwd or os.getcwd()

    def _sanitize_command(self, command: str) -> str:
        # Basic sanitization: check that the first token is in allowed list
        first_token = command.strip().split()[0] if command.strip() else ""
        # Strip any path prefix
        base_cmd = os.path.basename(first_token)
        if base_cmd and base_cmd not in ALLOWED_COMMANDS:
            # Warn but allow execution — the agent may need arbitrary commands.
            # Operators can restrict this list via config in production deployments.
            logger.warning(
                f"Command '{base_cmd}' is not in the pre-approved list; proceeding with caution. "
                "Review ALLOWED_COMMANDS in terminal.py to restrict execution."
            )
        return command

    async def execute(
        self,
        command: str,
        cwd: Optional[str] = None,
        timeout: int = 60,
        env: Optional[Dict[str, str]] = None,
    ) -> ExecutionResult:
        cwd = cwd or self.default_cwd
        os.makedirs(cwd, exist_ok=True)
        safe_command = self._sanitize_command(command)
        exec_env = os.environ.copy()
        if env:
            exec_env.update(env)

        start = time.monotonic()
        try:
            process = await asyncio.create_subprocess_shell(
                safe_command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
                env=exec_env,
            )
            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    process.communicate(), timeout=timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.communicate()
                duration = time.monotonic() - start
                return ExecutionResult(
                    stdout="",
                    stderr=f"Command timed out after {timeout}s",
                    exit_code=-1,
                    duration=duration,
                    command=command,
                )
            duration = time.monotonic() - start
            return ExecutionResult(
                stdout=stdout_bytes.decode("utf-8", errors="replace"),
                stderr=stderr_bytes.decode("utf-8", errors="replace"),
                exit_code=process.returncode or 0,
                duration=duration,
                command=command,
            )
        except Exception as exc:
            duration = time.monotonic() - start
            logger.error(f"Terminal execution error: {exc}")
            return ExecutionResult(
                stdout="",
                stderr=str(exc),
                exit_code=1,
                duration=duration,
                command=command,
            )

    async def execute_in_docker(
        self,
        command: str,
        image: str = "python:3.11-slim",
        cwd: str = "/workspace",
        timeout: int = 60,
    ) -> ExecutionResult:
        docker_cmd = (
            f"docker run --rm -w {cwd} {image} sh -c {repr(command)}"
        )
        return await self.execute(docker_cmd, timeout=timeout)

    async def run_python_code(self, code: str, cwd: Optional[str] = None) -> ExecutionResult:
        script_path = os.path.join(cwd or self.default_cwd, "_temp_script.py")
        with open(script_path, "w") as f:
            f.write(code)
        try:
            return await self.execute(f"python3 {script_path}", cwd=cwd, timeout=30)
        finally:
            if os.path.exists(script_path):
                os.remove(script_path)
