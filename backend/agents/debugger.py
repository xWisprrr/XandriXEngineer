from dataclasses import dataclass, field
from typing import List, Optional

from config import settings
from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class DebugResult:
    error_type: str
    root_cause: str
    suggested_fix: str
    confidence: float
    fixed_code: Optional[str] = None


class DebuggerAgent:
    name = "debugger"

    def __init__(self) -> None:
        self.status = "idle"
        self.current_action = ""

    async def analyze_error(self, error: str, code: str = "", context: str = "") -> DebugResult:
        self.status = "active"
        self.current_action = "Analyzing error"
        logger.info(f"DebuggerAgent: analyzing error: {error[:80]}...")

        if settings.OPENAI_API_KEY or settings.ANTHROPIC_API_KEY:
            try:
                result = await self._llm_analyze(error, code, context)
                self.status = "idle"
                self.current_action = ""
                return result
            except Exception as exc:
                logger.warning(f"LLM debug analysis failed: {exc}")

        result = self._rule_based_analyze(error, code)
        self.status = "idle"
        self.current_action = ""
        return result

    async def suggest_fix(self, error: str, code: str) -> str:
        self.status = "active"
        self.current_action = "Suggesting fix"
        logger.info("DebuggerAgent: suggesting fix...")

        if settings.OPENAI_API_KEY or settings.ANTHROPIC_API_KEY:
            try:
                prompt = f"""Fix the following code that has this error:

Error: {error}

Code:
```
{code}
```

Return ONLY the fixed code, no explanation."""
                fixed = await self._call_llm(prompt)
                self.status = "idle"
                self.current_action = ""
                import re
                fixed = re.sub(r'^```[\w]*\n?', '', fixed.strip())
                fixed = re.sub(r'\n?```$', '', fixed.strip())
                return fixed.strip()
            except Exception as exc:
                logger.warning(f"LLM fix suggestion failed: {exc}")

        self.status = "idle"
        self.current_action = ""
        return code

    def _rule_based_analyze(self, error: str, code: str) -> DebugResult:
        error_lower = error.lower()

        if "syntaxerror" in error_lower or "syntax error" in error_lower:
            return DebugResult(
                error_type="SyntaxError",
                root_cause="Code has invalid syntax",
                suggested_fix="Check for missing colons, brackets, or indentation errors",
                confidence=0.8,
            )
        elif "nameerror" in error_lower or "is not defined" in error_lower:
            return DebugResult(
                error_type="NameError",
                root_cause="Variable or function used before definition",
                suggested_fix="Ensure all variables and functions are defined before use",
                confidence=0.85,
            )
        elif "importerror" in error_lower or "modulenotfounderror" in error_lower:
            return DebugResult(
                error_type="ImportError",
                root_cause="Module not installed or not found",
                suggested_fix="Install the required module with pip/npm or check the import path",
                confidence=0.9,
            )
        elif "typeerror" in error_lower:
            return DebugResult(
                error_type="TypeError",
                root_cause="Wrong type passed to function or operation",
                suggested_fix="Check the types of arguments and ensure they match expected types",
                confidence=0.75,
            )
        elif "indexerror" in error_lower or "index out of range" in error_lower:
            return DebugResult(
                error_type="IndexError",
                root_cause="Accessing list/array with invalid index",
                suggested_fix="Check array bounds before accessing elements",
                confidence=0.85,
            )
        elif "keyerror" in error_lower:
            return DebugResult(
                error_type="KeyError",
                root_cause="Dictionary key does not exist",
                suggested_fix="Use dict.get(key, default) or check if key exists first",
                confidence=0.85,
            )
        elif "attributeerror" in error_lower:
            return DebugResult(
                error_type="AttributeError",
                root_cause="Object does not have the requested attribute",
                suggested_fix="Check the object type and available attributes",
                confidence=0.8,
            )
        elif "filenotfounderror" in error_lower or "no such file" in error_lower:
            return DebugResult(
                error_type="FileNotFoundError",
                root_cause="File or directory does not exist",
                suggested_fix="Check the file path and ensure the file exists",
                confidence=0.9,
            )
        elif "connectionerror" in error_lower or "connection refused" in error_lower:
            return DebugResult(
                error_type="ConnectionError",
                root_cause="Cannot connect to server or service",
                suggested_fix="Check that the service is running and the address/port is correct",
                confidence=0.85,
            )
        else:
            return DebugResult(
                error_type="UnknownError",
                root_cause="Error could not be automatically classified",
                suggested_fix="Review the error message and stack trace for clues",
                confidence=0.3,
            )

    async def _llm_analyze(self, error: str, code: str, context: str) -> DebugResult:
        prompt = f"""Analyze this error and provide debugging information.

Error: {error}
{f'Code: ```\\n{code}\\n```' if code else ''}
{f'Context: {context}' if context else ''}

Respond with a JSON object with these fields:
- error_type: string (e.g., "TypeError", "LogicError")
- root_cause: string (explanation of why this error occurred)
- suggested_fix: string (concrete steps to fix it)
- confidence: float between 0 and 1

Return ONLY the JSON object."""
        import json, re
        response = await self._call_llm(prompt)
        match = re.search(r'\{.*\}', response, re.DOTALL)
        if match:
            data = json.loads(match.group(0))
            return DebugResult(
                error_type=data.get("error_type", "UnknownError"),
                root_cause=data.get("root_cause", ""),
                suggested_fix=data.get("suggested_fix", ""),
                confidence=float(data.get("confidence", 0.5)),
            )
        return self._rule_based_analyze(error, code)

    async def _call_llm(self, prompt: str) -> str:
        if settings.MODEL_PROVIDER == "anthropic" and settings.ANTHROPIC_API_KEY:
            import anthropic
            client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
            msg = await client.messages.create(
                model=settings.DEFAULT_MODEL or "claude-3-opus-20240229",
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}],
            )
            return msg.content[0].text
        elif settings.OPENAI_API_KEY:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            response = await client.chat.completions.create(
                model=settings.DEFAULT_MODEL or "gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2000,
            )
            return response.choices[0].message.content or ""
        raise ValueError("No LLM API key configured")
