from config import settings
from utils.logger import get_logger

logger = get_logger(__name__)

PYTHON_TEMPLATES = {
    "script": '''#!/usr/bin/env python3
"""
{description}
"""

def main():
    {body}

if __name__ == "__main__":
    main()
''',
    "fastapi": '''from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def root():
    return {{"message": "Hello World"}}
''',
    "class": '''class {name}:
    """
    {description}
    """
    
    def __init__(self):
        pass
    
    def run(self):
        raise NotImplementedError
''',
}

JS_TEMPLATES = {
    "script": '''const main = () => {{
  // {description}
  console.log("Running...");
}};

main();
''',
    "express": '''const express = require("express");
const app = express();

app.get("/", (req, res) => {{
  res.json({{ message: "Hello World" }});
}});

app.listen(3000, () => console.log("Server running on port 3000"));
''',
}


class CoderAgent:
    name = "coder"

    def __init__(self) -> None:
        self.status = "idle"
        self.current_action = ""

    async def generate_code(
        self,
        requirements: str,
        language: str = "python",
        context: str = "",
        template: str = "script",
    ) -> str:
        self.status = "active"
        self.current_action = f"Generating {language} code"
        logger.info(f"CoderAgent: generating code for: {requirements[:80]}...")

        if settings.OPENAI_API_KEY or settings.ANTHROPIC_API_KEY:
            try:
                code = await self._llm_generate(requirements, language, context)
                self.status = "idle"
                self.current_action = ""
                return code
            except Exception as exc:
                logger.warning(f"LLM code generation failed, using template: {exc}")

        code = self._template_generate(requirements, language, template)
        self.status = "idle"
        self.current_action = ""
        return code

    async def edit_code(self, existing_code: str, instructions: str) -> str:
        self.status = "active"
        self.current_action = "Editing code"
        logger.info(f"CoderAgent: editing code per instructions: {instructions[:60]}...")

        if settings.OPENAI_API_KEY or settings.ANTHROPIC_API_KEY:
            try:
                prompt = f"""Edit the following code according to these instructions:

Instructions: {instructions}

Existing code:
```
{existing_code}
```

Return ONLY the complete modified code, no explanation."""
                code = await self._call_llm(prompt)
                # Strip markdown code fences if present
                code = self._strip_code_fences(code)
                self.status = "idle"
                self.current_action = ""
                return code
            except Exception as exc:
                logger.warning(f"LLM code edit failed: {exc}")

        self.status = "idle"
        self.current_action = ""
        return existing_code

    def detect_language(self, description: str) -> str:
        desc_lower = description.lower()
        if any(kw in desc_lower for kw in ["fastapi", "flask", "django", "python", ".py"]):
            return "python"
        if any(kw in desc_lower for kw in ["react", "next.js", "vue", "angular", "javascript", ".js"]):
            return "javascript"
        if any(kw in desc_lower for kw in ["typescript", ".ts", "node.js"]):
            return "typescript"
        if any(kw in desc_lower for kw in ["golang", "go ", ".go"]):
            return "go"
        if any(kw in desc_lower for kw in ["rust", ".rs", "cargo"]):
            return "rust"
        if any(kw in desc_lower for kw in ["java ", ".java", "spring"]):
            return "java"
        return "python"

    def _template_generate(self, requirements: str, language: str, template: str) -> str:
        if language == "python":
            tmpl = PYTHON_TEMPLATES.get(template, PYTHON_TEMPLATES["script"])
            return tmpl.format(description=requirements, body='print("Hello, World!")', name="MyClass")
        elif language in ("javascript", "typescript"):
            tmpl = JS_TEMPLATES.get(template, JS_TEMPLATES["script"])
            return tmpl.format(description=requirements)
        return f'# {language} code for: {requirements}\nprint("Not implemented")\n'

    async def _llm_generate(self, requirements: str, language: str, context: str) -> str:
        prompt = f"""You are an expert {language} developer. Write complete, working code for the following requirements.

Requirements: {requirements}
{f'Context: {context}' if context else ''}
Language: {language}

Rules:
- Write complete, runnable code
- Include proper error handling
- Add brief comments for clarity
- Return ONLY the code, no explanation or markdown fences"""
        code = await self._call_llm(prompt)
        return self._strip_code_fences(code)

    def _strip_code_fences(self, code: str) -> str:
        import re
        code = re.sub(r'^```[\w]*\n?', '', code.strip())
        code = re.sub(r'\n?```$', '', code.strip())
        return code.strip()

    async def _call_llm(self, prompt: str) -> str:
        if settings.MODEL_PROVIDER == "anthropic" and settings.ANTHROPIC_API_KEY:
            import anthropic
            client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
            msg = await client.messages.create(
                model=settings.DEFAULT_MODEL or "claude-3-opus-20240229",
                max_tokens=4000,
                messages=[{"role": "user", "content": prompt}],
            )
            return msg.content[0].text
        elif settings.OPENAI_API_KEY:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            response = await client.chat.completions.create(
                model=settings.DEFAULT_MODEL or "gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=4000,
            )
            return response.choices[0].message.content or ""
        raise ValueError("No LLM API key configured")
