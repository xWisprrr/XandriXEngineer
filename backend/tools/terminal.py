"""
XandriX Engineer - Tool: Terminal Execution
Provides sandboxed command execution with timeout and output capture.
"""
import asyncio
import os
import shlex
import signal
from pathlib import Path
from typing import Optional

from backend.core.logger import get_logger
from backend.models.schemas import ExecutionResult, ExecutionStatus

logger = get_logger("tool.terminal")


class Terminal:
    """Asynchronous terminal execution with timeout and output capture."""

    def __init__(self, working_dir: Optional[Path] = None, timeout: int = 120):
        self.working_dir = working_dir or Path.cwd()
        self.timeout = timeout
        self._env = dict(os.environ)

    def set_env(self, key: str, value: str) -> None:
        self._env[key] = value

    def set_working_dir(self, path: Path) -> None:
        self.working_dir = path

    async def run(
        self,
        command: str,
        working_dir: Optional[Path] = None,
        timeout: Optional[int] = None,
        env: Optional[dict] = None,
        stdin_data: Optional[str] = None,
    ) -> ExecutionResult:
        """Execute a shell command and return the result."""
        cwd = str(working_dir or self.working_dir)
        timeout = timeout or self.timeout
        merged_env = {**self._env, **(env or {})}

        logger.tool("terminal", f"Running: {command[:200]}", {"cwd": cwd})

        import time
        start = time.time()

        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                stdin=asyncio.subprocess.PIPE if stdin_data else None,
                cwd=cwd,
                env=merged_env,
            )

            stdin_bytes = stdin_data.encode() if stdin_data else None

            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(input=stdin_bytes),
                    timeout=timeout,
                )
            except asyncio.TimeoutError:
                try:
                    proc.kill()
                except ProcessLookupError:
                    pass
                return ExecutionResult(
                    status=ExecutionStatus.TIMEOUT,
                    stdout="",
                    stderr=f"Command timed out after {timeout}s",
                    return_code=-1,
                    duration=time.time() - start,
                )

            duration = time.time() - start
            stdout_str = stdout.decode("utf-8", errors="replace")
            stderr_str = stderr.decode("utf-8", errors="replace")
            rc = proc.returncode

            status = ExecutionStatus.SUCCESS if rc == 0 else ExecutionStatus.ERROR
            result = ExecutionResult(
                status=status,
                stdout=stdout_str,
                stderr=stderr_str,
                return_code=rc,
                duration=duration,
            )

            if rc != 0:
                logger.tool("terminal", f"Command failed (rc={rc}): {stderr_str[:500]}")
            else:
                logger.tool("terminal", f"Command succeeded in {duration:.2f}s")

            return result

        except FileNotFoundError as e:
            return ExecutionResult(
                status=ExecutionStatus.ERROR,
                stderr=f"Command not found: {e}",
                return_code=127,
            )
        except Exception as e:
            return ExecutionResult(
                status=ExecutionStatus.ERROR,
                stderr=f"Execution error: {e}",
                return_code=-1,
            )

    async def run_script(
        self,
        script: str,
        interpreter: str = "bash",
        working_dir: Optional[Path] = None,
        timeout: Optional[int] = None,
    ) -> ExecutionResult:
        """Execute a multi-line script."""
        import tempfile

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".sh" if interpreter == "bash" else ".py",
            delete=False
        ) as f:
            f.write(script)
            script_path = f.name

        try:
            result = await self.run(
                f"{interpreter} {script_path}",
                working_dir=working_dir,
                timeout=timeout,
            )
        finally:
            try:
                os.unlink(script_path)
            except OSError:
                pass

        return result

    async def install_package(self, package: str, manager: str = "pip") -> ExecutionResult:
        """Install a package using the specified package manager."""
        commands = {
            "pip": f"pip install --quiet {package}",
            "npm": f"npm install --silent {package}",
            "cargo": f"cargo add {package}",
            "apt": f"apt-get install -y {package}",
            "go": f"go get {package}",
        }
        cmd = commands.get(manager, f"{manager} install {package}")
        return await self.run(cmd, timeout=300)

    async def check_command_exists(self, command: str) -> bool:
        """Check if a command is available in PATH."""
        result = await self.run(f"which {command} 2>/dev/null || command -v {command} 2>/dev/null")
        return result.return_code == 0

    async def get_output(self, command: str, **kwargs) -> str:
        """Run a command and return stdout as a string."""
        result = await self.run(command, **kwargs)
        return result.stdout.strip()
