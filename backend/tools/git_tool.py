"""
XandriX Engineer - Tool: Git Integration
"""
from pathlib import Path
from typing import Optional

from backend.core.logger import get_logger
from backend.models.schemas import ExecutionResult
from backend.tools.terminal import Terminal

logger = get_logger("tool.git")


class GitTool:
    """Git operations for version control management."""

    def __init__(self, repo_path: Path, terminal: Terminal = None):
        self.repo_path = repo_path
        self.terminal = terminal or Terminal(working_dir=repo_path)
        self.terminal.set_working_dir(repo_path)

    async def init(self) -> ExecutionResult:
        """Initialize a new git repository."""
        result = await self.terminal.run("git init", working_dir=self.repo_path)
        if result.return_code == 0:
            await self.terminal.run(
                'git config user.email "xandrix@engineer.ai"',
                working_dir=self.repo_path,
            )
            await self.terminal.run(
                'git config user.name "XandriX Engineer"',
                working_dir=self.repo_path,
            )
        return result

    async def add(self, paths: list[str] = None) -> ExecutionResult:
        """Stage files for commit."""
        if paths:
            files = " ".join(paths)
            return await self.terminal.run(f"git add {files}", working_dir=self.repo_path)
        return await self.terminal.run("git add -A", working_dir=self.repo_path)

    async def commit(self, message: str) -> ExecutionResult:
        """Create a commit with all staged changes."""
        safe_msg = message.replace('"', '\\"')
        return await self.terminal.run(
            f'git commit -m "{safe_msg}"',
            working_dir=self.repo_path,
        )

    async def add_and_commit(self, message: str, paths: list[str] = None) -> ExecutionResult:
        """Stage all changes and commit."""
        await self.add(paths)
        return await self.commit(message)

    async def status(self) -> str:
        """Get git status."""
        result = await self.terminal.run("git status --short", working_dir=self.repo_path)
        return result.stdout

    async def log(self, n: int = 10) -> str:
        """Get recent commit log."""
        result = await self.terminal.run(
            f"git log --oneline -n {n}",
            working_dir=self.repo_path,
        )
        return result.stdout

    async def diff(self, staged: bool = False) -> str:
        """Get diff of changes."""
        cmd = "git diff --staged" if staged else "git diff"
        result = await self.terminal.run(cmd, working_dir=self.repo_path)
        return result.stdout

    async def branch(self, name: str) -> ExecutionResult:
        """Create and switch to a new branch."""
        return await self.terminal.run(
            f"git checkout -b {name}",
            working_dir=self.repo_path,
        )

    async def checkout(self, ref: str) -> ExecutionResult:
        """Checkout a branch or commit."""
        return await self.terminal.run(
            f"git checkout {ref}",
            working_dir=self.repo_path,
        )

    async def is_repo(self) -> bool:
        """Check if the path is a git repository."""
        result = await self.terminal.run(
            "git rev-parse --is-inside-work-tree 2>/dev/null",
            working_dir=self.repo_path,
        )
        return result.return_code == 0 and result.stdout.strip() == "true"

    async def create_gitignore(self, language: str) -> None:
        """Create a .gitignore file for the given language/framework."""
        patterns = {
            "python": "__pycache__/\n*.pyc\n*.pyo\n.venv/\nvenv/\n*.egg-info/\ndist/\nbuild/\n.pytest_cache/\n",
            "javascript": "node_modules/\ndist/\nbuild/\n.env\n.env.local\n*.log\n",
            "typescript": "node_modules/\ndist/\nbuild/\n.env\n*.js.map\n*.d.ts\n",
            "go": "*.exe\n*.test\nvendor/\n",
            "rust": "target/\nCargo.lock\n",
            "java": "*.class\n*.jar\ntarget/\n.idea/\n",
        }
        content = patterns.get(language, "*.log\n.env\n.DS_Store\n")
        gitignore = self.repo_path / ".gitignore"
        if not gitignore.exists():
            gitignore.write_text(content)
