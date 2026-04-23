import asyncio
import os
import re
import subprocess
from enum import Enum
from typing import Any, Dict, List, Optional

from tools.terminal import ExecutionResult, TerminalTool
from utils.logger import get_logger

logger = get_logger(__name__)


class Language(str, Enum):
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    GO = "go"
    RUST = "rust"
    JAVA = "java"
    C = "c"
    CPP = "cpp"
    BASH = "bash"
    SQL = "sql"
    UNKNOWN = "unknown"


EXTENSION_MAP: Dict[str, Language] = {
    ".py": Language.PYTHON,
    ".js": Language.JAVASCRIPT,
    ".mjs": Language.JAVASCRIPT,
    ".ts": Language.TYPESCRIPT,
    ".tsx": Language.TYPESCRIPT,
    ".go": Language.GO,
    ".rs": Language.RUST,
    ".java": Language.JAVA,
    ".c": Language.C,
    ".cpp": Language.CPP,
    ".cc": Language.CPP,
    ".cxx": Language.CPP,
    ".sh": Language.BASH,
    ".bash": Language.BASH,
    ".sql": Language.SQL,
}

RUNTIME_COMMANDS: Dict[Language, str] = {
    Language.PYTHON: "python3",
    Language.JAVASCRIPT: "node",
    Language.TYPESCRIPT: "npx ts-node",
    Language.GO: "go run",
    Language.RUST: "cargo run",
    Language.JAVA: "java",
    Language.C: "gcc",
    Language.CPP: "g++",
    Language.BASH: "bash",
}


class RuntimeManager:
    def __init__(self, workspace_dir: str = "./workspace") -> None:
        self.workspace_dir = os.path.abspath(workspace_dir)
        os.makedirs(self.workspace_dir, exist_ok=True)
        self._terminal = TerminalTool(default_cwd=self.workspace_dir)

    def detect_language(self, code_or_file: str) -> Language:
        # Try by file extension
        _, ext = os.path.splitext(code_or_file)
        if ext in EXTENSION_MAP:
            return EXTENSION_MAP[ext]

        # Try by code content heuristics
        code = code_or_file
        if re.search(r"^\s*(import|from)\s+\w+", code, re.MULTILINE):
            return Language.PYTHON
        if re.search(r"(console\.log|require\(|const |let |var |=>)", code):
            return Language.JAVASCRIPT
        if re.search(r"(func main\(\)|fmt\.Println|package main)", code):
            return Language.GO
        if re.search(r"(fn main\(\)|println!|use std::)", code):
            return Language.RUST
        if re.search(r"(public class|System\.out|import java\.)", code):
            return Language.JAVA
        if re.search(r"(#include|int main\(|printf\()", code):
            if "cout" in code or "std::" in code:
                return Language.CPP
            return Language.C
        if re.search(r"(#!/bin/bash|echo |grep |awk )", code):
            return Language.BASH
        return Language.UNKNOWN

    def check_runtime(self, language: Language) -> bool:
        cmd = RUNTIME_COMMANDS.get(language)
        if not cmd:
            return False
        executable = cmd.split()[0]
        try:
            result = subprocess.run(
                [executable, "--version"], capture_output=True, timeout=5
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def get_available_runtimes(self) -> Dict[Language, bool]:
        return {lang: self.check_runtime(lang) for lang in Language if lang != Language.UNKNOWN}

    def install_runtime(self, language: Language) -> bool:
        instructions = {
            Language.PYTHON: "sudo apt-get install python3 python3-pip",
            Language.JAVASCRIPT: "sudo apt-get install nodejs npm",
            Language.TYPESCRIPT: "npm install -g typescript ts-node",
            Language.GO: "sudo apt-get install golang",
            Language.RUST: "curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh",
            Language.JAVA: "sudo apt-get install default-jdk",
            Language.C: "sudo apt-get install gcc",
            Language.CPP: "sudo apt-get install g++",
        }
        instruction = instructions.get(language)
        if instruction:
            logger.info(f"To install {language.value} runtime, run: {instruction}")
        return False

    async def run(
        self,
        code: str,
        language: Language,
        filename: Optional[str] = None,
        dependencies: Optional[List[str]] = None,
        cwd: Optional[str] = None,
    ) -> ExecutionResult:
        run_dir = cwd or self.workspace_dir
        os.makedirs(run_dir, exist_ok=True)

        if dependencies:
            await self._install_dependencies(language, dependencies, run_dir)

        if language == Language.PYTHON:
            return await self._run_python(code, filename, run_dir)
        elif language in (Language.JAVASCRIPT, Language.TYPESCRIPT):
            return await self._run_js(code, language, filename, run_dir)
        elif language == Language.GO:
            return await self._run_go(code, filename, run_dir)
        elif language == Language.BASH:
            return await self._run_bash(code, filename, run_dir)
        else:
            return ExecutionResult(
                stdout="",
                stderr=f"Runtime for {language.value} not fully implemented",
                exit_code=1,
                duration=0.0,
            )

    async def _run_python(self, code: str, filename: Optional[str], cwd: str) -> ExecutionResult:
        fname = filename or "_run.py"
        fpath = os.path.join(cwd, fname)
        with open(fpath, "w") as f:
            f.write(code)
        result = await self._terminal.execute(f"python3 {fname}", cwd=cwd, timeout=60)
        return result

    async def _run_js(self, code: str, language: Language, filename: Optional[str], cwd: str) -> ExecutionResult:
        ext = ".ts" if language == Language.TYPESCRIPT else ".js"
        fname = filename or f"_run{ext}"
        fpath = os.path.join(cwd, fname)
        with open(fpath, "w") as f:
            f.write(code)
        if language == Language.TYPESCRIPT:
            cmd = f"npx --yes ts-node {fname}"
        else:
            cmd = f"node {fname}"
        return await self._terminal.execute(cmd, cwd=cwd, timeout=60)

    async def _run_go(self, code: str, filename: Optional[str], cwd: str) -> ExecutionResult:
        fname = filename or "_run.go"
        fpath = os.path.join(cwd, fname)
        with open(fpath, "w") as f:
            f.write(code)
        return await self._terminal.execute(f"go run {fname}", cwd=cwd, timeout=60)

    async def _run_bash(self, code: str, filename: Optional[str], cwd: str) -> ExecutionResult:
        fname = filename or "_run.sh"
        fpath = os.path.join(cwd, fname)
        with open(fpath, "w") as f:
            f.write(code)
        os.chmod(fpath, 0o755)
        return await self._terminal.execute(f"bash {fname}", cwd=cwd, timeout=60)

    async def _install_dependencies(self, language: Language, deps: List[str], cwd: str) -> None:
        if not deps:
            return
        if language == Language.PYTHON:
            pkgs = " ".join(deps)
            result = await self._terminal.execute(f"pip3 install {pkgs}", cwd=cwd, timeout=120)
            if result.exit_code != 0:
                logger.warning(f"Dependency install warning: {result.stderr}")
        elif language in (Language.JAVASCRIPT, Language.TYPESCRIPT):
            pkgs = " ".join(deps)
            result = await self._terminal.execute(f"npm install {pkgs}", cwd=cwd, timeout=120)
            if result.exit_code != 0:
                logger.warning(f"Dependency install warning: {result.stderr}")


runtime_manager = RuntimeManager()
