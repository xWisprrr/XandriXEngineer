import os
from dataclasses import dataclass, field
from typing import List, Optional

from config import settings
from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class TestResult:
    passed: int = 0
    failed: int = 0
    errors: List[str] = field(default_factory=list)
    coverage: Optional[float] = None
    output: str = ""
    success: bool = False


PYTEST_TEMPLATE = '''import pytest

{test_functions}
'''

JEST_TEMPLATE = '''describe("{module_name}", () => {{
{test_cases}
}});
'''


class TesterAgent:
    name = "tester"

    def __init__(self) -> None:
        self.status = "idle"
        self.current_action = ""

    async def generate_tests(self, code: str, language: str = "python", framework: str = "pytest") -> str:
        self.status = "active"
        self.current_action = f"Generating {framework} tests"
        logger.info("TesterAgent: generating tests...")

        if settings.OPENAI_API_KEY or settings.ANTHROPIC_API_KEY:
            try:
                tests = await self._llm_generate_tests(code, language, framework)
                self.status = "idle"
                self.current_action = ""
                return tests
            except Exception as exc:
                logger.warning(f"LLM test generation failed: {exc}")

        tests = self._template_tests(code, language, framework)
        self.status = "idle"
        self.current_action = ""
        return tests

    async def run_tests(self, test_file: str, language: str = "python", cwd: Optional[str] = None) -> TestResult:
        self.status = "active"
        self.current_action = "Running tests"
        logger.info(f"TesterAgent: running tests in {test_file}")

        from tools.terminal import TerminalTool
        terminal = TerminalTool(default_cwd=cwd or "./workspace")

        if language == "python":
            result = await terminal.execute(
                f"python3 -m pytest {test_file} -v --tb=short 2>&1",
                timeout=120,
            )
        elif language in ("javascript", "typescript"):
            result = await terminal.execute(
                f"npx jest {test_file} 2>&1",
                timeout=120,
            )
        else:
            self.status = "idle"
            return TestResult(errors=[f"Unsupported language: {language}"], output="")

        self.status = "idle"
        self.current_action = ""
        return self._parse_test_output(result.stdout + result.stderr, language)

    def _parse_test_output(self, output: str, language: str) -> TestResult:
        import re
        result = TestResult(output=output)

        if language == "python":
            passed_match = re.search(r'(\d+) passed', output)
            failed_match = re.search(r'(\d+) failed', output)
            error_match = re.search(r'(\d+) error', output)
            result.passed = int(passed_match.group(1)) if passed_match else 0
            result.failed = int(failed_match.group(1)) if failed_match else 0
            if error_match:
                result.errors.append(f"{error_match.group(1)} errors")
            result.success = result.failed == 0 and not result.errors

            coverage_match = re.search(r'TOTAL\s+\d+\s+\d+\s+(\d+)%', output)
            if coverage_match:
                result.coverage = float(coverage_match.group(1))
        elif language in ("javascript", "typescript"):
            passed_match = re.search(r'(\d+) passed', output)
            failed_match = re.search(r'(\d+) failed', output)
            result.passed = int(passed_match.group(1)) if passed_match else 0
            result.failed = int(failed_match.group(1)) if failed_match else 0
            result.success = result.failed == 0

        return result

    def _template_tests(self, code: str, language: str, framework: str) -> str:
        if language == "python" and framework == "pytest":
            return PYTEST_TEMPLATE.format(
                test_functions='''
def test_basic():
    """Basic test - replace with actual tests."""
    assert True

def test_placeholder():
    """Placeholder test."""
    result = None
    assert result is None
'''
            )
        elif language in ("javascript", "typescript") and framework == "jest":
            return JEST_TEMPLATE.format(
                module_name="module",
                test_cases='''
  test("basic test", () => {
    expect(true).toBe(true);
  });
'''
            )
        return f"# Tests for {language} code\n# Add tests here\n"

    async def _llm_generate_tests(self, code: str, language: str, framework: str) -> str:
        prompt = f"""You are a QA engineer. Generate comprehensive tests for the following {language} code using {framework}.

Code to test:
```{language}
{code}
```

Rules:
- Write complete, runnable tests
- Cover happy path and edge cases
- Use proper {framework} syntax
- Return ONLY the test code"""
        return await self._call_llm(prompt)

    async def _call_llm(self, prompt: str) -> str:
        if settings.MODEL_PROVIDER == "anthropic" and settings.ANTHROPIC_API_KEY:
            import anthropic
            client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
            msg = await client.messages.create(
                model=settings.DEFAULT_MODEL or "claude-3-opus-20240229",
                max_tokens=3000,
                messages=[{"role": "user", "content": prompt}],
            )
            return msg.content[0].text
        elif settings.OPENAI_API_KEY:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            response = await client.chat.completions.create(
                model=settings.DEFAULT_MODEL or "gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=3000,
            )
            return response.choices[0].message.content or ""
        raise ValueError("No LLM API key configured")
