from dataclasses import dataclass, field
from typing import List, Optional

from config import settings
from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ReviewIssue:
    severity: str  # "error", "warning", "info"
    line: Optional[int]
    message: str
    suggestion: str = ""


@dataclass
class ReviewResult:
    issues: List[ReviewIssue] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    score: float = 0.0
    approved: bool = False
    summary: str = ""


@dataclass
class CritiqueResult:
    issues: List[str] = field(default_factory=list)
    improvements: List[str] = field(default_factory=list)
    quality_score: float = 0.0
    meets_requirements: bool = False
    explanation: str = ""


class ReviewerAgent:
    name = "reviewer"

    def __init__(self) -> None:
        self.status = "idle"
        self.current_action = ""

    async def review_code(self, code: str, requirements: str = "", language: str = "python") -> ReviewResult:
        self.status = "active"
        self.current_action = "Reviewing code"
        logger.info("ReviewerAgent: reviewing code...")

        if settings.OPENAI_API_KEY or settings.ANTHROPIC_API_KEY:
            try:
                result = await self._llm_review(code, requirements, language)
                self.status = "idle"
                self.current_action = ""
                return result
            except Exception as exc:
                logger.warning(f"LLM code review failed: {exc}")

        result = self._static_review(code, language)
        self.status = "idle"
        self.current_action = ""
        return result

    async def self_critique(self, output: str, expected: str) -> CritiqueResult:
        self.status = "active"
        self.current_action = "Self-critiquing output"
        logger.info("ReviewerAgent: self-critiquing...")

        if settings.OPENAI_API_KEY or settings.ANTHROPIC_API_KEY:
            try:
                result = await self._llm_critique(output, expected)
                self.status = "idle"
                self.current_action = ""
                return result
            except Exception as exc:
                logger.warning(f"LLM critique failed: {exc}")

        self.status = "idle"
        self.current_action = ""
        return CritiqueResult(
            quality_score=0.5,
            meets_requirements=bool(output),
            explanation="Automated self-critique unavailable without LLM.",
        )

    def _static_review(self, code: str, language: str) -> ReviewResult:
        issues: List[ReviewIssue] = []
        suggestions: List[str] = []

        lines = code.split('\n')
        for i, line in enumerate(lines, 1):
            if len(line) > 120:
                issues.append(ReviewIssue(
                    severity="warning",
                    line=i,
                    message=f"Line too long ({len(line)} chars)",
                    suggestion="Break line into multiple lines",
                ))

        if language == "python":
            if "except:" in code and "except Exception" not in code:
                issues.append(ReviewIssue(
                    severity="warning",
                    line=None,
                    message="Bare except clause catches all exceptions",
                    suggestion="Use 'except Exception as e:' instead",
                ))
            if "print(" in code and "logging" not in code:
                suggestions.append("Consider using logging instead of print statements")
            if not any(line.strip().startswith('"""') or line.strip().startswith("'''") for line in lines[:5]):
                suggestions.append("Add a module docstring")

        error_count = sum(1 for i in issues if i.severity == "error")
        warning_count = sum(1 for i in issues if i.severity == "warning")
        score = max(0.0, 1.0 - (error_count * 0.3) - (warning_count * 0.1))

        return ReviewResult(
            issues=issues,
            suggestions=suggestions,
            score=round(score, 2),
            approved=error_count == 0,
            summary=f"Found {error_count} errors and {warning_count} warnings.",
        )

    async def _llm_review(self, code: str, requirements: str, language: str) -> ReviewResult:
        import json, re
        prompt = f"""Review this {language} code and provide feedback.

{f'Requirements: {requirements}' if requirements else ''}

Code:
```{language}
{code}
```

Respond with a JSON object:
{{
  "issues": [
    {{"severity": "error|warning|info", "line": null or line_number, "message": "...", "suggestion": "..."}}
  ],
  "suggestions": ["..."],
  "score": 0.0 to 1.0,
  "approved": true or false,
  "summary": "..."
}}

Return ONLY the JSON."""
        response = await self._call_llm(prompt)
        match = re.search(r'\{.*\}', response, re.DOTALL)
        if match:
            data = json.loads(match.group(0))
            issues = [
                ReviewIssue(
                    severity=i.get("severity", "info"),
                    line=i.get("line"),
                    message=i.get("message", ""),
                    suggestion=i.get("suggestion", ""),
                )
                for i in data.get("issues", [])
            ]
            return ReviewResult(
                issues=issues,
                suggestions=data.get("suggestions", []),
                score=float(data.get("score", 0.5)),
                approved=bool(data.get("approved", False)),
                summary=data.get("summary", ""),
            )
        return self._static_review(code, language)

    async def _llm_critique(self, output: str, expected: str) -> CritiqueResult:
        import json, re
        prompt = f"""Critique this output compared to expected requirements.

Expected: {expected}
Actual Output: {output}

Respond with JSON:
{{
  "issues": ["..."],
  "improvements": ["..."],
  "quality_score": 0.0 to 1.0,
  "meets_requirements": true or false,
  "explanation": "..."
}}

Return ONLY the JSON."""
        response = await self._call_llm(prompt)
        match = re.search(r'\{.*\}', response, re.DOTALL)
        if match:
            data = json.loads(match.group(0))
            return CritiqueResult(
                issues=data.get("issues", []),
                improvements=data.get("improvements", []),
                quality_score=float(data.get("quality_score", 0.5)),
                meets_requirements=bool(data.get("meets_requirements", False)),
                explanation=data.get("explanation", ""),
            )
        return CritiqueResult(quality_score=0.5, meets_requirements=bool(output))

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
