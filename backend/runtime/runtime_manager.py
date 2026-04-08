"""
XandriX Engineer - Multi-Language Runtime Manager
Handles compilation, execution, and debugging across all supported languages.
"""
import re
from pathlib import Path
from typing import Optional

from backend.config import SUPPORTED_LANGUAGES
from backend.core.logger import get_logger
from backend.models.schemas import ExecutionResult, ExecutionStatus
from backend.tools.terminal import Terminal

logger = get_logger("runtime")


class RuntimeManager:
    """Manages code execution across multiple programming languages."""

    def __init__(self, terminal: Terminal = None):
        self.terminal = terminal or Terminal()

    def detect_language(self, code: str, filename: str = "") -> str:
        """Auto-detect the programming language from code/filename."""
        if filename:
            ext = Path(filename).suffix.lower()
            for lang, info in SUPPORTED_LANGUAGES.items():
                if ext in info["extensions"]:
                    return lang

        # Heuristic detection from code patterns
        patterns = {
            "python": [r"import\s+\w+", r"def\s+\w+\(", r"print\(", r"#!.*python"],
            "javascript": [r"const\s+\w+", r"function\s+\w+\(", r"require\(", r"console\.log"],
            "typescript": [r"interface\s+\w+", r":\s*string", r":\s*number", r"export\s+"],
            "java": [r"public\s+class", r"System\.out", r"import\s+java"],
            "go": [r"package\s+main", r"func\s+main\(", r"import\s+\""],
            "rust": [r"fn\s+main\(", r"let\s+mut\s", r"println!"],
            "cpp": [r"#include\s*<", r"std::", r"cout\s*<<"],
            "c": [r"#include\s*<stdio\.h>", r"int\s+main\(", r"printf\("],
            "bash": [r"#!/bin/(ba)?sh", r"\$\{.*\}", r"echo\s+"],
            "sql": [r"SELECT\s+", r"INSERT\s+INTO", r"CREATE\s+TABLE"],
        }

        scores = {lang: 0 for lang in patterns}
        for lang, pats in patterns.items():
            for pat in pats:
                if re.search(pat, code, re.IGNORECASE):
                    scores[lang] += 1

        best = max(scores, key=scores.get)
        if scores[best] > 0:
            return best
        return "python"  # default

    async def run_code(
        self,
        code: str,
        language: str,
        working_dir: Optional[Path] = None,
        timeout: int = 60,
        args: list[str] = None,
    ) -> ExecutionResult:
        """Execute code in the specified language."""
        lang_info = SUPPORTED_LANGUAGES.get(language)
        if not lang_info:
            return ExecutionResult(
                status=ExecutionStatus.ERROR,
                stderr=f"Unsupported language: {language}",
            )

        if language == "python":
            return await self._run_python(code, working_dir, timeout, args)
        elif language in ("javascript", "typescript"):
            return await self._run_js_ts(code, language, working_dir, timeout, args)
        elif language == "go":
            return await self._run_go(code, working_dir, timeout, args)
        elif language == "rust":
            return await self._run_rust(code, working_dir, timeout, args)
        elif language in ("c", "cpp"):
            return await self._run_c_cpp(code, language, working_dir, timeout, args)
        elif language == "java":
            return await self._run_java(code, working_dir, timeout, args)
        elif language == "bash":
            return await self._run_bash(code, working_dir, timeout, args)
        elif language == "sql":
            return await self._run_sql(code, working_dir, timeout)
        else:
            return ExecutionResult(
                status=ExecutionStatus.ERROR,
                stderr=f"Runtime for {language} not implemented",
            )

    async def run_file(
        self,
        filepath: Path,
        working_dir: Optional[Path] = None,
        timeout: int = 60,
        args: list[str] = None,
    ) -> ExecutionResult:
        """Execute an existing file."""
        code = filepath.read_text(encoding="utf-8")
        language = self.detect_language(code, filepath.name)
        return await self.run_code(code, language, working_dir or filepath.parent, timeout, args)

    async def _run_python(self, code: str, cwd: Optional[Path], timeout: int, args: list[str]) -> ExecutionResult:
        import tempfile, os
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, dir=cwd) as f:
            f.write(code)
            tmp = f.name
        args_str = " ".join(args or [])
        result = await self.terminal.run(f"python3 {tmp} {args_str}", working_dir=cwd, timeout=timeout)
        os.unlink(tmp)
        result.language = "python"
        return result

    async def _run_js_ts(self, code: str, lang: str, cwd: Optional[Path], timeout: int, args: list[str]) -> ExecutionResult:
        import tempfile, os
        ext = ".ts" if lang == "typescript" else ".js"
        with tempfile.NamedTemporaryFile(mode="w", suffix=ext, delete=False, dir=cwd) as f:
            f.write(code)
            tmp = f.name
        args_str = " ".join(args or [])
        if lang == "typescript":
            runner = "ts-node"
        else:
            runner = "node"
        result = await self.terminal.run(f"{runner} {tmp} {args_str}", working_dir=cwd, timeout=timeout)
        os.unlink(tmp)
        result.language = lang
        return result

    async def _run_go(self, code: str, cwd: Optional[Path], timeout: int, args: list[str]) -> ExecutionResult:
        import tempfile, os
        with tempfile.NamedTemporaryFile(mode="w", suffix=".go", delete=False, dir=cwd) as f:
            f.write(code)
            tmp = f.name
        args_str = " ".join(args or [])
        result = await self.terminal.run(f"go run {tmp} {args_str}", working_dir=cwd, timeout=timeout)
        os.unlink(tmp)
        result.language = "go"
        return result

    async def _run_rust(self, code: str, cwd: Optional[Path], timeout: int, args: list[str]) -> ExecutionResult:
        import tempfile, os
        work_dir = cwd or Path("/tmp/xandrix_rust")
        work_dir.mkdir(exist_ok=True)
        src_file = work_dir / "main.rs"
        out_file = work_dir / "main_out"
        src_file.write_text(code)
        compile_result = await self.terminal.run(f"rustc {src_file} -o {out_file}", working_dir=work_dir, timeout=60)
        if compile_result.return_code != 0:
            compile_result.language = "rust"
            return compile_result
        args_str = " ".join(args or [])
        result = await self.terminal.run(f"{out_file} {args_str}", working_dir=work_dir, timeout=timeout)
        result.language = "rust"
        return result

    async def _run_c_cpp(self, code: str, lang: str, cwd: Optional[Path], timeout: int, args: list[str]) -> ExecutionResult:
        import tempfile, os
        ext = ".cpp" if lang == "cpp" else ".c"
        compiler = "g++" if lang == "cpp" else "gcc"
        with tempfile.NamedTemporaryFile(mode="w", suffix=ext, delete=False, dir=cwd or Path("/tmp")) as f:
            f.write(code)
            tmp_src = f.name
        tmp_out = tmp_src.replace(ext, "")
        compile_result = await self.terminal.run(f"{compiler} {tmp_src} -o {tmp_out}", timeout=60)
        if compile_result.return_code != 0:
            os.unlink(tmp_src)
            compile_result.language = lang
            return compile_result
        args_str = " ".join(args or [])
        result = await self.terminal.run(f"{tmp_out} {args_str}", working_dir=cwd, timeout=timeout)
        os.unlink(tmp_src)
        os.unlink(tmp_out)
        result.language = lang
        return result

    async def _run_java(self, code: str, cwd: Optional[Path], timeout: int, args: list[str]) -> ExecutionResult:
        import tempfile, os, re as re_mod
        work_dir = cwd or Path("/tmp/xandrix_java")
        work_dir.mkdir(exist_ok=True)
        class_match = re_mod.search(r"public\s+class\s+(\w+)", code)
        class_name = class_match.group(1) if class_match else "Main"
        src_file = work_dir / f"{class_name}.java"
        src_file.write_text(code)
        compile_result = await self.terminal.run(f"javac {src_file}", working_dir=work_dir, timeout=60)
        if compile_result.return_code != 0:
            compile_result.language = "java"
            return compile_result
        args_str = " ".join(args or [])
        result = await self.terminal.run(f"java {class_name} {args_str}", working_dir=work_dir, timeout=timeout)
        result.language = "java"
        return result

    async def _run_bash(self, code: str, cwd: Optional[Path], timeout: int, args: list[str]) -> ExecutionResult:
        import tempfile, os
        with tempfile.NamedTemporaryFile(mode="w", suffix=".sh", delete=False) as f:
            f.write(code)
            tmp = f.name
        os.chmod(tmp, 0o755)
        args_str = " ".join(args or [])
        result = await self.terminal.run(f"bash {tmp} {args_str}", working_dir=cwd, timeout=timeout)
        os.unlink(tmp)
        result.language = "bash"
        return result

    async def _run_sql(self, code: str, cwd: Optional[Path], timeout: int) -> ExecutionResult:
        result = await self.terminal.run(
            "sqlite3 :memory:",
            working_dir=cwd,
            timeout=timeout,
            stdin_data=code,
        )
        result.language = "sql"
        return result

    async def check_syntax(self, code: str, language: str) -> tuple[bool, str]:
        """Check syntax without executing. Returns (valid, error_message)."""
        if language == "python":
            import ast
            try:
                ast.parse(code)
                return True, ""
            except SyntaxError as e:
                return False, str(e)
        elif language == "javascript":
            result = await self.terminal.run(f"node --check -e {repr(code)}")
            return result.return_code == 0, result.stderr
        return True, ""  # Can't check other languages without writing files

    def analyze_error(self, result: ExecutionResult) -> dict:
        """Parse error output and extract structured error information."""
        error_text = result.stderr or result.stdout
        patterns = {
            "python": r'File "([^"]+)", line (\d+).*?\n(.*?Error.*)',
            "javascript": r'at\s+\S+\s+\(([^:]+):(\d+):\d+\)',
            "go": r'([^:]+):(\d+):\d+:\s+(.*)',
            "rust": r'error(?:\[E\d+\])?: (.*)\n.*-->\s+([^:]+):(\d+)',
        }
        info = {
            "raw_error": error_text[:2000],
            "return_code": result.return_code,
            "language": result.language,
        }
        if result.language in patterns:
            match = re.search(patterns[result.language], error_text, re.DOTALL)
            if match:
                info["parsed"] = match.groups()
        return info
